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
from sqlmodel import Session, select
from Worker.Models.shared_workflow_table import workflowTable
from Worker.workflow.workflow_engine import WorkflowEngine
from Worker.workflow.workflow_persistence import WorkflowRepository
from Worker.workflow.workflow_models import WorkflowNode, WorkflowDefinition
from Worker.worker_engine import WorkerEngine
from Worker.registry import Taskregistry

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
        poll_interval: float = 10.0,
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
        self.repo = WorkflowRepository(worker_db_path)  # BD propia para logs
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
        logger.info(f"[WorkerService] 📁 BD Worker: {worker_db_path}")
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
                
                #agregar y borrar despues
                logger.info(f"[WorkerService] ✅ Estado actualizado: {workflow_id} → {status}")
                logger.debug(f"[WorkerService] 📊 Estado en BD después de commit: {record.status}")

                logger.debug(f"[WorkerService] 💾 Estado de {workflow_id} actualizado a '{status}'")
                return True
                
        except Exception as e:
            logger.error(f"[WorkerService] ❌ Error actualizando BD: {e}")
            #agregar y borrar despues
            import traceback
            logger.error(f"[WorkerService] 📜 Traceback:\n{traceback.format_exc()}")
            return False

    def _convert_api_workflow_to_definition(self, api_workflow: Dict[str, Any]) -> WorkflowDefinition:
        """
        Convierte la estructura de workflow de la API a WorkflowDefinition del Worker.
        
        API: {
            "id": "uuid",
            "name": "workflow_name",
            "definition": {
                "steps": [
                    {"type": "HTTPS GET Request", "args": {"url": "..."}}
                ]
            }
        }
        
        Worker: WorkflowDefinition(
            name="workflow_name",
            nodes=[WorkflowNode(id="step_0", type="http_get", params={...})]
        )
        """
        steps = api_workflow.get("definition", {}).get("steps", [])
        nodes = []

        for i, step in enumerate(steps):
            # Mapear tipo de API a tipo de Worker
            api_type = step.get("type", "")
            worker_type = self._map_step_type(api_type)

            # Crear nodo con dependencias secuenciales
            node = WorkflowNode(
                id=f"step_{i}",
                type=worker_type,
                params=step.get("args", {}),
                depends_on=[f"step_{i-1}"] if i > 0 else []
            )
            nodes.append(node)

        return WorkflowDefinition(
            name=api_workflow.get("name", "unnamed_workflow"),
            nodes=nodes
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

            # ✅ AGREGAR: Log del resultado, borrar despues
            # ✅ AGREGAR: Logging detallado del resultado
            logger.info(f"[WorkerService] 🎯 Workflow ejecutado:")
            logger.info(f"   - Status: {result.status}")
            logger.info(f"   - Results keys: {list(result.results.keys())}")
            logger.info(f"   - Results: {result.results}")

            # 4. Mapear resultado al formato de la API
            api_status = self._map_worker_status_to_api(result.status)

            # ✅ AGREGAR DEBUG aquí, borrar despues
            logger.info(f"[WorkerService] 🔍 Worker status: {result.status} → API status: {api_status}")
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

        while not self._stop_flag:
            try:
                # Consultar workflows pendientes de la BD
                logger.debug("[WorkerService] 🔍 Consultando workflows pendientes en BD...")
                pending_workflows = self._get_pending_workflows_from_db()

                if not pending_workflows:
                    logger.debug("[WorkerService] 💤 No hay workflows pendientes")
                else:
                    logger.info(f"[WorkerService] 📋 Encontrados {len(pending_workflows)} workflow(s) pendiente(s)")

                    # Procesar cada workflow
                    for workflow in pending_workflows:
                        if self._execute_workflow(workflow):
                            self.stats["total_processed"] += 1

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
        logger.info(f"[WorkerService] 🚀 Iniciando servicio en modo bloqueante...")
        self._stop_flag = False
        
        try:
            self._poll_loop()
        except KeyboardInterrupt:
            logger.info("[WorkerService] ⏹️ Interrupción por teclado (Ctrl+C)")
            self.stop()

    def stop(self):
        """
        Detiene el servicio de polling.
        """
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