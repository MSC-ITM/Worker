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

#class workflowTable(SQLModel, table=True):
    # __tablename__ = "workflowtable"

    # id: Optional[str] = Field(default=None, primary_key=True)
    # name: str = Field(nullable=False, max_length=255)
    # definition: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    # status: str = Field(default="pendiente", nullable=False, max_length=50)
    # created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    # # updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    # """
    # Tabla identica al diseño del API.
    # """
    # __tablename__ = "workflowtable"
    # __table_args__ = {"extend_existing": True}
    # id: str = Field(primary_key=True, index=True)
    # name: str
    # status: str
    # created_at: str
    # updated_at: str
    # definition: Optional[str] = None  # JSON serializado como TEXT