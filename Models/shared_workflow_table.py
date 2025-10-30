# Worker/models/shared_workflow_table.py
from sqlmodel import SQLModel, Field

class workflowTable(SQLModel, table=True):
    __tablename__ = "workflowtable"
    __table_args__ = {"extend_existing": True}

    id: str = Field(primary_key=True, index=True)
    name: str
    status: str
    created_at: str
    updated_at: str 
    definition: str | None = None

