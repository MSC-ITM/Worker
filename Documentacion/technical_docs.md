# 🏛️ Arquitectura Técnica - Worker Engine

Documentación técnica detallada del sistema de orquestación de workflows.

---

## 📐 Principios de Diseño

### SOLID Principles

- **Single Responsibility**: Cada clase tiene una única responsabilidad bien definida
- **Open/Closed**: Extensible mediante nuevas tareas sin modificar el core
- **Liskov Substitution**: Todas las tareas implementan `ITask` consistentemente
- **Interface Segregation**: Interfaces específicas (ITask, IPlanner)
- **Dependency Inversion**: Dependencias en abstracciones, no implementaciones concretas

### Patrones de Diseño

| Patrón | Implementación | Propósito |
|--------|---------------|-----------|
| **Strategy** | `ITask` + tareas concretas | Intercambiar algoritmos de procesamiento |
| **Factory** | `TaskRegistry` | Crear instancias de tareas dinámicamente |
| **Command** | `TaskCommand` | Encapsular requests como objetos |
| **Decorator** | `TimeDecorator`, `LoggingDecorator` | Añadir funcionalidad sin modificar código |
| **Template Method** | `ITask.run()` | Definir esqueleto de algoritmo |
| **Repository** | `WorkflowRepository` | Abstraer acceso a datos |

---

## 🔄 Ciclo de Vida de un Workflow

### 1. Definición (JSON → Objeto)

```python
# Entrada: JSON
{
  "name": "Mi Workflow",
  "nodes": [
    {"id": "task1", "type": "http_get", "params": {...}},
    {"id": "task2", "type": "save_db", "depends_on": ["task1"], "params": {...}}
  ]
}

# Conversión
workflow = WorkflowDefinition.from_dict(json_data)

# Resultado: Objeto Python
WorkflowDefinition(
    name="Mi Workflow",
    nodes=[
        WorkflowNode(id="task1", type="http_get", ...),
        WorkflowNode(id="task2", type="save_db", depends_on=["task1"], ...)
    ]
)
```

### 2. Inicialización

```python
workflow_id = repo.save_workflow_run(
    workflow_name=workflow.name,
    status="RUNNING",
    results={},
    started_at=datetime.now(),
    finished_at=datetime.now()
)
```

**Registro en BD:**

```sql
INSERT INTO workflowrun (name, status, started_at, finished_at, duration, result_summary)
VALUES ('Mi Workflow', 'RUNNING', '2025-10-23 10:00:00', '2025-10-23 10:00:00', 0, '{}');
```

### 3. Resolución de Dependencias

El motor resuelve el orden de ejecución usando un algoritmo topológico:

```python
pending = {node.id: node for node in workflow.nodes}
executed = set()

while pending:
    for node_id, node in list(pending.items()):
        # ¿Todas las dependencias completadas?
        if all(dep in executed for dep in node.depends_on):
            # Ejecutar nodo
            execute_node(node)
            executed.add(node_id)
            del pending[node_id]
```

**Ejemplo de resolución:**

```
Workflow: A → B → C
          ↓
          D → E

Orden de ejecución:
1. A (sin dependencias)
2. B y D (dependen de A) - pueden ejecutarse en paralelo*
3. C (depende de B)
4. E (depende de D)

*Nota: En v1.0 la ejecución es secuencial. La paralelización viene en v2.0
```

### 4. Ejecución de Nodo

```python
# 1. Crear comando
command = TaskCommand(
    run_id=f"{workflow.name}_{node.id}",
    node_key=node.id,
    type=node.type,
    params=node.params
)

# 2. Delegar a WorkerEngine
task_result = worker.execute_command(command)

# 3. Guardar resultado
repo.save_node_run(
    workflow_id=workflow_id,
    node_id=node.id,
    node_type=node.type,
    status=task_result["status"],
    started_at=node_start,
    finished_at=node_end,
    result=task_result["result"]
)
```

### 5. Manejo de Fallos

```python
# Si una tarea falla
if task_result.get("status") == "FAILED":
    node_status[node_id] = "FAILED"
    
    # Saltar tareas dependientes
    for dependent_node in get_dependents(node_id):
        node_status[dependent_node] = "SKIPPED"
        results[dependent_node] = {
            "status": "SKIPPED",
            "reason": f"Dependencia fallida: {node_id}"
        }
```

### 6. Finalización

