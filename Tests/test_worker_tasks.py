# tests/test_worker_tasks.py
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from Worker.worker_engine import WorkerEngine
from Worker.worker_engine import TaskCommand  # if TaskCommand lives elsewhere adjust import
from Worker.planner.planner_facade import PlannerFacade
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

def test_validate_and_save(tmp_path):
    # create a copy of seed CSV into tmp_path
    src = "tests/seeds/sample.csv"
    dst = tmp_path / "sample.csv"
    import shutil
    shutil.copy(src, dst)

    # run validate_csv and save_db via WorkerEngine directly
    T2 = iniciarTaskRegestry()
    engine = WorkerEngine(T2)

    cmd_validate = TaskCommand(run_id="T1", node_key="v1", type="validate_csv",
                               params={"path": str(dst), "columns": ["id","nombre","edad"]})
    r1 = engine.execute_command(cmd_validate)
    assert r1["status"] == "SUCCESS"
    assert isinstance(r1["result"], dict)

    cmd_save = TaskCommand(run_id="T2", node_key="s1", type="save_db",
                           params={"path": str(dst), "table": "test_users", "mode": "replace"})
    r2 = engine.execute_command(cmd_save)
    assert r2["status"] == "SUCCESS"
