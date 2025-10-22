from abc import ABC, abstractmethod
from typing import Type, Dict, Any
from strategies.base import ITask
from strategies.Http_get import HttpGetTask
from strategies.notify_mock import NotifyMockTask
from strategies.save_db import SaveDBTask
from strategies.transform_simply import TransformSimpleTask
from strategies.validate_csv import ValidateCSVTask

"""
Para crear listado de tareas a utilizar
Task = http_get()
Task.register()
Task = notify_mock()
Task.register()
...
Task queda intanciada con ultima clase
"""

#Factory pattern
class TaskFactory(ABC):
    _registry = {}

    def register(self, type:str):
        task_type = type
        self._registry[task_type] = self.create()
        print(f"[TaskFactory] Registrada tarea: {task_type}")
    
    @abstractmethod
    def create():
        pass


    def list(self) -> list[Type[ITask]]:
        """
        Devuelve una lista de todas las clases de tareas registradas.
        (Usado por el endpoint /task-types para el frontend)
        """
        return list(self._registry.values())

    def clear(self):
        """
        Limpia el registro (útil para pruebas unitarias o reinicios).
        """
        self._registry.clear()


class http_get(TaskFactory):
    def create(self):
        return HttpGetTask()
    
class notify_mock(TaskFactory):
    def create(self):
        return NotifyMockTask()
    
class save_db(TaskFactory):
    def create(self):
        return SaveDBTask()
    
class transform_simply(TaskFactory):
    def create(self):
        return TransformSimpleTask()
    
class validate_csv(TaskFactory):
   def create(self):
        return ValidateCSVTask() 