```python
# Determinar estado global
if all(s == "SUCCESS" for s in node_status.values()):
    wf_status = "SUCCESS"
elif any(s == "SUCCESS" for s in node_status.values()):
    wf_status = "PARTIAL_SUCCESS"
else:
    wf_status = "FAILED"

# Actualizar registro
repo.update_workflow_run(
    workflow_id=workflow_id,
    status=wf_status,
    results=results,
    finished_at=datetime.now()
)
```

---

## 🗄️ Modelo de Datos

### Diagrama ER

```
┌─────────────────────────┐
│     WorkflowRun         │
├─────────────────────────┤
│ id (PK)                 │
│ name                    │
│ status                  │
│ started_at              │
│ finished_at             │
│ duration                │
│ result_summary (JSON)   │
└────────────┬────────────┘
             │ 1
             │
             │ N
             ▼
┌─────────────────────────┐
│      NodeRun            │
├─────────────────────────┤
│ id (PK)                 │
│ workflow_id (FK)        │
│ node_id                 │
│ type                    │
│ status                  │
│ started_at              │
│ finished_at             │
│ duration                │
│ result_data (JSON)      │
└─────────────────────────┘
```

### Estados de Ejecución

| Estado | Descripción |
|--------|-------------|
| `RUNNING` | Workflow en ejecución |
| `SUCCESS` | Todas las tareas completadas exitosamente |
| `PARTIAL_SUCCESS` | Algunas tareas completadas, otras fallaron |
| `FAILED` | Todas las tareas fallaron |

| Estado Nodo | Descripción |
|-------------|-------------|
| `SUCCESS` | Tarea completada correctamente |
| `FAILED` | Tarea falló durante ejecución |
| `SKIPPED` | Tarea no ejecutada por dependencia fallida |

---

## 🎯 Extensibilidad

### Añadir un Nuevo Tipo de Tarea

#### 1. Crear la Estrategia

```python
# Worker/strategies/mi_nueva_tarea.py
from Worker.strategies.base import ITask
import requests

class MiNuevaTarea(ITask):
    type = "mi_nueva_tarea"
    display_name = "Mi Nueva Tarea"
    description = "Hace algo increíble"
    category = "Custom"
    icon = "star"
    
    params_schema = {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "title": "Parámetro 1"},
            "param2": {"type": "integer", "title": "Parámetro 2"}
        },
        "required": ["param1"]
    }
    
    def validate_params(self, params):
        """Validación de parámetros"""
        if "param1" not in params:
            raise ValueError("param1 es requerido")
        
        if not isinstance(params.get("param2", 0), int):
            raise TypeError("param2 debe ser entero")
    
    def execute(self, context, params):
        """Lógica principal"""
        # Acceder a resultados de tareas previas
        previous_result = context.get("tarea_anterior", {})
        
        # Tu lógica
        resultado = self.procesar(
            params["param1"],
            params.get("param2", 0)
        )
        
        return {
            "success": True,
            "output": resultado,
            "metadata": {"procesado": True}
        }
    
    def procesar(self, param1, param2):
        """Implementación del algoritmo"""
        return f"{param1} * {param2}"
    
    def on_error(self, error):
        """Manejo personalizado de errores"""
        print(f"[MiNuevaTarea] Error: {error}")
        return {
            "success": False,
            "error": str(error),
            "output": None
        }
```

#### 2. Registrar la Tarea

```python
# En tu inicialización
from Worker.strategies.mi_nueva_tarea import MiNuevaTarea

registry = Taskregistry()
registry.register(MiNuevaTarea)
```

#### 3. Configurar Decoradores (Opcional)

```python
# Worker/config/decoradores_config.py
from Worker.decorador import TimeDecorator, LoggingDecorator

TASK_DECORATOR_MAP = {
    "mi_nueva_tarea": [TimeDecorator, LoggingDecorator],
    # ... otras tareas
}
```

#### 4. Usar en Workflow

```json
{
  "name": "Test Nueva Tarea",
  "nodes": [
    {
      "id": "task1",
      "type": "mi_nueva_tarea",
      "params": {
        "param1": "valor",
        "param2": 42
      }
    }
  ]
}
```

### Añadir un Nuevo Decorador

