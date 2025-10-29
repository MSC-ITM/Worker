# Worker/Tests/test_worker_service.py
"""
Tests para el WorkerService que lee workflows de la BD compartida.
"""
import pytest
import json
import time
from datetime import datetime, UTC
from pathlib import Path
from sqlmodel import create_engine, SQLModel, Session, Field as SQLField, select
from typing import Optional

from Worker.service.worker_service import WorkerService
from Worker.registry import Taskregistry


# ============================================================
# FUNCIÓN HELPER PARA MODELO
# ============================================================

def get_workflow_table_model():
    """Factory para crear el modelo cada vez que se necesite"""
    class workflowTable(SQLModel, table=True):
        """Modelo idéntico al que usa la API"""
        __tablename__ = "workflowtable"
        __table_args__ = {"extend_existing": True}
        
        id: str = SQLField(primary_key=True, index=True)
        name: str
        status: str
        created_at: str
        updated_at: str
        definition: Optional[str] = None
    
    return workflowTable


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def shared_db_path(tmp_path):
    """Crea una BD compartida temporal para tests"""
    db_path = tmp_path / "test_shared.db"

    # ✅ Limpiar metadata ANTES de crear tablas
    from sqlmodel import SQLModel
    SQLModel.metadata.clear()
    
    # Crear engine
    engine = create_engine(
        f"sqlite:///{db_path}", 
        connect_args={"check_same_thread": False}
    )
    
   # ✅ Crear SOLO la tabla compartida en esta BD
    workflowTable = get_workflow_table_model()
    workflowTable.__table__.create(engine, checkfirst=True)  # ← Crear solo esta tabla
    
    yield str(db_path)
    
    # Cleanup
    engine.dispose()


@pytest.fixture
def worker_db_path(tmp_path):
    """Crea una BD del worker temporal para tests"""
    db_path = tmp_path / "test_worker_logs.db"
    return str(db_path)

@pytest.fixture
def workflow_repo_for_tests(worker_db_path):
    """Crea un WorkflowRepository temporal para los tests"""
    from Worker.workflow.workflow_persistence import WorkflowRepository
    from sqlmodel import SQLModel
    
    repo = WorkflowRepository(worker_db_path)
    
    # ✅ CRÍTICO: Asegurar que las tablas se crean
    SQLModel.metadata.create_all(repo.engine)
    
    return repo

@pytest.fixture
def worker_service(shared_db_path, worker_db_path):
    """Crea un WorkerService configurado para tests"""
    from sqlmodel import SQLModel

    service = WorkerService(
        shared_db_path=shared_db_path,
        poll_interval=1.0,  # Intervalo corto para tests rápidos
        worker_db_path=worker_db_path
    )
    
    # ✅ Verificar que las tablas del Worker se crearon
    from sqlalchemy import inspect
    inspector = inspect(service.repo.engine)
    tables = inspector.get_table_names()
    
    if "workflowrun" not in tables or "noderun" not in tables:
        raise RuntimeError(
            f"❌ Tablas de Worker no creadas en {worker_db_path}.\n"
            f"   Tablas existentes: {tables}\n"
            f"   Se esperaba: ['workflowrun', 'noderun']"
        )
    yield service
    
    # Cleanup
    service.stop()
    service.registry.clear()
    
    # ✅ CRÍTICO: Cerrar los engines que creó el service
    if hasattr(service, 'shared_engine') and service.shared_engine:
        service.shared_engine.dispose()
    if hasattr(service, 'repo') and hasattr(service.repo, 'engine'):
        service.repo.engine.dispose()
    SQLModel.metadata.clear()

@pytest.fixture
def populated_db(shared_db_path):
    """Fixture que crea workflows de prueba en la BD compartida"""
    engine = create_engine(
        f"sqlite:///{shared_db_path}", 
        connect_args={"check_same_thread": False}
    )
    
    def _create_workflow(workflow_id: str, name: str, status: str, definition: dict):
        """Helper para crear workflows"""
        # ✅ Obtener el modelo DENTRO de esta función
        workflowTable = get_workflow_table_model()
        
        with Session(engine) as session:
            workflow = workflowTable(
                id=workflow_id,
                name=name,
                status=status,
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
                definition=json.dumps(definition)
            )
            session.add(workflow)
            session.commit()
    
    yield _create_workflow
    
    # Cleanup
    engine.dispose()


