from Worker.strategies.base import ITask
from Worker.FactoryM import TaskFactoryDirector
from typing import Type, Dict


class Taskregistry():
    """
    Implementa el Factory Method para crear catálogo de estrategias de tareas disponibles en el sistema.
    Permite registrar y crear instancias de tareas concretas.
    """

    def __init__(self):
        self._registry: Dict[str, Type[ITask]] = {}
    
    def register(self, task_name:str):
        """
        Registra una clase concreta de tarea en el catálogo global.
        Debe tener un atributo 'type' único.
        """
        TaskFactory= TaskFactoryDirector()

        if task_name not in TaskFactory.All_posible_tasks:
            raise ValueError(f"La clase {task_name} no está definida como tarea.")

        if task_name in self._registry:
            raise ValueError(f"El tipo de tarea '{task_name}' ya está registrado.")
        
        Taskclas=TaskFactory.create(task_name).__class__
        self._registry[task_name] = Taskclas
        print(f"[Taskregistry] Registrada tarea: {task_name}")

    
    def create(self, task_type: str) -> ITask:
        """Devuelve la instancia de la clase Task (concreteproduct) a utlizar"""
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
        print("[Taskregistry] 🧹 Registro limpiado.")

