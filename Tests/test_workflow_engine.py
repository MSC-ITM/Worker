# tests/test_workflow_engine.py
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import json
from Worker.workflow.workflow_models import WorkflowDefinition, WorkflowResult
from Worker.workflow.workflow_persistence import WorkflowRepository, WorkflowRun
from Worker.workflow.workflow_engine import WorkflowEngine
from Worker.worker_engine import WorkerEngine
from Worker.factory import Taskregistry
from Worker.strategies.Http_get import HttpGetTask
from Worker.strategies.validate_csv import ValidateCSVTask
from Worker.strategies.transform_simply import TransformSimpleTask
from Worker.strategies.save_db import SaveDBTask
from Worker.strategies.notify_mock import NotifyMockTask

def iniciarTaskRegestry():
    T = Taskregistry()
    T.register(HttpGetTask)
    T.register(ValidateCSVTask)
    T.register(TransformSimpleTask)
    T.register(SaveDBTask)
    T.register(NotifyMockTask)
    return T

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def test_run_csv_workflow(tmp_path):
    # Arrange: ensure repo uses tmp db
    db_path = tmp_path / "test_workflows.db"
    repo = WorkflowRepository(db_path=str(db_path))
    T1 = iniciarTaskRegestry()
    worker = WorkerEngine(T1)
    engine = WorkflowEngine(worker=worker, repo=repo)

    wf_json = load_json("tests/seeds/workflow_csv.json")
    wf = WorkflowDefinition.from_dict(wf_json)

    # Act
    result = engine.run(wf)

    # Assert
    assert result.workflow_name == wf.name
    assert result.status in ("SUCCESS","PARTIAL_SUCCESS","FAILED")
    # results must include step1 and step2
    assert "step1" in result.results
    assert "step2" in result.results

    # DB should contain a workflow run record
    from sqlmodel import Session, select
    
    with Session(repo.engine) as session:
        runs = session.exec(select(WorkflowRun)).all()
        # Verifica que al menos se guardó un registro
        assert len(runs) > 0
        assert repo.engine is not None

def test_run_http_workflow():
    # Use a simple repo (file created in current dir; it's okay for CI local)
    repo = WorkflowRepository(db_path="tests/data/workflows_test_http.db")
    T = iniciarTaskRegestry()
    worker = WorkerEngine(T)
    engine = WorkflowEngine(worker=worker, repo=repo)

    wf_json = load_json("tests/seeds/workflow_http.json")
    wf = WorkflowDefinition.from_dict(wf_json)
    result = engine.run(wf)
    assert "get1" in result.results
    assert "notify1" in result.results
