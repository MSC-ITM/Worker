# tests/test_planner_facade.py
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from Worker.planner.planner_facade import PlannerFacade
from Worker.workflow.workflow_models import WorkflowDefinition
from Worker.workflow.workflow_engine import WorkflowEngine
from Worker.workflow.workflow_persistence import WorkflowRepository
from Worker.worker_engine import WorkerEngine



def test_mock_planner_creates_valid_workflow():
    planner = PlannerFacade()
    wf = planner.plan_workflow("procesar csv", {"path": "tests/seeds/sample.csv"})
    assert isinstance(wf, WorkflowDefinition)
    assert "Validación" in wf.name or any(n.type == "validate_csv" for n in wf.nodes)

def test_mock_planner_respects_context():
    planner = PlannerFacade()
    ctx = {"type": "csv", "path": "tests/seeds/sample.csv", "columns": ["id","nombre"]}
    wf = planner.plan_workflow("any", ctx)
    # check nodes refer to given path
    assert wf.nodes[0].params["path"] == "tests/seeds/sample.csv"
