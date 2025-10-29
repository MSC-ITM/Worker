# Worker/Tests/test_registry.py
import pytest
from Worker.registry import Taskregistry
from Worker.FactoryM import TaskFactoryDirector
from Worker.strategies.Http_get import HttpGetTask

@pytest.fixture
def registry():
    reg = Taskregistry()
    yield reg
    reg.clear()

def test_register_and_create(registry):
    registry.register("http_get")
    instance = registry.create("http_get")
    assert isinstance(instance, HttpGetTask)

def test_register_invalid_task(registry):
    with pytest.raises(ValueError) as exc:
        registry.register("invalid_task")
    assert "no está definida como tarea" in str(exc.value)

def test_duplicate_registration(registry):
    registry.register("http_get")
    with pytest.raises(ValueError) as exc:
        registry.register("http_get")
    assert "ya está registrado" in str(exc.value)

def test_list_tasks(registry):
    registry.register("http_get")
    tasks = registry.list()
    assert len(tasks) == 1
    assert HttpGetTask in tasks

def test_clear_registry(registry):
    registry.register("http_get")
    registry.clear()
    assert len(registry.list()) == 0
