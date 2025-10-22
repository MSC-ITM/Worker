#Task_command
from dataclasses import dataclass, field
from typing import Any, Dict

@dataclass
class TaskCommand:
    """
    Representa una instrucción para ejecutar una tarea en el Worker.
    Forma parte del patrón Command.
    """

    run_id: str                     # ID de ejecución del flujo
    node_key: str                   # Identificador del nodo dentro del flujo
    type: str                       # Tipo de tarea (coincide con BaseTask.type)
    params: Dict[str, Any] = field(default_factory=dict)  # Parámetros de ejecución
    metadata: Dict[str, Any] = field(default_factory=dict)  # Info opcional del flujo o UI

    def __repr__(self) -> str:
        return (
            f"<TaskCommand type={self.type} node={self.node_key} run={self.run_id}>"
        )