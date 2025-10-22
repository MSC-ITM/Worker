
from worker_engine import WorkerEngine
from Task_command import TaskCommand
from factory import Taskregistry
from strategies.Http_get import HttpGetTask
from strategies.validate_csv import ValidateCSVTask
from strategies.transform_simply import TransformSimpleTask
from strategies.save_db import SaveDBTask
from strategies.notify_mock import NotifyMockTask

T2 = Taskregistry()
T2.register(HttpGetTask)
T2.register(ValidateCSVTask)
T2.register(TransformSimpleTask)
T2.register(SaveDBTask)
T2.register(NotifyMockTask)
print ("--"*30)

engine = WorkerEngine(T2)

command = TaskCommand(
    run_id="RUN-001",
    node_key="node1",
    type="http_get",
    params={"url": "https://www.outlook.com"}
)

context = {"run_id": "RUN-001"}
result = engine.execute_command(command, context)

print("---"*30)

command = TaskCommand(
    run_id="RUN-TEST1",
    node_key="valcsv1",
    type="validate_csv",
    params={
        "path": "data/sample.csv",
        "columns": ["id", "nombre", "edad"]
    }
)
result = engine.execute_command(command)
print(result)
print("---"*30)

command = TaskCommand(
    run_id="RUN-TEST2",
    node_key="save_db1",
    type="save_db",
    params={
        "path": "data/sample.csv",
        "table": "usuarios",
        "mode": "replace"
    }
)
result = engine.execute_command(command)
print(result)
print("---"*30)
command = TaskCommand(
    run_id="RUN-TEST3",
    node_key="transform1",
    type="transform_simple",
    params={
        "input_path": "data/sample.csv",
        "output_path": "data/output.csv",
        "select_columns": ["id", "nombre", "ciudad"],
        "rename_map": {"nombre": "NombreCompleto"}
    }
)
result = engine.execute_command(command)
print(result)
print("---"*30)