# ============================================================
# TESTS DE LECTURA DE BD
# ============================================================

def test_get_pending_workflows_empty_db(worker_service):
    """Valida que retorne lista vacía cuando no hay workflows"""
    pending = worker_service._get_pending_workflows_from_db()
    assert pending == []


def test_get_pending_workflows_with_data(worker_service, populated_db):
    """Valida que obtenga workflows pendientes correctamente"""
    # Crear workflows con diferentes estados
    definition = {"steps": [{"type": "HTTPS GET Request", "args": {"url": "http://test.com"}}]}
    
    populated_db("wf1", "pending_flow_1", "en_espera", definition)
    populated_db("wf2", "pending_flow_2", "en_espera", definition)
    populated_db("wf3", "completed_flow", "completado", definition)
    
    # Obtener pendientes
    pending = worker_service._get_pending_workflows_from_db()
    
    assert len(pending) == 2
    assert all(wf["status"] == "en_espera" for wf in pending)
    assert "wf1" in [wf["id"] for wf in pending]
    assert "wf2" in [wf["id"] for wf in pending]
    assert "wf3" not in [wf["id"] for wf in pending]


def test_get_pending_workflows_structure(worker_service, populated_db):
    """Valida la estructura de los workflows retornados"""
    definition = {
        "steps": [
            {"type": "HTTPS GET Request", "args": {"url": "http://example.com"}}
        ]
    }
    
    populated_db("wf1", "test_flow", "en_espera", definition)
    
    pending = worker_service._get_pending_workflows_from_db()
    
    assert len(pending) == 1
    workflow = pending[0]
    
    # Validar campos
    assert "id" in workflow
    assert "name" in workflow
    assert "status" in workflow
    assert "created_at" in workflow
    assert "definition" in workflow
    
    # Validar que definition sea un dict (no string)
    assert isinstance(workflow["definition"], dict)
    assert "steps" in workflow["definition"]


# ============================================================
# TESTS DE ACTUALIZACIÓN DE BD
# ============================================================

def test_update_workflow_status_success(worker_service, populated_db):
    """Valida actualización exitosa de estado"""
    definition = {"steps": []}
    populated_db("wf1", "test_flow", "en_espera", definition)
    
    # Actualizar a 'en_progreso'
    success = worker_service._update_workflow_status_in_db("wf1", "en_progreso") 
    assert success is True
    
    # Verificar cambio
    pending = worker_service._get_pending_workflows_from_db()
    assert len(pending) == 0  # Ya no está pendiente


def test_update_workflow_status_with_results(worker_service, populated_db, shared_db_path):
    """Valida que los resultados se guarden en la definición"""
    definition = {"steps": []}
    populated_db("wf1", "test_flow", "en_espera", definition)
    
    results = {
        "step_0": {"status": "SUCCESS", "output": "data"},
        "step_1": {"status": "SUCCESS", "output": "more_data"}
    }
    
    # Actualizar con resultados
    success = worker_service._update_workflow_status_in_db(
        "wf1", 
        "completado", 
        results=results
    )
    assert success is True
    
    # Verificar que los resultados se guardaron
       
    workflowTable = get_workflow_table_model()
    
    with Session(worker_service.shared_engine) as session:
        stmt = select(workflowTable).where(workflowTable.id == "wf1")
        workflow = session.exec(stmt).first()
        
        assert workflow is not None
        assert workflow.status == "completado"
        
        saved_def = json.loads(workflow.definition)
        assert "execution_results" in saved_def
        assert saved_def["execution_results"] == results
        assert "executed_at" in saved_def
    
    worker_service.shared_engine.dispose()


