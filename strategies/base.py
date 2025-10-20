from abc import ABC, abstractmethod
from typing import Any, Dict

class ITask(ABC):
    @abstractmethod
    def execute(self, params: dict) -> dict:
        """Ejecuta la tarea y retorna resultado"""
        pass
    
    @abstractmethod
    def validate_params(self, params: dict) -> bool:
        """Valida parámetros antes de ejecutar"""
        pass

    @abstractmethod
    def get_param_schema(self) -> Dict[str, Any]:
        """
        Retorna el schema JSON de parámetros esperados.
        Útil para documentación y UI.
        """
        return {}
    
