# worker/planner/interfaces.py
from abc import ABC, abstractmethod
from typing import Dict, Any
from workflow.workflow_models import WorkflowDefinition

class IProvider(ABC):
    """ Contrato para proveedores que generen (sugieran) WorkflowDefinition
    a partir de una descripción/goal y un contexto de datos.
    """

    @abstractmethod
    def suggest_workflow(self, goal: str, data_context: Dict[str, Any]) -> WorkflowDefinition:
        """
        Debe devolver un WorkflowDefinition creado a partir del 'goal' y 'data_context'.
        """
        pass
        #raise NotImplementedError