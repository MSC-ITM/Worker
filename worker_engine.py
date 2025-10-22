# worker/worker_engine.py
import traceback
from datetime import datetime
from Borrador_FactoryM import TaskFactory
from strategies import base
from Task_command import TaskCommand
from Borrador_decorador import timedecorator


class WorkerEngine:
    def __init__(self, registry:TaskFactory):
        self.registry = registry
    """Motor principal del Worker. Ejecuta comandos encolados."""

    def execute_command(self, command: TaskCommand, context={}):
        print(f"[Worker] Ejecutando {command}")

        try:
            # 1️⃣ Crear instancia de la tarea (Strategy) desde el registro		
            #task = self.registry.create(command.type)
            task = timedecorator(self.registry.create(command.type))

            # # 2️⃣ Validar parámetros antes de ejecutar y 3️⃣ Ejecutar la tarea
            result = task.run(context, command.params)
            print(task.run.__name__)
            print(task.run.__doc__) 
            
            # 4️⃣ Registrar éxito y devolver resultado
            print(f"[Worker] ✅ Tarea '{command.type}' completada exitosamente")
            return {
                "status": "SUCCESS",
                "run_id": command.run_id,
                "node_key": command.node_key,
                "result": result,
                "finished_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            # 5️⃣ Manejo de error y logging
            print(f"[Worker] ❌ Error ejecutando {command}: {e}")
            traceback.print_exc()
            return {
                "status": "FAILED",
                "run_id": command.run_id,
                "node_key": command.node_key,
                "error": str(e),
                "finished_at": datetime.utcnow().isoformat()
            }