```python
# Worker/decorador.py
class MetricsDecorator(TaskDecorator):
    """Envía métricas a un sistema de monitoreo"""
    
    def run(self, context: Dict[str, Any], params: Dict[str, Any]) -> Any:
        task_name = self._wrapped_Task.__class__.__name__
        
        # Antes de ejecutar
        self.send_metric(f"task.{task_name}.started", 1)
        
        try:
            result = self._wrapped_Task.run(context, params)
            
            # Si es exitoso
            self.send_metric(f"task.{task_name}.success", 1)
            return result
            
        except Exception as e:
            # Si falla
            self.send_metric(f"task.{task_name}.failed", 1)
            raise
    
    def send_metric(self, metric_name: str, value: int):
        """Envía métrica a sistema externo"""
        # Implementación: StatsD, Prometheus, etc.
        pass
```

---

## 🔍 Debugging y Troubleshooting

### Logs Detallados

El sistema genera logs estructurados en cada etapa:

```
[WorkflowEngine] ▶️ Ejecutando workflow: Mi Workflow
[WorkflowEngine] ▶️ Ejecutando nodo: task1 (http_get)
[Worker] ▶️ Ejecutando http_get (node=task1, run=Mi Workflow_task1)
[HttpGetTask] ▶️ Iniciando tarea con params: {'url': 'https://...'}
[HttpGetTask] ✅ Finalizada en 0.234s
[Worker] ✅ Tarea 'http_get' completada
[WorkflowEngine] ✅ Nodo 'task1' completado correctamente.
```

### Inspeccionar Base de Datos

```python
from sqlmodel import Session, select
from Worker.workflow.workflow_persistence import WorkflowRun, NodeRun, WorkflowRepository

repo = WorkflowRepository()

# Ver últimas ejecuciones
with Session(repo.engine) as session:
    runs = session.exec(
        select(WorkflowRun).order_by(WorkflowRun.started_at.desc()).limit(10)
    ).all()
    
    for run in runs:
        print(f"{run.id}: {run.name} - {run.status} ({run.duration}s)")

# Ver detalles de un workflow específico
with Session(repo.engine) as session:
    workflow_run = session.get(WorkflowRun, 1)
    nodes = session.exec(
        select(NodeRun).where(NodeRun.workflow_id == workflow_run.id)
    ).all()
    
    print(f"\nWorkflow: {workflow_run.name}")
    for node in nodes:
        print(f"  - {node.node_id}: {node.status} ({node.duration}s)")
```

### Errores Comunes

| Error | Causa | Solución |
|-------|-------|----------|
| `AttributeError: 'Engine' object has no attribute 'table_names'` | Versión incorrecta de SQLAlchemy | Usar `inspect(engine).get_table_names()` |
| `ValueError: Unknown task type: X` | Tarea no registrada | Verificar `registry.register(XTask)` |
| `Dependencias circulares` | Workflow mal definido | Revisar `depends_on` en JSON |
| `FileNotFoundError` en tests | Archivo seed faltante | Crear `tests/seeds/sample.csv` |
| `Task returns dict instead of raising` | Decorador captura excepciones | Hacer `raise` en decoradores |

---

## 🧪 Testing Strategy

### Pirámide de Tests

```
        /\
       /  \
      / E2E\           ← Integration Tests (test_workflow_engine.py)
     /______\
    /        \
   /  Unit    \        ← Unit Tests (test_worker_tasks.py)
  /____________\
 /   Mocks      \      ← Mock Tests (test_planner_facade.py)
/________________\
```

### Test Fixtures

```python
# conftest.py (opcional)
import pytest
from Worker.factory import Taskregistry
from Worker.worker_engine import WorkerEngine
from Worker.workflow.workflow_persistence import WorkflowRepository

@pytest.fixture
def task_registry():
    """Registry con todas las tareas"""
    from Worker.strategies.Http_get import HttpGetTask
    from Worker.strategies.validate_csv import ValidateCSVTask
    from Worker.strategies.save_db import SaveDBTask
    
    registry = Taskregistry()
    registry.register(HttpGetTask)
    registry.register(ValidateCSVTask)
    registry.register(SaveDBTask)
    return registry

@pytest.fixture
def worker_engine(task_registry):
    """Worker engine configurado"""
    return WorkerEngine(task_registry)

@pytest.fixture
def temp_db(tmp_path):
    """Base de datos temporal para tests"""
    db_path = tmp_path / "test.db"
    return WorkflowRepository(db_path=str(db_path))
```

### Testing de Tareas Individuales

