
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
print(result)

