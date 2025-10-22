from strategies.base import ITask
from typing import Dict, Any
import time

class TaskDecorator(ITask):
    def __init__(self, Task:ITask):
        self._wrapped_Task = Task

    def run(self, *args, **kwargs):
        pass

class timedecorator(TaskDecorator):
    def run(self, context: Dict[str, Any], params: Dict[str, Any]) -> Any:
        task_name = self.__class__.__name__
        start = time.time()
        print(f"[{task_name}] ▶️ Inicio de ejecución de tarea")
        try:
            result = self._wrapped_Task.run(context, params)
            elapsed = round(time.time() - start, 3)
            print(f"[{task_name}] ✅ Finalizada en {elapsed}s")
            return result
        except Exception as e:
            elapsed = round(time.time() - start, 3)
            print(f"[{task_name}] ❌ Error tras {elapsed}s: {e}")
            raise