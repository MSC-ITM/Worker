# worker/worker_engine.py
import traceback
from datetime import datetime
from Worker.factory import Taskregistry
#from Worker.Borrador_FactoryM import TaskFactory
from Worker.strategies import base
from Worker.Task_command import TaskCommand
from Worker.decorador import TimeDecorator
from Worker.config.decoradores_config import TASK_DECORATOR_MAP


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

        # 1️⃣ Crear instancia de la tarea (Strategy) desde el registro	
        task = self.registry.create(command.type)
        if not task:
            raise ValueError(f"Tarea no registrada: {command.type}")
        # 3️⃣ Aplicar decoradores configurados
        task = self._apply_decorators(task, command.type)

        # 4️⃣ Ejecutar flujo
        context = {}

        try:

            # # 2️⃣ Validar parámetros antes de ejecutar y 3️⃣ Ejecutar la tarea
            result = task.run(context, command.params)
            print("")
            # 4️⃣ Registrar éxito y devolver resultado
            print(f"[Worker] ✅ Tarea '{command.type}' completada")
            return {
                "status": "SUCCESS",
                "run_id": command.run_id,
                "node_key": command.node_key,
                "result": result,
            }

        except Exception as e:
            # si el decorador no lo manejó, aún tienes fallback
            print(f"[Worker] ❌ Error ejecutando {command}: {e}")
            return {"status": "FAILED", "error": str(e)}