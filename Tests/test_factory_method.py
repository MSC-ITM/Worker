# Worker/Tests/test_factory_method.py
import pytest
from Worker.FactoryM import TaskFactoryDirector
from Worker.strategies.Http_get import HttpGetTask
from Worker.strategies.notify_mock import NotifyMockTask
from Worker.strategies.save_db import SaveDBTask
from Worker.strategies.transform_simply import TransformSimpleTask
from Worker.strategies.validate_csv import ValidateCSVTask

@pytest.fixture
def factory():
    return TaskFactoryDirector()

def test_create_http_get(factory):
    task = factory.create("http_get")
    assert isinstance(task, HttpGetTask)

def test_create_notify_mock(factory):
    task = factory.create("notify_mock")
    assert isinstance(task, NotifyMockTask)

def test_create_save_db(factory):
    task = factory.create("save_db")
    assert isinstance(task, SaveDBTask)

def test_create_transform_simple(factory):
    task = factory.create("transform_simple")
    assert isinstance(task, TransformSimpleTask)

def test_create_validate_csv(factory):
    task = factory.create("validate_csv")
    assert isinstance(task, ValidateCSVTask)

def test_invalid_task_type(factory):
    with pytest.raises(ValueError) as exc:
        factory.create("invalid_task")
    assert "Tipo de tarea desconocido" in str(exc.value)
