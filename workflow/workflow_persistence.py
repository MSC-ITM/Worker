# worker/workflow/workflow_persistence.py
from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import Field, SQLModel, create_engine, Session, select, Column
from sqlalchemy import inspect
import json
import os

class WorkflowDefinition(SQLModel, table=True):
    __tablename__ = "workflow_definition"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False, max_length=255)
    definition: Dict[str, Any] = Field(sa_column=Column(json), nullable=False)
    status: str = Field(default="pendiente", nullable=False, max_length=50)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

# --- MODELOS DE TABLA ---

class WorkflowRun(SQLModel, table=True):
    __tablename__ = "workflowrun"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration: Optional[float] = None
    result_summary: Optional[str] = None  # JSON resumido


class NodeRun(SQLModel, table=True):
    __tablename__ = "noderun"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_id: int = Field(foreign_key="workflowrun.id")
    node_id: str
    type: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration: Optional[float] = None
    result_data: Optional[str] = None  # JSON completo


# --- GESTOR DE BASE DE DATOS ---

class WorkflowRepository:
    def __init__(self, db_path: str = "data/workflows.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        if db_path.startswith("sqlite://"):
            self.engine = create_engine(db_path)
        else:
            self.engine = create_engine(f"sqlite:///{db_path}")

        # 💡 Crea las tablas si no existen físicamente en el archivo SQLite
        inspector = inspect(self.engine)
        existing_tables = inspector.get_table_names()
        
        if "workflowrun" not in existing_tables or "noderun" not in existing_tables:
            SQLModel.metadata.create_all(self.engine)

    def save_workflow_run(self, workflow_name: str, status: str, results: Dict[str, Any],
                          started_at: datetime, finished_at: datetime):
        duration = (finished_at - started_at).total_seconds()
        summary = json.dumps({k: v.get("status", "OK") for k, v in results.items()}, ensure_ascii=False)

        with Session(self.engine) as session:
            run = WorkflowRun(
                name=workflow_name,
                status=status,
                started_at=started_at,
                finished_at=finished_at,
                duration=duration,
                result_summary=summary
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            return run.id

    def save_node_run(self, workflow_id: int, node_id: str, node_type: str,
                      status: str, started_at: datetime, finished_at: datetime, result: Dict[str, Any]):
        duration = (finished_at - started_at).total_seconds()
        result_json = json.dumps(result, ensure_ascii=False)

        with Session(self.engine) as session:
            node = NodeRun(
                workflow_id=workflow_id,
                node_id=node_id,
                type=node_type,
                status=status,
                started_at=started_at,
                finished_at=finished_at,
                duration=duration,
                result_data=result_json
            )
            session.add(node)
            session.commit()
        
    def update_workflow_run(self, workflow_id: int, status: str, results: Dict[str, Any], finished_at: datetime):
        """Actualiza un workflow existente"""
        with Session(self.engine) as session:
            run = session.get(WorkflowRun, workflow_id)
            if run:
                run.status = status
                run.finished_at = finished_at
                run.duration = (finished_at - run.started_at).total_seconds()
                run.result_summary = json.dumps(
                    {k: v.get("status", "OK") for k, v in results.items()}, 
                    ensure_ascii=False
                )
                session.add(run)
                session.commit()

    def create_workflow(self, name: str, definition: dict) -> WorkflowDefinition:
        with Session(self.engine) as session:
            wf = WorkflowDefinition(name=name, definition=definition, status="pendiente")
            session.add(wf)
            session.commit()
            session.refresh(wf)
            return wf

    def get_workflow(self, workflow_id: int) -> Optional[WorkflowDefinition]:
        with Session(self.engine) as session:
            statement = select(WorkflowDefinition).where(WorkflowDefinition.id == workflow_id)
            return session.exec(statement).first()

    def list_workflows(self) -> list[WorkflowDefinition]:
        with Session(self.engine) as session:
            return list(session.exec(select(WorkflowDefinition)))

    def update_workflow_status(self, workflow_id: int, status: str):
        with Session(self.engine) as session:
            wf = session.get(WorkflowDefinition, workflow_id)
            if wf:
                wf.status = status
                wf.updated_at = datetime.utcnow()
                session.add(wf)
                session.commit()
                session.refresh(wf)
                return wf
            return None

    def list_pending(self):
        with Session(self.engine) as session:
            stmt = select(WorkflowDefinition).where(WorkflowDefinition.status == "pendiente")
            return list(session.exec(stmt))
