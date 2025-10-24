from Worker.strategies.base import ITask
from typing import Type, Dict

"""
T2 = Taskregistry()
T2.register(HttpGetTask)
T2.register(ValidateCSVTask)
...
"""

#Factory pattern
class Taskregistry():
    """
    Catálogo de estrategias de tareas disponibles en el sistema.
    Permite registrar y crear instancias de tareas concretas.
    """

    def __init__(self):
        self._registry: Dict[str, Type[ITask]] = {}
    
    def register(self, task_cls: Type[ITask]):
        """
        Registra una clase concreta de tarea en el catálogo global.
        Debe tener un atributo 'type' único.
        """
        if not hasattr(task_cls, "type"):
            raise ValueError(f"La clase {task_cls.__name__} no define atributo 'type'.")

        task_type = getattr(task_cls, "type")

        if task_type in self._registry:
            raise ValueError(f"El tipo de tarea '{task_type}' ya está registrado.")

        self._registry[task_type] = task_cls
        print(f"[TaskRegistry] Registrada tarea: {task_type}")

    
    def create(self, task_type: str) -> ITask:
        if task_type not in self._registry:
            raise ValueError(f"Unknown task type: {task_type}")
        return self._registry[task_type]()
    
    def list(self) -> list[Type[ITask]]:
        """
        Devuelve una lista de todas las clases de tareas registradas.
        (Usado por el endpoint /task-types para el frontend)
        """
        return list(self._registry.values())


    def clear(self):
        """
        Limpia el registro actual (útil en tests).
        """
        self._registry.clear()
        print("[TaskRegistry] 🧹 Registro limpiado.")

