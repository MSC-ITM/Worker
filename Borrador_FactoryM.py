from abc import ABC, abstractmethod
from typing import Type, Dict, Any
from strategies.base import ITask
from strategies.Http_get import HttpGetTask
from strategies.notify_mock import NotifyMockTask
from strategies.save_db import SaveDBTask
from strategies.transform_simply import TransformSimpleTask
from strategies.validate_csv import ValidateCSVTask

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

    # ======== Hooks opcionales (Template Method) ========

    def before(self, params: Dict[str, Any]):
        """
        Hook opcional que se ejecuta antes de `execute()`.
        Puede ser usado para inicialización, logging o métricas.
        """
        pass

    def after(self, result: Any):
        """
        Hook opcional que se ejecuta después de `execute()`.
        Permite registrar resultados, métricas o limpieza de recursos.
        """
        pass

    def on_error(self, error: Exception):
        """
        Hook opcional que se ejecuta si ocurre un error durante `execute()`.
        Permite manejar fallos, reintentos o reportes personalizados.
        """
        print(f"[{self.__class__.__name__}] Error durante ejecución: {error}")

    # ======== Plantilla de ejecución ========

    def run(self, context: Dict[str, Any], params: Dict[str, Any]) -> Any:
        """
        Define el ciclo de vida estándar de ejecución de una tarea.
        Este método puede ser llamado por el Worker o el Orchestrator.

        Flujo:
        1. before(params)
        2. validate_params(params)
        3. execute(context, params)
        4. after(result)

        Maneja excepciones y llama `on_error()` si ocurre un fallo.

        Returns:
            Resultado de `execute()`, o relanza la excepción capturada.
        """
        self.before(params)
        try:
            self.validate_params(params)
            result = self.execute(context, params)
            self.after(result)
            return result
        except Exception as e:
            self.on_error(e)
            raise

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

