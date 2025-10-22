# worker/workflow/workflow_engine.py
from typing import Dict, Any
from worker_engine import WorkerEngine
from workflow.workflow_models import WorkflowDefinition, WorkflowResult
import json

class WorkflowEngine:
    """
    Orquestador de flujos de trabajo.
    Coordina la ejecución secuencial (o futura paralela) de tareas con dependencias.
    """
    def __init__(self, worker: WorkerEngine):
        self.worker = worker

    def run(self, workflow: WorkflowDefinition) -> WorkflowResult:
        print(f"[WorkflowEngine] ▶️ Ejecutando workflow: {workflow.name}")
        context: Dict[str, Any] = {}
        results: Dict[str, Any] = {}
        node_status: Dict[str, str] = {}  # SUCCESS | FAILED | SKIPPED

        # 🔹 Determinar orden de ejecución según dependencias
        pending = {node.id: node for node in workflow.nodes}
        executed = set()

        while pending:
            progress = False

            for node_id, node in list(pending.items()):
                deps = node.depends_on

                # Si alguna dependencia falló, saltar esta tarea
                if any(node_status.get(dep) == "FAILED" for dep in deps):
                    print(f"[WorkflowEngine] ⚠️ Saltando nodo '{node_id}' por dependencia fallida.")
                    node_status[node_id] = "SKIPPED"
                    results[node_id] = {
                        "status": "SKIPPED",
                        "reason": f"Dependencia fallida: {deps}"
                    }
                    executed.add(node_id)
                    del pending[node_id]
                    progress = True
                    continue

                # Ejecutar si todas las dependencias están completas
                if all(dep in executed for dep in node.depends_on):
                    print(f"[WorkflowEngine] ▶️ Ejecutando nodo: {node.id} ({node.type})")
                    from Task_command import TaskCommand  # importar aquí para evitar ciclos
                    command = TaskCommand(
                        run_id=f"{workflow.name}_{node.id}",
                        node_key=node.id,
                        type=node.type,
                        params=node.params
                    )

                    # Ejecutar tarea con Worker
                    task_result = self.worker.execute_command(command)
                    result_data = task_result.get("result")

                     # Determinar estado de la tarea
                    if task_result.get("status") == "SUCCESS" and not (
                        isinstance(result_data, dict) and result_data.get("success") is False):
                        node_status[node_id] = "SUCCESS"
                        print(f"[WorkflowEngine] ✅ Nodo '{node_id}' completado correctamente.")
                    else:
                        node_status[node_id] = "FAILED"
                        print(f"[WorkflowEngine] ❌ Nodo '{node_id}' falló durante la ejecución.")


                    # Guardar resultados
                    results[node.id] = task_result.get("result")
                    context[node.id] = task_result.get("result")
                    executed.add(node.id)
                    del pending[node_id]
                    progress = True

            if not progress:
                raise RuntimeError("❌ No se puede continuar: dependencias circulares o tareas bloqueadas.")
            
        # Determinar estado global del workflow
        if all(status == "SUCCESS" for status in node_status.values()):
            workflow_status = "SUCCESS"
        elif any(status == "SUCCESS" for status in node_status.values()):
            workflow_status = "PARTIAL_SUCCESS"
        else:
            workflow_status = "FAILED"

        print(f"[WorkflowEngine] 🏁 Workflow completado: {workflow.name} con estado {workflow_status}")
        return WorkflowResult(workflow_name=workflow.name, status=workflow_status, results=results)
