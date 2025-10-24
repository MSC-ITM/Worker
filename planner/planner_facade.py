# worker/planner/planner_facade.py
from typing import Dict, Any, Optional
from Worker.planner.interfaces import IProvider
from Worker.planner.mock_provider import MockProvider
from Worker.workflow.workflow_models import WorkflowDefinition


class PlannerFacade:
    """
    Fachada de alto nivel para generar workflows.
    Por defecto usa MockProvider, pero puedes pasar cualquier IProvider.
    """

    def __init__(self, provider: Optional[IProvider] = None):
        self.provider = provider or MockProvider()

    def plan_workflow(self, goal: str, context: Dict[str, Any]) -> WorkflowDefinition:
        """
        Genera un WorkflowDefinition llamando al provider configurado.
        """
        print(f"[PlannerFacade] Planificando workflow para goal='{goal}'")
        return self.provider.suggest_workflow(goal, context)
