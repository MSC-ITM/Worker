# worker/workflow/workflow_models.py
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

@dataclass
class WorkflowNode:
    id: str
    type: str
    params: Dict[str, Any]
    depends_on: List[str] = field(default_factory=list)

@dataclass
class WorkflowDefinition:
    name: str
    nodes: List[WorkflowNode]
    id: Optional[str] = None  # Workflow ID from API (e.g., "wf_abc123")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowDefinition":
        nodes = [WorkflowNode(**n) for n in data.get("nodes", [])]
        return cls(
            name=data.get("name", "Unnamed Workflow"),
            nodes=nodes,
            id=data.get("id")
        )

@dataclass
class WorkflowResult:
    workflow_name: str
    status: str
    results: Dict[str, Any] = field(default_factory=dict)
