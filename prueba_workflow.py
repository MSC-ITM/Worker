from workflow.workflow_engine import WorkflowEngine
from workflow.workflow_models import WorkflowDefinition
from Worker.workflow.workflow_persistence import WorkflowRepository
from worker_engine import WorkerEngine
import json

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


workflow_data = {
    "name": "Carga y Transformación",
    "nodes": [
        {
            "id": "step1",
            "type": "validate_csv",
            "params": {"path": "data/sample.csv", "columns": ["id", "nombre", "edad"]}
        },
        {
            "id": "step2",
            "type": "transform_simple",
            "depends_on": ["step1"],
            "params": {
                "input_path": "data/sample.csv",
                "output_path": "data/output.csv",
                "select_columns": ["id", "nombre"],
                "rename_map": {"nombre": "NombreCompleto"}
            }
        },
        {
            "id": "step3",
            "type": "save_db",
            "depends_on": ["step2"],
            "params": {
                "path": "data/output.csv",
                "table": "usuarios",
                "mode": "replace"
            }
        }
    ]
}

# workflow = WorkflowDefinition.from_dict(workflow_data)
# engine = WorkflowEngine(worker=WorkerEngine(T2))
# result = engine.run(workflow)

"""con persistencia"""
repo = WorkflowRepository()
engine = WorkflowEngine(worker=WorkerEngine(T2), repo=repo)
workflow = WorkflowDefinition.from_dict(workflow_data)
result = engine.run(workflow)

print(json.dumps(result.__dict__, indent=2, ensure_ascii=False))
