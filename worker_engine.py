# worker/worker_engine.py
import traceback
from datetime import datetime
from registry import Taskregistry
from Task_command import TaskCommand
from config.decoradores_config import TASK_DECORATOR_MAP


class WorkerEngine:
    def __init__(self, registry:Taskregistry):
        self.registry = registry
    """
    Orquestador principal de ejecución de tareas (Worker). Ejecuta comandos encolados
    Aplica decoradores de forma automática para instrumentar las tareas.
    """
    def _apply_decorators(self, task, task_id:str):
        """Aplica decoradores según el tipo de tarea."""
        decorated_task = task

        # Obtiene lista de decoradores registrados para este tipo
        decorators = TASK_DECORATOR_MAP.get(task_id, [])

        for decorator_cls in decorators:
            decorated_task = decorator_cls(decorated_task)

        return decorated_task
    
    def execute_command(self, command: TaskCommand, context=None):
        print(f"[Worker] ▶️ Ejecutando {command.type} (node={command.node_key}, run={command.run_id})")
        # Inicializar context si es None
        if context is None:
            context = {}    

        # 1️⃣ Crear instancia de la tarea usando el registro (Factory Method indirecto)
        try:
            task = self.registry.create(command.type)
        except ValueError as e:
            print(f"[Worker] ❌ Error: tipo de tarea no registrada '{command.type}'")
            return {"status": "FAILED", "error": str(e)}

        # 2️⃣ Aplicar decoradores
        task = self._apply_decorators(task, command.type)

        # 3️⃣ Ejecutar con manejo de errores controlado
        try:
            result = task.run(context, command.params)
            print(f"[Worker] ✅ Tarea '{command.type}' completada correctamente.")
            return {
                "status": "SUCCESS",
                "run_id": command.run_id,
                "node_key": command.node_key,
                "result": result,
            }

        except Exception as e:
            # Captura genérica (en caso de que el decorador no haya manejado)
            print(f"[Worker] ❌ Error ejecutando {command.type}: {e}")
            return {
                "status": "FAILED",
                "run_id": command.run_id,
                "node_key": command.node_key,
                "error": str(e),
            }