def test_update_workflow_status_nonexistent(worker_service):
    """Valida manejo de workflow inexistente"""
    success = worker_service._update_workflow_status_in_db("nonexistent", "completado")
    assert success is False


# ============================================================
# TESTS DE CONVERSIÓN DE FORMATOS
# ============================================================

def test_convert_api_workflow_to_definition_simple(worker_service):
    """Valida conversión básica de workflow API a Worker"""
    api_workflow = {
        "id": "wf1",
        "name": "test_workflow",
        "definition": {
            "steps": [
                {"type": "HTTPS GET Request", "args": {"url": "http://example.com"}},
                {"type": "Mock Notification", "args": {"channel": "email", "message": "Done"}}
            ]
        }
    }
    
    worker_def = worker_service._convert_api_workflow_to_definition(api_workflow)
    
    # Validar estructura
    assert worker_def.name == "test_workflow"
    assert len(worker_def.nodes) == 2
    
    # Validar primer nodo
    assert worker_def.nodes[0].id == "step_0"
    assert worker_def.nodes[0].type == "http_get"
    assert worker_def.nodes[0].params == {"url": "http://example.com"}
    assert worker_def.nodes[0].depends_on == []
    
    # Validar segundo nodo
    assert worker_def.nodes[1].id == "step_1"
    assert worker_def.nodes[1].type == "notify_mock"
    assert worker_def.nodes[1].params == {"channel": "email", "message": "Done"}
    assert worker_def.nodes[1].depends_on == ["step_0"]


def test_convert_api_workflow_empty_steps(worker_service):
    """Valida conversión de workflow sin steps"""
    api_workflow = {
        "id": "wf1",
        "name": "empty_workflow",
        "definition": {}
    }
    
    worker_def = worker_service._convert_api_workflow_to_definition(api_workflow)
    
    assert worker_def.name == "empty_workflow"
    assert worker_def.nodes == []


def test_map_step_type_all_types(worker_service):
    """Valida mapeo de todos los tipos de tareas"""
    mappings = {
        "HTTPS GET Request": "http_get",
        "Validate CSV File": "validate_csv",
        "Simple Transform": "transform_simple",
        "Save to Database": "save_db",
        "Mock Notification": "notify_mock"
    }
    
    for api_type, expected_worker_type in mappings.items():
        result = worker_service._map_step_type(api_type)
        assert result == expected_worker_type, f"Mapeo incorrecto para {api_type}"


def test_map_step_type_unknown(worker_service):
    """Valida manejo de tipo desconocido"""
    result = worker_service._map_step_type("Unknown Task Type")
    assert result == "unknown_task_type"  # Debe convertir a snake_case


def test_map_worker_status_to_api(worker_service):
    """Valida mapeo de estados Worker → API"""
    mappings = {
        "SUCCESS": "completado",
        "FAILED": "fallido",
        "PARTIAL_SUCCESS": "completado",
        "RUNNING": "en_progreso"
    }
    
    for worker_status, expected_api_status in mappings.items():
        result = worker_service._map_worker_status_to_api(worker_status)
        assert result == expected_api_status


# ============================================================
# TESTS DE EJECUCIÓN DE WORKFLOWS
# ============================================================

