from strategies.base import ITask
from typing import Dict, Any
import json
import time


class TaskDecorator(ITask):
    """
    Clase base para los decoradores de tareas.
    Implementa la misma interfaz que BaseTask (ITask) para poder anidarse.
    """
    def __init__(self, task: ITask):
        self._wrapped_Task = task

    def run(self, *args, **kwargs):
        """Debe ser implementado por los decoradores concretos."""
        raise NotImplementedError


class TimeDecorator(TaskDecorator):
    """
    Decorador de tiempo de ejecución.
    Mide cuánto tarda la tarea en completarse y captura errores sin romper el flujo.
    """
    def run(self, context: Dict[str, Any], params: Dict[str, Any]) -> Any:
        task_name = self._wrapped_Task.__class__.__name__
        start = time.time()
        #print(f"[{task_name}] ▶️ Inicio de ejecución de tarea")

        try:
            # ✅ Ejecuta la tarea envuelta
            result = self._wrapped_Task.run(context, params)
            elapsed = round(time.time() - start, 3)
            print(f"[{task_name}] ✅ Finalizada en {elapsed}s")
            return result

        except Exception as e:
            elapsed = round(time.time() - start, 3)
            print(f"[{task_name}] ❌ Error tras {elapsed}s: {e}")

            # 🚫 En lugar de relanzar, delega el manejo al on_error() de la tarea
            if hasattr(self._wrapped_Task, "on_error"):
                return self._wrapped_Task.on_error(e)

            # fallback genérico
            return {"success": False, "error": str(e), "elapsed": elapsed}

class LoggingDecorator(TaskDecorator):
    """
    Decorador que imprime logs estructurados antes y después de la ejecución.
    """
    def run(self, context: Dict[str, Any], params: Dict[str, Any]) -> Any:
        task_name = self._wrapped_Task.__class__.__name__
        print(f"[{task_name}] 🧾 Registro de ejecución:")
        print(json.dumps(params, indent=2, ensure_ascii=False))

        try:
            result = self._wrapped_Task.run(context, params)
            print(f"[{task_name}] 📤 Resultado: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return result
        except Exception as e:
            if hasattr(self._wrapped_Task, "on_error"):
                return self._wrapped_Task.on_error(e)
            return {"success": False, "error": str(e)}