```python
# test_custom_task.py
import pytest
from Worker.strategies.mi_nueva_tarea import MiNuevaTarea

def test_mi_nueva_tarea_success():
    """Test de ejecución exitosa"""
    task = MiNuevaTarea()
    
    result = task.execute(
        context={},
        params={"param1": "test", "param2": 5}
    )
    
    assert result["success"] == True
    assert result["output"] == "test * 5"

def test_mi_nueva_tarea_validation_error():
    """Test de validación de parámetros"""
    task = MiNuevaTarea()
    
    with pytest.raises(ValueError, match="param1 es requerido"):
        task.validate_params({"param2": 5})

def test_mi_nueva_tarea_with_context():
    """Test usando contexto de tareas previas"""
    task = MiNuevaTarea()
    
    context = {
        "tarea_anterior": {"data": "valor"}
    }
    
    result = task.execute(context, {"param1": "test"})
    assert result["success"] == True
```

### Testing de Workflows

```python
def test_workflow_with_dependencies(tmp_path):
    """Test de workflow con dependencias"""
    # Setup
    db_path = tmp_path / "test.db"
    repo = WorkflowRepository(db_path=str(db_path))
    registry = iniciar_registry()
    worker = WorkerEngine(registry)
    engine = WorkflowEngine(worker=worker, repo=repo)
    
    # Workflow con 3 nodos: A → B → C
    workflow_json = {
        "name": "Test Dependency Chain",
        "nodes": [
            {"id": "A", "type": "validate_csv", "params": {...}},
            {"id": "B", "type": "transform_simple", "depends_on": ["A"], "params": {...}},
            {"id": "C", "type": "save_db", "depends_on": ["B"], "params": {...}}
        ]
    }
    
    workflow = WorkflowDefinition.from_dict(workflow_json)
    
    # Execute
    result = engine.run(workflow)
    
    # Assert
    assert result.status == "SUCCESS"
    assert "A" in result.results
    assert "B" in result.results
    assert "C" in result.results
    
    # Verify execution order
    from sqlmodel import Session, select
    with Session(repo.engine) as session:
        nodes = session.exec(
            select(NodeRun).order_by(NodeRun.started_at)
        ).all()
        
        assert nodes[0].node_id == "A"
        assert nodes[1].node_id == "B"
        assert nodes[2].node_id == "C"
```

### Mocking de Servicios Externos

```python
from unittest.mock import patch, Mock

def test_http_get_with_mock():
    """Test de HttpGetTask con mock de requests"""
    task = HttpGetTask()
    
    with patch('requests.get') as mock_get:
        # Configurar mock
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Mocked response"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Ejecutar
        result = task.execute(
            context={},
            params={"url": "https://example.com"}
        )
        
        # Verificar
        assert result["success"] == True
        assert result["status_code"] == 200
        mock_get.assert_called_once()
```

---

## 🚀 Performance y Optimización

### Benchmarking

```python
import time
from Worker.workflow.workflow_engine import WorkflowEngine

def benchmark_workflow(workflow, iterations=10):
    """Mide el tiempo promedio de ejecución"""
    times = []
    
    for i in range(iterations):
        start = time.time()
        engine.run(workflow)
        elapsed = time.time() - start
        times.append(elapsed)
    
    avg_time = sum(times) / len(times)
    print(f"Tiempo promedio: {avg_time:.3f}s")
    print(f"Min: {min(times):.3f}s, Max: {max(times):.3f}s")
```

### Optimizaciones Implementadas

1. **Lazy Loading de Tareas**: Las tareas se instancian solo cuando se necesitan
2. **Connection Pooling**: SQLAlchemy maneja pool de conexiones
3. **Batch Inserts**: NodeRuns se pueden insertar en lote (futuro)

### Métricas Importantes

```python
# Monitorear estas métricas:
- Tiempo de ejecución por workflow
- Tiempo de ejecución por tipo de tarea
- Tasa de éxito/fallo
- Cantidad de workflows en cola
- Uso de memoria
```

---

## 🔐 Seguridad

### Validación de Inputs

Todas las tareas validan sus parámetros antes de ejecutar:

```python
def validate_params(self, params):
    # Validar tipos
    if not isinstance(params.get("path"), str):
        raise TypeError("path debe ser string")
    
    # Validar valores
    if params.get("mode") not in ["append", "replace"]:
        raise ValueError("mode debe ser 'append' o 'replace'")
    
    # Sanitizar paths
    path = os.path.abspath(params["path"])
    if not path.startswith("/allowed/directory/"):
        raise SecurityError("Path no permitido")
```

### Protección contra Path Traversal

