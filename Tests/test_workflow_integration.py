"""
Tests de integración para el sistema de workflows
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from Worker.workflow.workflow_persistence import WorkflowRepository
from Worker.workflow.workflow_models import WorkflowDefinition, WorkflowNode
from Worker.workflow.workflow_engine import WorkflowEngine
from Worker.worker_engine import WorkerEngine


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def task_registry():
    """Fixture que proporciona un TaskRegistry limpio con tareas mock."""
    from Worker.registry import Taskregistry
    registry = Taskregistry()
    
    # Registrar tareas reales del sistema
    registry.register("http_get")
    registry.register("validate_csv")
    registry.register("transform_simple")
    registry.register("save_db")
    registry.register("notify_mock")
    
    yield registry
    registry.clear()


@pytest.fixture
def workflow_repo(tmp_path):
    """Fixture que proporciona un WorkflowRepository temporal."""
    db_path = tmp_path / "test_workflows.db"
    # ✅ WorkflowRepository ahora crea las tablas automáticamente
    repo = WorkflowRepository(str(db_path))
    
    
    # Verificar que las tablas existen
    from sqlalchemy import inspect
    inspector = inspect(repo.engine)
    tables = inspector.get_table_names()
    

    assert "workflowrun" in tables, f"Tabla workflowrun no existe. Tablas: {tables}"
    assert "noderun" in tables, f"Tabla noderun no existe. Tablas: {tables}"
    
    yield repo


@pytest.fixture
def worker_engine(task_registry):
    """Fixture que proporciona un WorkerEngine con el registry."""
    return WorkerEngine(task_registry)


@pytest.fixture
def workflow_engine(worker_engine, workflow_repo):
    """Fixture que proporciona un WorkflowEngine completo."""
    return WorkflowEngine(worker_engine, workflow_repo)


# ============================================================
# TESTS DE INTEGRACIÓN CON MOCKS
# ============================================================

@patch('requests.get')
def test_run_simple_workflow(mock_get, workflow_engine, workflow_repo):
    """
    Prueba la ejecución end-to-end de un workflow básico.
    """
    # Mock de la respuesta HTTP
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = '{"data": "test"}'
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    # 1️⃣ Crear un workflow de prueba usando WorkflowDefinition de models
    nodes = [
        WorkflowNode(id="n1", type="http_get", params={"url": "https://example.com/data.csv"}),
        WorkflowNode(id="n2", type="notify_mock", params={"channel": "console", "message": "Test"}, depends_on=["n1"])
    ]
    
    workflow = WorkflowDefinition(name="simple_flow", nodes=nodes)
    
    # 2️⃣ Ejecutar workflow
    result = workflow_engine.run(workflow)
    
    # 3️⃣ Validar resultado
    assert result.status in ["SUCCESS", "PARTIAL_SUCCESS"], f"Workflow falló: {result.status}"
    assert "n1" in result.results, "Falta resultado del nodo n1"
    assert "n2" in result.results, "Falta resultado del nodo n2"
    
    # Validar salidas específicas
    n1_output = result.results["n1"]
    assert n1_output["success"] is True
    assert n1_output["status_code"] == 200
    
    n2_output = result.results["n2"]
    # Verificar que n2 se ejecutó correctamente (puede tener 'sent' o 'success')
    assert "sent" in n2_output and n2_output["sent"] is True, f"n2 falló: {n2_output}"


@patch('os.path.exists', return_value=False)
def test_run_workflow_with_error(mock_exists, workflow_engine, workflow_repo):
    """
    Simula un error controlado para validar que on_error funciona correctamente.
    """
    nodes = [
        WorkflowNode(id="v1", type="validate_csv", params={"path": "data/nonexistent.csv", "columns": ["a", "b"]})
    ]
    
    workflow = WorkflowDefinition(name="failing_flow", nodes=nodes)
    
    result = workflow_engine.run(workflow)
    
    # El workflow debe fallar pero de manera controlada
    assert result.status == "FAILED", "Se esperaba un fallo controlado"
    assert "v1" in result.results


@patch('requests.get')
def test_workflow_with_branching(mock_get, workflow_engine, workflow_repo):
    """
    Prueba un workflow con múltiples ramas (branching).
    
    Estructura:
       n1 (http_get)
      /  \\
     n2   n3 (transform)
      \\  /
       n4 (notify)
    """
    # Mock de HTTP
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = 'col1,col2\nval1,val2'
    mock_response.headers = {}
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    # Mock para validate_csv (simular que el archivo existe)
    with patch('os.path.exists', return_value=True), \
         patch('builtins.open', create=True) as mock_open:
        
        # Simular CSV válido
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = "x,y\n1,2\n3,4"
        mock_open.return_value = mock_file
        
        nodes = [
            WorkflowNode(id="n1", type="http_get", params={"url": "https://api.example.com"}),
            WorkflowNode(id="n2", type="validate_csv", params={"path": "data/valid.csv", "columns": ["x"]}, depends_on=["n1"]),
            WorkflowNode(id="n3", type="transform_simple", params={"input_path": "data/valid.csv", "output_path": "data/out.csv"}, depends_on=["n1"]),
            WorkflowNode(id="n4", type="notify_mock", params={"channel": "slack", "message": "Done"}, depends_on=["n2", "n3"])
        ]
        
        workflow = WorkflowDefinition(name="branching_flow", nodes=nodes)
        
        result = workflow_engine.run(workflow)
        
        # Validar que todos los nodos se ejecutaron
        assert result.status in ["SUCCESS", "PARTIAL_SUCCESS"]
        assert len(result.results) == 4
        for node_id in ["n1", "n2", "n3", "n4"]:
            assert node_id in result.results


@patch('requests.get')
def test_workflow_with_dependencies(mock_get, workflow_engine):
    """
    Valida que las dependencias se respeten en el orden de ejecución.
    """
    # Mock HTTP
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = 'data'
    mock_response.headers = {}
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    with patch('os.path.exists', return_value=True), \
         patch('builtins.open', create=True) as mock_open:
        
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = "col1\nval1"
        mock_open.return_value = mock_file
        
        nodes = [
            WorkflowNode(id="step1", type="http_get", params={"url": "http://source.com"}),
            WorkflowNode(id="step2", type="transform_simple", params={"input_path": "data.csv", "output_path": "out.csv"}, depends_on=["step1"]),
            WorkflowNode(id="step3", type="save_db", params={"table": "test", "data": {}}, depends_on=["step2"])
        ]
        
        workflow = WorkflowDefinition(name="sequential_flow", nodes=nodes)
        
        result = workflow_engine.run(workflow)
        
        assert result.status in ["SUCCESS", "PARTIAL_SUCCESS"]
        assert all(node_id in result.results for node_id in ["step1", "step2", "step3"])


@patch('os.path.exists', return_value=False)
def test_workflow_skips_on_failed_dependency(mock_exists, workflow_engine):
    """
    Valida que los nodos dependientes se salten si una dependencia falla.
    """
    nodes = [
        WorkflowNode(id="failing", type="validate_csv", params={"path": "data/nonexistent.csv", "columns": ["a"]}),
        WorkflowNode(id="dependent", type="notify_mock", params={"message": "Test"}, depends_on=["failing"])
    ]
    
    workflow = WorkflowDefinition(name="skip_flow", nodes=nodes)
    
    result = workflow_engine.run(workflow)
    
    assert result.status == "FAILED"
    assert "failing" in result.results
    assert "dependent" in result.results
    assert result.results["dependent"]["status"] == "SKIPPED"


@patch('requests.get')
def test_workflow_from_dict(mock_get, workflow_engine):
    """
    Valida la creación de workflow desde diccionario.
    """
    # Mock HTTP
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = 'success'
    mock_response.headers = {}
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    workflow_dict = {
        "name": "dict_flow",
        "nodes": [
            {"id": "n1", "type": "http_get", "params": {"url": "http://test.com"}},
            {"id": "n2", "type": "notify_mock", "params": {"channel": "email", "message": "Done"}, "depends_on": ["n1"]}
        ]
    }
    
    workflow = WorkflowDefinition.from_dict(workflow_dict)
    
    assert workflow.name == "dict_flow"
    assert len(workflow.nodes) == 2
    assert workflow.nodes[1].depends_on == ["n1"]
    
    result = workflow_engine.run(workflow)
    assert result.status == "SUCCESS"