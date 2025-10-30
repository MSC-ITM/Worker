import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from abc import ABC, abstractmethod
from typing import Type, Dict, Any
from Worker.strategies.base import ITask
from Worker.strategies.Http_get import HttpGetTask
from Worker.strategies.notify_mock import NotifyMockTask
from Worker.strategies.save_db import SaveDBTask
from Worker.strategies.transform_simply import TransformSimpleTask
from Worker.strategies.validate_csv import ValidateCSVTask

#Factory pattern
class TaskFactory(ABC):
   
    @abstractmethod
    def create():
        pass



class http_getFactory(TaskFactory):
    def create(self)-> ITask:
        return HttpGetTask()
    
class notify_mockFactory(TaskFactory):
    def create(self)-> ITask:
        return NotifyMockTask()
    
class save_dbFactory(TaskFactory):
    def create(self)-> ITask:
        return SaveDBTask()
    
class transform_simplyFactory(TaskFactory):
    def create(self)-> ITask:
        return TransformSimpleTask()
    
class validate_csvFactory(TaskFactory):
   def create(self)-> ITask:
        return ValidateCSVTask()

# === Clase Directora (elige la fábrica según tipo) ===
class TaskFactoryDirector(TaskFactory):
    All_posible_tasks = {"http_get":http_getFactory,
                             "validate_csv": validate_csvFactory, 
                             "save_db":save_dbFactory,
                             "notify_mock":notify_mockFactory, 
                             "transform_simple":transform_simplyFactory
                             }
    def create(self, task_type: str) -> ITask:
        if task_type in self.All_posible_tasks:
            return self.All_posible_tasks[task_type]().create()
        else:
            raise ValueError(f"Tipo de tarea desconocido: {task_type}") 

