# Worker/service/worker_service.py
"""
Servicio de Worker que lee directamente de la BD compartida con la API.
No requiere comunicación HTTP, lee workflows pendientes de la misma BD SQLite.
"""
import time
import threading
from datetime import datetime, UTC
from typing import Optional, Dict, Any, List
import logging, json
import sys
import os

# Add parent directory to path to enable relative imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Fix Windows console encoding for emojis - set before any output
if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from sqlmodel import Session, select
from Models.shared_workflow_table import workflowTable
from workflow.workflow_engine import WorkflowEngine
from workflow.workflow_persistence import WorkflowRepository
from workflow.workflow_models import WorkflowNode, WorkflowDefinition
from worker_engine import WorkerEngine
from registry import Taskregistry

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkerService:
    """
    Servicio que lee workflows pendientes directamente de la BD SQLite compartida.
    No requiere API ni polling HTTP.
    """

    def __init__(
        self,
        shared_db_path: str = "database.db",  # ← Misma BD que usa la API
        poll_interval: float = 3.0,  # ← Cambiado de 10.0 a 3.0 segundos para ejecución más rápida
        worker_db_path: str = "data/worker_workflows.db"  # ← BD propia del worker para logs

    ):
        """
        Args:
            shared_db_path: Ruta a la BD compartida con la API (database.db)
            poll_interval: Intervalo de polling en segundos
            worker_db_path: Ruta a la BD propia del worker para persistir ejecuciones
        """
        self.shared_db_path = shared_db_path
        self.poll_interval = poll_interval
        self._stop_flag = False
        self._polling_thread: Optional[threading.Thread] = None
        self._is_stopped = False  # ✅ AGREGAR: Flag para evitar múltiples stops

        # Importar el modelo de la API
        from sqlmodel import create_engine, SQLModel
        from sqlalchemy import Column, JSON
        
        # Crear engine para la BD compartida (misma que usa la API)
        self.shared_engine = create_engine(
            f"sqlite:///{shared_db_path}",
            connect_args={"check_same_thread": False}
        )

        # Componentes del Worker
        self.registry = Taskregistry()
        self._register_tasks()
        
        self.worker_engine = WorkerEngine(self.registry)
        # IMPORTANT: Use shared DB for all workflow execution records
        self.repo = WorkflowRepository(shared_db_path)
        self.workflow_engine = WorkflowEngine(self.worker_engine, self.repo)

        # Estadísticas
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "started_at": None
        }

        logger.info(f"[WorkerService] 🚀 Inicializado")
        logger.info(f"[WorkerService] 📁 BD compartida: {shared_db_path}")
        logger.info(f"[WorkerService] 📁 BD usada para TODO (workflows + ejecuciones): {shared_db_path}")
        logger.info(f"[WorkerService] ⏱️  Poll interval: {poll_interval}s")

    def _register_tasks(self):
        """Registra todas las tareas disponibles"""
        try:
            self.registry.register("http_get")
            self.registry.register("validate_csv")
            self.registry.register("transform_simple")
            self.registry.register("save_db")
            self.registry.register("notify_mock")
            logger.info("[WorkerService] ✅ Tareas registradas correctamente")
        except Exception as e:
            logger.error(f"[WorkerService] ❌ Error registrando tareas: {e}")
            raise

    def _get_pending_workflows_from_db(self) -> List[Dict[str, Any]]:
        """
        Lee workflows pendientes directamente de la BD compartida.
        
        Returns:
            Lista de workflows con estado 'en_espera'
        """
        # Importar el modelo de la API (WorkflowTable)
        # from sqlmodel import SQLModel, Field as SQLField
        # import json
        
        # class WorkflowTable(SQLModel, table=True):
        #     """Modelo idéntico al de la API"""
        #     __tablename__ = "workflowtable"
        #     __table_args__ = {"extend_existing": True}
            
        #     id: str = SQLField(primary_key=True, index=True)
        #     name: str
        #     status: str
        #     created_at: str
        #     updated_at: str
        #     definition: Optional[str] = None

        try:
            with Session(self.shared_engine) as session:
                # Buscar workflows con estado 'en_espera'
                stmt = select(workflowTable).where(workflowTable.status == "en_espera")
                records = session.exec(stmt).all()
                # Convertir a diccionarios
                workflows = []
                for record in records:
                    workflows.append({
                        "id": record.id,
                        "name": record.name,
                        "status": record.status,
                        "created_at": record.created_at,
                        "definition": json.loads(record.definition) if record.definition else {}
                    })
                
                return workflows
                
        except Exception as e:
            logger.error(f"[WorkerService] ❌ Error leyendo BD: {e}")
            return []

    def _update_workflow_status_in_db(
        self, 
        workflow_id: str, 
        status: str, 
        results: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Actualiza el estado de un workflow en la BD compartida.
        
        Args:
            workflow_id: ID del workflow
            status: Nuevo estado ('en_progreso', 'completado', 'fallido')
            results: Resultados de la ejecución (opcional)
            
        Returns:
            True si se actualizó exitosamente
        """
        # from sqlmodel import SQLModel, Field as SQLField
        # import json
        
        # class WorkflowTable(SQLModel, table=True):
        #     """Modelo idéntico al de la API"""
        #     __tablename__ = "workflowtable"
        #     __table_args__ = {"extend_existing": True}
            
        #     id: str = SQLField(primary_key=True)
        #     name: str
        #     status: str
        #     created_at: str
        #     definition: Optional[str] = None

        try:
            with Session(self.shared_engine) as session:
                stmt = select(workflowTable).where(workflowTable.id == workflow_id)
                record = session.exec(stmt).first()
                
                if not record:
                    logger.warning(f"[WorkerService] ⚠️ Workflow {workflow_id} no encontrado")
                    return False
                
                # Actualizar estado
                record.status = status
                record.updated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
                
                # Si hay resultados, agregarlos a la definición
                if results:
                    current_def = json.loads(record.definition) if record.definition else {}
                    current_def["execution_results"] = results
                    current_def["executed_at"] = datetime.now(UTC).isoformat()
                    record.definition = json.dumps(current_def)
                
                session.add(record)
                session.commit()
                session.refresh(record)
                
                logger.debug(f"[WorkerService] 💾 Estado de {workflow_id} actualizado a '{status}'")
                return True
                
        except Exception as e:
            logger.error(f"[WorkerService] ❌ Error actualizando BD: {e}")
            return False

    def _convert_api_workflow_to_definition(self, api_workflow: Dict[str, Any]) -> WorkflowDefinition:
        """
        Convierte la estructura de workflow de la API a WorkflowDefinition del Worker.

        Soporta dos formatos:
        1. Backend format (nodes directamente): {"nodes": [...]}
        2. Legacy format (steps): {"steps": [...]}
        """
        definition = api_workflow.get("definition", {})

        # Check if definition already has nodes (Backend format)
        if "nodes" in definition:
            # Backend already converted to Worker format
            nodes_data = definition["nodes"]
            nodes = [
                WorkflowNode(
                    id=node.get("id"),
                    type=node.get("type"),
                    params=node.get("params", {}),
                    depends_on=node.get("depends_on", [])
                )
                for node in nodes_data
            ]
        else:
            # Legacy: Convert from steps
            steps = definition.get("steps", [])
            nodes = []
            for i, step in enumerate(steps):
                api_type = step.get("type", "")
                worker_type = self._map_step_type(api_type)
                node = WorkflowNode(
                    id=f"step_{i}",
                    type=worker_type,
                    params=step.get("args", {}),
                    depends_on=[f"step_{i-1}"] if i > 0 else []
                )
                nodes.append(node)

        return WorkflowDefinition(
            name=api_workflow.get("name", "unnamed_workflow"),
            nodes=nodes,
            id=api_workflow.get("id")  # Pass workflow ID
        )

    def _map_step_type(self, api_type: str) -> str:
        """
        Mapea tipos de tareas de la API a tipos del Worker.
        """
        mapping = {
            "HTTPS GET Request": "http_get",
            "Validate CSV File": "validate_csv",
            "Simple Transform": "transform_simple",
            "Save to Database": "save_db",
            "Mock Notification": "notify_mock"
        }
        
        result = mapping.get(api_type)
        if not result:
            logger.warning(f"[WorkerService] ⚠️ Tipo desconocido '{api_type}', usando como está")
            result = api_type.lower().replace(" ", "_")
        
        return result

    def _map_worker_status_to_api(self, worker_status: str) -> str:
        """
        Mapea estados del Worker a estados de la API.
        """
        mapping = {
            "SUCCESS": "completado",
            "FAILED": "fallido",
            "PARTIAL_SUCCESS": "completado",
            "RUNNING": "en_progreso"
        }
        return mapping.get(worker_status, "fallido")

    def _execute_workflow(self, api_workflow: Dict[str, Any]) -> bool:
        """
        Ejecuta un workflow individual.
        
        Returns:
            True si se procesó exitosamente, False en caso contrario
        """
        workflow_id = api_workflow["id"]
        workflow_name = api_workflow["name"]

        logger.info(f"[WorkerService] 📥 Procesando workflow: {workflow_name} (ID: {workflow_id})")

        try:
            # 1. Marcar como 'en_progreso'
            if not self._update_workflow_status_in_db(workflow_id, "en_progreso"):
                logger.warning(f"[WorkerService] ⚠️ No se pudo reclamar workflow {workflow_id}")
                return False

            # 2. Convertir a formato del Worker
            workflow_def = self._convert_api_workflow_to_definition(api_workflow)

            # 3. Ejecutar workflow
            logger.info(f"[WorkerService] ▶️ Ejecutando workflow: {workflow_name}")
            result = self.workflow_engine.run(workflow_def)

            # 4. Mapear resultado al formato de la API
            api_status = self._map_worker_status_to_api(result.status)

            # 5. Actualizar estado en BD compartida

            success = self._update_workflow_status_in_db(
                workflow_id=workflow_id,
                status=api_status,
                results=result.results
            )
            if not success:
                logger.error(f"[WorkerService] ❌ Error actualizando estado de {workflow_name}")
                self.stats["failed"] += 1
                self.stats["total_processed"] += 1
                return False
            
            self.stats["total_processed"] += 1  
            if api_status == "completado":
                logger.info(f"[WorkerService] ✅ Workflow {workflow_name} completado: {api_status}")
                self.stats["successful"] += 1
                return True
            else:
                logger.warning(f"[WorkerService] ⚠️ Workflow {workflow_name} falló: {api_status}")
                self.stats["failed"] += 1 
                return False  


        except Exception as e:
            logger.error(f"[WorkerService] 💥 Error ejecutando workflow {workflow_name}: {e}", exc_info=True)
            # Marcar como fallido en BD
            try:
                self._update_workflow_status_in_db(
                    workflow_id=workflow_id,
                    status="fallido"
                )
            except Exception as update_error:
                logger.error(f"[WorkerService] ⚠️ No se pudo actualizar estado a 'fallido': {update_error}")

            self.stats["failed"] += 1
            self.stats["total_processed"] += 1
            return False

    def _poll_loop(self):
        """
        Bucle principal: consulta workflows pendientes de la BD y los ejecuta.
        """
        logger.info(f"[WorkerService] 🔄 Iniciando loop de polling...")
        self.stats["started_at"] = datetime.now(UTC).isoformat()

        cycle_count = 0

        while not self._stop_flag:
            try:
                cycle_count += 1
                # Consultar workflows pendientes de la BD
                logger.debug("[WorkerService] 🔍 Consultando workflows pendientes en BD...")
                pending_workflows = self._get_pending_workflows_from_db()

                if not pending_workflows:
                    logger.debug("[WorkerService] 💤 No hay workflows pendientes")
                else:
                    logger.info(f"[WorkerService] 📋 Encontrados {len(pending_workflows)} workflow(s) pendiente(s)")

                    # Procesar cada workflow
                    for workflow in pending_workflows:
                        self._execute_workflow(workflow)
                
                logger.debug(f"[WorkerService] 😴 Durmiendo {self.poll_interval}s hasta próximo ciclo...")

            except Exception as e:
                logger.error(f"[WorkerService] ⚠️ Error en ciclo de polling: {e}", exc_info=True)

            # Esperar antes del siguiente ciclo
            time.sleep(self.poll_interval)

        logger.info("[WorkerService] 🛑 Loop de polling detenido")

    def start(self):
        """
        Inicia el servicio de polling en un hilo separado.
        No bloqueante.
        """
        if self._polling_thread and self._polling_thread.is_alive():
            logger.warning("[WorkerService] ⚠️ El servicio ya está corriendo")
            return

        logger.info(f"[WorkerService] 🚀 Iniciando servicio de polling (intervalo: {self.poll_interval}s)")
        self._stop_flag = False
        self._polling_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._polling_thread.start()

    def start_blocking(self):
        """
        Inicia el servicio de polling de forma bloqueante.
        Útil para ejecutar como proceso principal.
        """
        print("\n" + "="*70)
        print("🚀 WORKER SERVICE INICIADO")
        print("="*70)
        print(f"📁 Base de datos: {self.shared_db_path}")
        print(f"⏱️  Intervalo de polling: {self.poll_interval} segundos")
        print(f"📊 Listo para procesar workflows...")
        print("="*70 + "\n")

        logger.info(f"[WorkerService] 🚀 Iniciando servicio en modo bloqueante...")
        self._stop_flag = False

        try:
            self._poll_loop()
        except KeyboardInterrupt:
            logger.info("[WorkerService] ⏹️ Interrupción por teclado (Ctrl+C)")
            self._stop_flag = True

    def stop(self):
        """
        Detiene el servicio de polling.
        """
        if self._is_stopped:
            # ✅ Mostrar desde dónde se llamó
            import traceback
            logger.warning("[WorkerService] ⚠️ stop() llamado múltiples veces desde:")
            logger.warning("".join(traceback.format_stack()))
            return
        if self._is_stopped:
            logger.debug("[WorkerService] ⚠️ El servicio ya fue detenido, ignorando llamada duplicada")
            return
        
        self._is_stopped = True
        logger.info("[WorkerService] ⏸️ Deteniendo servicio...")
        self._stop_flag = True

        if self._polling_thread:
            self._polling_thread.join(timeout=5)

        logger.info("[WorkerService] 🛑 Servicio detenido")
        logger.info(f"[WorkerService] 📊 Estadísticas: {self.stats}")
        
        # Cleanup
        self.registry.clear()
         # 💡 Cerrar conexiones abiertas
        try:
            self.shared_engine.dispose()
            self.repo.engine.dispose()
            logger.info("[WorkerService] 🔒 Conexiones SQLite cerradas correctamente")
        except Exception as e:
            logger.warning(f"[WorkerService] ⚠️ Error cerrando conexiones: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas del servicio"""
        return self.stats.copy()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Worker Service para ejecutar workflows')
    parser.add_argument('--db-path', type=str, default='../data/workflows.db',
                        help='Ruta a la base de datos SQLite compartida')
    parser.add_argument('--poll-interval', type=float, default=3.0,
                        help='Intervalo de polling en segundos (default: 3.0)')

    args = parser.parse_args()

    print("[WorkerService] Starting with database:", args.db_path)
    print(f"[WorkerService] Polling every {args.poll_interval} seconds...")
    print()

    # Crear y iniciar servicio (el parámetro se llama shared_db_path, no db_path)
    service = WorkerService(shared_db_path=args.db_path, poll_interval=args.poll_interval)

    try:
        service.start()
        # Mantener el programa corriendo
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[WorkerService] Deteniendo servicio...")
        service.stop()
        print("[WorkerService] Servicio detenido correctamente")