```python
import os

def safe_path(base_dir, filename):
    """Previene path traversal attacks"""
    filepath = os.path.join(base_dir, filename)
    realpath = os.path.realpath(filepath)
    
    if not realpath.startswith(os.path.realpath(base_dir)):
        raise SecurityError("Path traversal detectado")
    
    return realpath
```

### Límites de Recursos

```python
# Configuración recomendada
MAX_WORKFLOW_DURATION = 3600  # 1 hora
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
MAX_CONCURRENT_WORKFLOWS = 10

# Implementar timeout
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Workflow excedió tiempo máximo")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(MAX_WORKFLOW_DURATION)
```

---

## 🌐 Integración con API REST

### Ejemplo con FastAPI

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

app = FastAPI()

class WorkflowRequest(BaseModel):
    name: str
    nodes: list

@app.post("/workflows/execute")
async def execute_workflow(request: WorkflowRequest):
    """Ejecuta un workflow"""
    try:
        # Convertir a WorkflowDefinition
        workflow_dict = request.dict()
        workflow = WorkflowDefinition.from_dict(workflow_dict)
        
        # Ejecutar
        result = engine.run(workflow)
        
        return {
            "workflow_id": result.workflow_name,
            "status": result.status,
            "results": result.results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/workflows/{workflow_id}")
async def get_workflow_status(workflow_id: int):
    """Consulta el estado de un workflow"""
    from sqlmodel import Session, select
    
    with Session(repo.engine) as session:
        run = session.get(WorkflowRun, workflow_id)
        
        if not run:
            raise HTTPException(status_code=404, detail="Workflow no encontrado")
        
        return {
            "id": run.id,
            "name": run.name,
            "status": run.status,
            "started_at": run.started_at.isoformat(),
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "duration": run.duration
        }

@app.get("/tasks/types")
async def list_task_types():
    """Lista todos los tipos de tareas disponibles"""
    tasks = registry.list()
    
    return [
        {
            "type": task.type,
            "display_name": task.display_name,
            "description": task.description,
            "category": task.category,
            "params_schema": task.params_schema
        }
        for task in tasks
    ]
```

---

## 📊 Monitoreo y Observabilidad

### Logging Estructurado

```python
import logging
import json

# Configurar logging JSON
logging.basicConfig(
    format='%(message)s',
    level=logging.INFO
)

def log_event(event_type: str, data: dict):
    """Log estructurado en JSON"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event_type,
        **data
    }
    logging.info(json.dumps(log_entry))

# Uso
log_event("workflow.started", {
    "workflow_id": workflow_id,
    "workflow_name": workflow.name,
    "node_count": len(workflow.nodes)
})
```

### Métricas con Prometheus

```python
from prometheus_client import Counter, Histogram, Gauge

# Métricas
workflow_executions = Counter(
    'workflow_executions_total',
    'Total de ejecuciones de workflows',
    ['workflow_name', 'status']
)

task_duration = Histogram(
    'task_duration_seconds',
    'Duración de tareas',
    ['task_type']
)

active_workflows = Gauge(
    'active_workflows',
    'Workflows en ejecución'
)

# Instrumentar código
@task_duration.labels(task_type=task.type).time()
def execute_task(task, params):
    return task.run({}, params)
```

### Health Check Endpoint

```python
@app.get("/health")
async def health_check():
    """Verifica salud del sistema"""
    checks = {
        "database": check_database(),
        "task_registry": check_registry(),
        "disk_space": check_disk_space()
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if all_healthy else "unhealthy",
            "checks": checks
        }
    )

def check_database():
    try:
        with Session(repo.engine) as session:
            session.exec(select(WorkflowRun).limit(1))
        return True
    except:
        return False
```

---

## 🐳 Deployment

### Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY Worker/ ./Worker/
COPY workflows/ ./workflows/

# Crear directorios de datos
RUN mkdir -p data logs

# Exponer puerto (si usas FastAPI)
EXPOSE 8000

# Comando por defecto
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  worker-engine:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./workflows:/app/workflows
    environment:
      - DB_PATH=/app/data/workflows.db
      - LOG_LEVEL=INFO
    restart: unless-stopped
```

### Environment Variables

```python
# config.py
import os

class Config:
    DB_PATH = os.getenv("DB_PATH", "data/workflows.db")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", "5"))
    TASK_TIMEOUT = int(os.getenv("TASK_TIMEOUT", "3600"))
```

---

## 📚 Referencias

- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/)
- [Design Patterns: Gang of Four](https://refactoring.guru/design-patterns)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [Python Best Practices](https://docs.python-guide.org/)