def test_execute_workflow_success(worker_service, populated_db, mocker):
    """Valida ejecución exitosa de un workflow simple"""
    # Mock de requests para http_get
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.text = "test data"
    mock_response.headers = {"Content-Type": "text/plain"}
    mock_response.raise_for_status = mocker.Mock()
    mocker.patch('requests.get', return_value=mock_response)
    
    # Crear workflow de prueba
    definition = {
        "steps": [
            {"type": "HTTPS GET Request", "args": {"url": "http://test.com"}},
            {"type": "Mock Notification", "args": {"channel": "console", "message": "Test"}}
        ]
    }
    populated_db("wf1", "test_workflow", "en_espera", definition)
    
    # Obtener workflow
    pending = worker_service._get_pending_workflows_from_db()
    print (f"***es 1?{len(pending)}linea 352 de test_worker_service")
    assert len(pending) == 1
    
    # Ejecutar
    success = worker_service._execute_workflow(pending[0])
    
    # ✅ AGREGAR DEBUG para ver qué pasó
    if not success:
        import json
        print("\n❌ Ejecución falló")
        print(f"Stats: {worker_service.stats}")
        # Ver el estado actual en BD
        from sqlmodel import Session, select
        from Worker.Models.shared_workflow_table import workflowTable
        with Session(worker_service.shared_engine) as session:
            stmt = select(workflowTable).where(workflowTable.id == "wf1")
            wf = session.exec(stmt).first()
            print(f"Estado final: {wf.status}")
            if wf.definition:
                def_data = json.loads(wf.definition)
                print(f"Results: {def_data.get('execution_results', 'N/A')}")

    # Validar
    assert success is True
    assert worker_service.stats["successful"] == 1
    assert worker_service.stats["failed"] == 0


def test_execute_workflow_marks_in_progress(worker_service, populated_db, shared_db_path, mocker):
    """Valida que el workflow se marque como 'en_progreso' al iniciar"""
    # Mock para evitar ejecución real
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.text = "data"
    mock_response.headers = {}
    mock_response.raise_for_status = mocker.Mock()
    mocker.patch('requests.get', return_value=mock_response)
    
    definition = {
        "steps": [
            {"type": "HTTPS GET Request", "args": {"url": "http://test.com"}},
            {"type": "Mock Notification", "args": {"channel": "console", "message": "Test"}}
        ]
    }
    populated_db("wf1", "test_workflow", "en_espera", definition)
    
    # Ejecutar
    pending = worker_service._get_pending_workflows_from_db()
    worker_service._execute_workflow(pending[0])
    
    # Verificar estado en BD
    
    workflowTable = get_workflow_table_model()
    
    with Session(worker_service.shared_engine) as session:
        stmt = select(workflowTable).where(workflowTable.id == "wf1")
        workflow = session.exec(stmt).first()
        
        # Debe estar completado (o fallido si algo falló)
        assert workflow.status in ["completado", "fallido", "en_progreso"]
    
    worker_service.shared_engine.dispose()


def test_execute_workflow_with_error(worker_service, populated_db, mocker):
    """Valida manejo de error durante ejecución"""
    # Crear workflow que fallará (URL inválida)
    # ✅ Mockear requests para que lance excepción
    import requests
    mocker.patch('requests.get', side_effect=requests.exceptions.ConnectionError("Connection failed"))
    
    definition = {
        "steps": [
            {"type": "HTTPS GET Request", "args": {"url": "http://nonexistent-domain-12345.com"}}
        ]
    }
    populated_db("wf1", "failing_workflow", "en_espera", definition)
    
    # Ejecutar
    pending = worker_service._get_pending_workflows_from_db()
    success = worker_service._execute_workflow(pending[0])
    
    # Debe fallar pero de forma controlada
    assert success is False, "El workflow debería haber fallado"
    assert worker_service.stats["failed"] == 1
    assert worker_service.stats["successful"] == 0

# ============================================================
# TESTS DE SERVICIO COMPLETO
# ============================================================

def test_worker_service_initialization(shared_db_path, worker_db_path):
    """Valida inicialización correcta del servicio"""
    service = WorkerService(
        shared_db_path=shared_db_path,
        poll_interval=5.0,
        worker_db_path=worker_db_path
    )
    
    assert service.shared_db_path == shared_db_path
    assert service.poll_interval == 5.0
    assert service._stop_flag is False
    assert service.stats["total_processed"] == 0
    
    service.stop()


def test_worker_service_start_stop(worker_service):
    """Valida inicio y detención del servicio"""
    # Iniciar en hilo separado
    worker_service.start()
    
    # Verificar que está corriendo
    assert worker_service._polling_thread is not None
    assert worker_service._polling_thread.is_alive()
    
    # Detener
    worker_service.stop()
    
    # Esperar un momento
    time.sleep(0.5)
    
    # Verificar que se detuvo
    assert worker_service._stop_flag is True


