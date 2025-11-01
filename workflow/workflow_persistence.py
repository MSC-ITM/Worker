# worker/workflow/workflow_persistence.py
from datetime import datetime, UTC
from typing import Optional, Dict, Any
from sqlmodel import Field, SQLModel, create_engine, Session
from sqlalchemy import MetaData
import json as json_module
import os

# ✅ CREAR METADATA SEPARADO para las tablas del Worker
worker_metadata = MetaData()
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
        # Crear directorio si no existe
        db_dir = os.path.dirname(db_path)
        if db_dir and db_dir != '':
            os.makedirs(db_dir, exist_ok=True)

        # Crear engine con conexión segura para threading
        if db_path.startswith("sqlite://"):
            self.engine = create_engine(db_path, connect_args={"check_same_thread": False})
        else:
            self.engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

        # ✅ FORZAR creación de tablas específicas
        WorkflowRun.__table__.create(self.engine, checkfirst=True)
        NodeRun.__table__.create(self.engine, checkfirst=True)
         
         # ✅ AGREGAR: Verificar que las tablas se crearon
        from sqlalchemy import inspect
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()
        if "workflowrun" not in tables or "noderun" not in tables:
            raise RuntimeError(f"❌ Tablas no creadas. Tablas existentes: {tables}")


    def save_workflow_run(self, workflow_name: str, status: str, results: Dict[str, Any],
                          started_at: datetime, finished_at: datetime):
        duration = (finished_at - started_at).total_seconds()
        summary = json_module.dumps({k: v.get("status", "OK") for k, v in results.items()}, ensure_ascii=False)

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
        result_json = json_module.dumps(result, ensure_ascii=False)

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
            session.refresh(node)
            return node.id

    def create_node_run_running(self, workflow_id: int, node_id: str, node_type: str, started_at: datetime):
        """Crea un noderun en estado RUNNING al inicio de la ejecución"""
        with Session(self.engine) as session:
            node = NodeRun(
                workflow_id=workflow_id,
                node_id=node_id,
                type=node_type,
                status="RUNNING",
                started_at=started_at,
                finished_at=started_at,  # Placeholder
                duration=0.0,
                result_data=json_module.dumps({}, ensure_ascii=False)
            )
            session.add(node)
            session.commit()
            session.refresh(node)
            return node.id

    def update_node_run_completed(self, node_run_id: int, status: str, finished_at: datetime, result: Dict[str, Any]):
        """Actualiza un noderun cuando termina la ejecución"""
        result_json = json_module.dumps(result, ensure_ascii=False)

        with Session(self.engine) as session:
            node = session.get(NodeRun, node_run_id)
            if node:
                node.status = status
                node.finished_at = finished_at
                node.duration = (finished_at - node.started_at).total_seconds()
                node.result_data = result_json
                session.commit()
        
    def update_workflow_run(self, workflow_id: int, status: str, results: Dict[str, Any], finished_at: datetime):
        """Actualiza un workflow existente"""
        with Session(self.engine) as session:
            run = session.get(WorkflowRun, workflow_id)
            if run:
                run.status = status
                run.finished_at = finished_at
                run.duration = (finished_at - run.started_at).total_seconds()
                run.result_summary = json_module.dumps(
                    {k: (v.get("status", "OK") if isinstance(v, dict) else str(v))
     for k, v in results.items()}, 
                    ensure_ascii=False
                )
                session.add(run)
                session.commit()
