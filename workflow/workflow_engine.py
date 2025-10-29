# worker/workflow/workflow_engine.py
from typing import Dict, Any
from Worker.worker_engine import WorkerEngine
from Worker.workflow.workflow_models import WorkflowDefinition, WorkflowResult
from Worker.workflow.workflow_persistence import WorkflowRepository
from Worker.Task_command import TaskCommand 
import json
from datetime import datetime

class WorkflowEngine:
    """
    Orquestador de flujos de trabajo.
    Coordina la ejecución secuencial (o futura paralela) de tareas con dependencias.
    """
    def __init__(self, worker: WorkerEngine, repo: WorkflowRepository):
        self.worker = worker
        self.repo = repo    

    def run(self, workflow: WorkflowDefinition) -> WorkflowResult:
        print(f"[WorkflowEngine] ▶️ Ejecutando workflow: {workflow.name}")
        start_time = datetime.now()

        context: Dict[str, Any] = {}
        results: Dict[str, Any] = {}
        node_status: Dict[str, str] = {}  # SUCCESS | FAILED | SKIPPED

        # 🔹 Determinar orden de ejecución según dependencias
        pending = {node.id: node for node in workflow.nodes}
        executed = set()

        workflow_id = None  # se asignará después de crear el registro base

        # Registrar inicio de workflow
        with self.repo.engine.connect() as conn:
            workflow_id = self.repo.save_workflow_run(
                workflow_name=workflow.name,
                status="RUNNING",
                results={},
                started_at=start_time,
                finished_at=start_time
            )

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
                    node_start = datetime.now()
                    print(f"[WorkflowEngine] ▶️ Ejecutando nodo: {node.id} ({node.type})")                    
                    command = TaskCommand(
                        run_id=f"{workflow.name}_{node.id}",
                        node_key=node.id,
                        type=node.type,
                        params=node.params
                    )

                    # Ejecutar tarea con Worker
                    task_result = self.worker.execute_command(command)
                    result_data = task_result.get("result")
                    node_end = datetime.now()

                     # Determinar estado de la tarea
                    if task_result.get("status") == "SUCCESS" and not (
                        isinstance(result_data, dict) and result_data.get("success") is False):
                        status = "SUCCESS"
                        print(f"[WorkflowEngine] ✅ Nodo '{node_id}' completado correctamente.")
                    else:
                        status = "FAILED"
                        print(f"[WorkflowEngine] ❌ Nodo '{node_id}' falló durante la ejecución.")

                    # Guardar resultados
                    node_status[node.id] = status
                    results[node.id] = task_result.get("result")
                    context[node.id] = task_result.get("result")

                    # Persistir nodo
                    self.repo.save_node_run(
                        workflow_id=workflow_id,
                        node_id=node_id,
                        node_type=node.type,
                        status=status,
                        started_at=node_start,
                        finished_at=node_end,
                        result=result_data or {}
                    )

                    executed.add(node.id)
                    del pending[node_id]
                    progress = True

            if not progress:
                raise RuntimeError("❌ No se puede continuar: dependencias circulares o tareas bloqueadas.")
            
        # Determinar estado global del workflow
        end_time = datetime.now()
        if all(s == "SUCCESS" for s in node_status.values()):
            wf_status = "SUCCESS"
        elif any(s == "SUCCESS" for s in node_status.values()):
            wf_status = "PARTIAL_SUCCESS"
        else:
            wf_status = "FAILED"

        # Actualiza el status del workflow
        self.repo.update_workflow_run(
            workflow_id=workflow_id,
            status=wf_status,
            results=results,
            finished_at=end_time
        )

        print(f"[WorkflowEngine] 🏁 Workflow completado: {workflow.name} con estado {wf_status}")
        return WorkflowResult(workflow_name=workflow.name, status=wf_status, results=results)