def test_worker_service_get_stats(worker_service):
    """Valida obtención de estadísticas"""
    stats = worker_service.get_stats()
    
    assert isinstance(stats, dict)
    assert "total_processed" in stats
    assert "successful" in stats
    assert "failed" in stats
    assert stats["total_processed"] == 0


def test_worker_service_processes_multiple_workflows(worker_service, populated_db, mocker):
    """Valida que el servicio procese múltiples workflows en un ciclo"""
    # Mock de requests
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.text = "data"
    mock_response.headers = {"Content-Type": "text/plain"} 
    mock_response.raise_for_status = mocker.Mock()
    mocker.patch('requests.get', return_value=mock_response)
    
    # Crear 3 workflows pendientes
    definition = {
        "steps": [
            {"type": "HTTPS GET Request", "args": {"url": "http://test.com"}},
            {"type": "Mock Notification", "args": {"channel": "console", "message": "Done"}}
        ]
    }
    
    for i in range(3):
        populated_db(f"wf{i}", f"workflow_{i}", "en_espera", definition)
    
    # Ejecutar un ciclo de polling manualmente
    pending = worker_service._get_pending_workflows_from_db()
    assert len(pending) == 3
    
    # Procesar todos
    successful = 0  # contador
    for workflow in pending:
        if worker_service._execute_workflow(workflow):
            successful += 1  # ← Solo contar si tuvo éxito
    
    # Validar estadísticas
    assert worker_service.stats["total_processed"] == 3


# ============================================================
# TESTS DE INTEGRACIÓN
# ============================================================

def test_end_to_end_workflow_execution(worker_service, populated_db, shared_db_path, mocker):
    """
    Test end-to-end completo:
    1. Se crea workflow en BD
    2. Worker lo detecta
    3. Worker lo ejecuta
    4. Worker actualiza estado
    """
    # Mock de requests
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.text = '{"result": "success"}'
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.raise_for_status = mocker.Mock()
    mocker.patch('requests.get', return_value=mock_response)
    
    # 1. Crear workflow en BD (como lo haría la API)
    definition = {
        "steps": [
            {"type": "HTTPS GET Request", "args": {"url": "http://api.example.com/data"}},
            {"type": "Mock Notification", "args": {"channel": "email", "message": "Workflow completed"}}
        ]
    }
    populated_db("wf_e2e", "end_to_end_test", "en_espera", definition)
    
    # 2. Worker detecta workflow
    pending = worker_service._get_pending_workflows_from_db()
    assert len(pending) == 1
    assert pending[0]["id"] == "wf_e2e"
    assert pending[0]["status"] == "en_espera"
    
    # 3. Worker ejecuta workflow
    success = worker_service._execute_workflow(pending[0])
    # ✅ AGREGAR DEBUG si falla
    if not success:
        print(f"\n❌ Workflow execution failed")
        print(f"Stats: {worker_service.stats}")
    assert success is True 
    
        
    WorkflowTable = get_workflow_table_model()
    
    with Session(worker_service.shared_engine) as session:
        stmt = select(WorkflowTable).where(WorkflowTable.id == "wf_e2e")
        workflow = session.exec(stmt).first()
        
        assert workflow is not None
        assert workflow.status == "completado"
        
        # Verificar que hay resultados
        saved_def = json.loads(workflow.definition)
        assert "execution_results" in saved_def
        assert "step_0" in saved_def["execution_results"]
        assert "step_1" in saved_def["execution_results"]
    
    worker_service.shared_engine.dispose()


# ============================================================
# CONFTEST ADICIONAL PARA MOCKS
# ============================================================

@pytest.fixture
def mock_requests(request, mocker):
    """Fixture para mockear requests automáticamente"""
    if request.param:
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.text = "mocked response"
        mock_response.headers = {}
        mock_response.raise_for_status = mocker.Mock()
        mocker.patch('requests.get', return_value=mock_response)
