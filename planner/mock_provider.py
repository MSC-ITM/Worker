# worker/planner/mock_provider.py
from typing import Dict, Any
from Worker.planner.interfaces import IProvider
from Worker.workflow.workflow_models import WorkflowDefinition


class MockProvider(IProvider):
    """
    Implementación sencilla para pruebas: genera workflows predecibles
    dependiendo de palabras clave en el 'goal'.
    """

    def suggest_workflow(self, goal: str, data_context: Dict[str, Any]) -> WorkflowDefinition:
        print(f"[MockProvider] Generando flujo mock para goal='{goal}'")

        goal_lower = (goal or "").lower()

        if "csv" in goal_lower or data_context.get("type") == "csv":
            wf = {
                "name": "Validación CSV automática",
                "nodes": [
                    {
                        "id": "validate",
                        "type": "validate_csv",
                        "params": {
                            "path": data_context.get("path", "tests/seeds/sample.csv"),
                            "columns": data_context.get("columns", ["id", "nombre", "edad"])
                        }
                    },
                    {
                        "id": "save",
                        "type": "save_db",
                        "depends_on": ["validate"],
                        "params": {
                            "path": data_context.get("path", "tests/seeds/sample.csv"),
                            "table": data_context.get("table", "usuarios"),
                            "mode": data_context.get("mode", "replace")
                        }
                    }
                ]
            }
        else:
            wf = {
                "name": "HTTP + Notify Workflow",
                "nodes": [
                    {
                        "id": "get",
                        "type": "http_get",
                        "params": {"url": data_context.get("url", "https://jsonplaceholder.typicode.com/todos/1")}
                    },
                    {
                        "id": "notify",
                        "type": "notify_mock",
                        "depends_on": ["get"],
                        "params": {"channel": "console", "message": "Mock notify after GET"}
                    }
                ]
            }

        return WorkflowDefinition.from_dict(wf)

