# tests/test_worker_integration.py
"""
Pruebas de integración del WorkerService con la base de datos compartida.
Valida que el Worker:
 - ejecuta correctamente workflows 'en_espera'
 - marca como fallidos los workflows con errores
"""

import os
import json
import uuid
import time
import threading
from datetime import datetime, UTC
from sqlmodel import SQLModel, Field, Session, create_engine, select
import pytest
from Worker.Models.shared_workflow_table import workflowTable

from Worker.service.worker_service import WorkerService


# ============================================================
# CONFIGURACIÓN
# ============================================================

DB_PATH = os.path.abspath("database.db")
DB_URL = f"sqlite:///{DB_PATH}"


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture(scope="module")
def setup_database():
    """Crea la base de datos y tabla si no existen"""
    engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    yield engine


def _insert_workflow(engine, name: str, steps: dict) -> str:
    """Función auxiliar para insertar un workflow"""
    with Session(engine) as session:
        wf = workflowTable(
            id=str(uuid.uuid4()),
            name=name,
            status="en_espera",
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
            definition=json.dumps(steps)
        )
        session.add(wf)
        session.commit()
        return wf.id


@pytest.fixture
def insert_success_workflow(setup_database):
    """Inserta un workflow válido"""
    engine = setup_database
    definition = {
        "steps": [
            {
                "type": "HTTPS GET Request",
                "args": {
                    "url": "https://httpbin.org/get",
                    "timeout": 5
                }
            },
            {
                "type": "Mock Notification",
                "args": {"channel": "console", "message": "Workflow completado!"}
            }
        ]
    }
    return _insert_workflow(engine, "workflow_exitoso", definition)


@pytest.fixture
def insert_failed_workflow(setup_database):
    """Inserta un workflow con error (URL inválida)"""
    engine = setup_database
    definition = {
        "steps": [
            {
                "type": "HTTPS GET Request",
                "args": {"url": "https://no-existe-esta-url-999.fake/"}
            },
            {
                "type": "Mock Notification",
                "args": {"channel": "console", "message": "No debería ejecutarse"}
            }
        ]
    }
    return _insert_workflow(engine, "workflow_fallido", definition)


# ============================================================
# TESTS
# ============================================================

def _run_worker_for(seconds: float):
    """Ejecuta el Worker en un hilo y lo detiene tras unos segundos"""
    worker = WorkerService(shared_db_path=DB_PATH, poll_interval=2.0)
    worker_thread = threading.Thread(target=worker.start_blocking, daemon=True)
    worker_thread.start()
    time.sleep(seconds)
    worker.stop()
    worker_thread.join(timeout=3)
    return worker


def test_worker_executes_success_workflow(setup_database, insert_success_workflow):
    """Debe completar correctamente un workflow válido"""
    workflow_id = insert_success_workflow
    _run_worker_for(8)

    engine = setup_database
    with Session(engine) as session:
        wf = session.exec(select(workflowTable).where(workflowTable.id == workflow_id)).first()

    assert wf is not None
    assert wf.status in ["completado", "fallido"]
    definition = json.loads(wf.definition)
    assert "execution_results" in definition
    print("\n✅ Workflow exitoso procesado:")
    print(json.dumps(definition["execution_results"], indent=2, ensure_ascii=False))


def test_worker_handles_failed_workflow(setup_database, insert_failed_workflow):
    """Debe marcar como fallido un workflow con error"""
    workflow_id = insert_failed_workflow
    _run_worker_for(8)

    engine = setup_database
    with Session(engine) as session:
        wf = session.exec(select(workflowTable).where(workflowTable.id == workflow_id)).first()

    assert wf is not None
    assert wf.status == "fallido", f"Esperado 'fallido', obtenido '{wf.status}'"
    definition = json.loads(wf.definition)
    assert "execution_results" in definition
    print("\n⚠️ Workflow fallido procesado:")
    print(json.dumps(definition["execution_results"], indent=2, ensure_ascii=False))
