# 📚 API Reference - Worker Engine

Documentación completa de la API pública del Worker Engine.

---

## 📋 Tabla de Contenidos

- [WorkflowEngine](#workflowengine)
- [WorkerEngine](#workerengine)
- [TaskRegistry](#taskregistry)
- [ITask](#itask)
- [WorkflowRepository](#workflowrepository)
- [Models](#models)
- [Decorators](#decorators)

---

## WorkflowEngine

Orquestador principal de workflows con gestión de dependencias.

### Constructor

```python
WorkflowEngine(worker: WorkerEngine, repo: WorkflowRepository)
```

**Parámetros:**
- `worker` (WorkerEngine): Motor de ejecución de tareas
- `repo` (WorkflowRepository): Repositorio para persistencia

**Ejemplo:**

```python
from Worker.workflow.workflow_engine import WorkflowEngine
from Worker.worker_engine import WorkerEngine
from Worker.workflow.workflow_persistence import WorkflowRepository
from Worker.factory import Taskregistry

registry = Taskregistry()
# ... registrar tareas
worker = WorkerEngine(registry)
repo = WorkflowRepository(db_path="data/workflows.db")
engine = WorkflowEngine(worker=worker, repo=repo)
```

### Métodos

#### `run(workflow: WorkflowDefinition) -> WorkflowResult`

Ejecuta un workflow completo con gestión de dependencias.

**Parámetros:**
- `workflow` (WorkflowDefinition): Definición del workflow a ejecutar

**Retorna:**
- `WorkflowResult`: Objeto con resultados de ejecución

**Raises:**
- `RuntimeError`: Si hay dependencias circulares o tareas bloqueadas

**Ejemplo:**

```python
from Worker.workflow.workflow_models import WorkflowDefinition
import json

# Cargar workflow desde JSON
with open("workflow.json") as f:
    workflow_data = json.load(f)

workflow = WorkflowDefinition.from_dict(workflow_data)

# Ejecutar
result = engine.run(workflow)

# Inspeccionar resultado
print(f"Estado: {result.status}")  # SUCCESS, PARTIAL_SUCCESS, FAILED
print(f"Resultados: {result.results}")  # Dict con resultados por nodo
```

**Estados Posibles:**
- `SUCCESS`: Todas las tareas completadas exitosamente
- `PARTIAL_SUCCESS`: Algunas tareas exitosas, otras fallaron
- `FAILED`: Todas las tareas fallaron

---

## WorkerEngine

Ejecutor de comandos individuales con aplicación de decoradores.

### Constructor

```python
WorkerEngine(registry: Taskregistry)
```

**Parámetros:**
- `registry` (Taskregistry): Registro de tareas disponibles

**Ejemplo:**

```python
from Worker.worker_engine import WorkerEngine
from Worker.factory import Taskregistry
from Worker.strategies.Http_get import HttpGetTask

registry = Taskregistry()
registry.register(HttpGetTask)

worker = WorkerEngine(registry)
```

### Métodos

#### `execute_command(command: TaskCommand, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]`

Ejecuta un comando de tarea individual.

**Parámetros:**
- `command` (TaskCommand): Comando con información de la tarea
- `context` (Dict, optional): Contexto compartido entre tareas

**Retorna:**
- `Dict[str, Any]`: Diccionario con resultado de ejecución
  ```python
  {
      "status": "SUCCESS" | "FAILED",
      "run_id": str,
      "node_key": str,
      "result": Any,
      "error": str  # Solo si status == "FAILED"
  }
  ```

**Ejemplo:**

```python
from Worker.Task_command import TaskCommand

command = TaskCommand(
    run_id="workflow_1_task_1",
    node_key="task1",
    type="http_get",
    params={"url": "https://api.example.com/data"}
)

result = worker.execute_command(command)

if result["status"] == "SUCCESS":
    print(f"Resultado: {result['result']}")
else:
    print(f"Error: {result['error']}")
```

---

## TaskRegistry

Catálogo de tareas disponibles (patrón Factory).

### Constructor

```python
Taskregistry()
```

**Ejemplo:**

```python
from Worker.factory import Taskregistry

registry = Taskregistry()
```

### Métodos

#### `register(task_cls: Type[ITask]) -> None`

Registra una nueva clase de tarea.

**Parámetros:**
- `task_cls` (Type[ITask]): Clase que hereda de ITask

**Raises:**
- `ValueError`: Si la clase no tiene atributo `type` o el tipo ya está registrado

**Ejemplo:**

```python
from Worker.strategies.Http_get import HttpGetTask
from Worker.strategies.validate_csv import ValidateCSVTask

registry.register(HttpGetTask)
registry.register(ValidateCSVTask)
```

#### `create(task_type: str) -> ITask`

Crea una instancia de una tarea registrada.

**Parámetros:**
- `task_type` (str): Tipo de tarea a crear

**Retorna:**
- `ITask`: Instancia de la tarea

**Raises:**
- `ValueError`: Si el tipo no está registrado

**Ejemplo:**

```python
task = registry.create("http_get")
result = task.execute(context={}, params={"url": "https://..."})
```

#### `list() -> List[Type[ITask]]`

Devuelve lista de todas las clases de tareas registradas.

**Retorna:**
- `List[Type[ITask]]`: Lista de clases de tareas

**Ejemplo:**

```python
available_tasks = registry.list()

for task_cls in available_tasks:
    print(f"{task_cls.type}: {task_cls.display_name}")
    print(f"  Categoría: {task_cls.category}")
    print(f"  Descripción: {task_cls.description}")
```

#### `clear() -> None`

Limpia el registro (útil en tests).

**Ejemplo:**

```python
registry.clear()
```

---

## ITask

Interfaz base para todas las tareas (patrón Strategy).

### Atributos de Clase

```python
class MiTarea(ITask):
    type: str                    # Identificador único (ej: "http_get")
    display_name: str           # Nombre para UI (ej: "HTTP GET Request")
    description: str            # Descripción breve
    category: str               # Categoría (ej: "Entrada", "Transformación")
    icon: str                   # Icono para UI (ej: "globe")
    params_schema: Dict         # JSON Schema de parámetros
```

### Métodos Abstractos

#### `validate_params(params: Dict[str, Any]) -> bool`

Valida parámetros antes de ejecutar.

**Parámetros:**
- `params` (Dict): Parámetros de configuración

**Raises:**
- `ValueError`: Si hay parámetros inválidos o faltantes
- `TypeError`: Si hay tipos incorrectos

**Ejemplo:**

```python
def validate_params(self, params):
    if "url" not in params:
        raise ValueError("El parámetro 'url' es obligatorio")
    
    if not isinstance(params["url"], str):
        raise TypeError("'url' debe ser string")
    
    if not params["url"].startswith("http"):
        raise ValueError("'url' debe comenzar con http:// o https://")
```

#### `execute(context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]`

Ejecuta la lógica principal de la tarea.

**Parámetros:**
- `context` (Dict): Contexto compartido (resultados de tareas previas)
- `params` (Dict): Parámetros de configuración

**Retorna:**
- `Dict[str, Any]`: Resultado de la ejecución
  ```python
  {
      "success": bool,
      # ... otros campos específicos de la tarea
  }
  ```

**Ejemplo:**

```python
def execute(self, context, params):
    # Acceder a resultados previos
    prev_data = context.get("tarea_anterior", {})
    
    # Ejecutar lógica
    result = self.procesar_datos(params["input"])
    
    # Retornar resultado
    return {
        "success": True,
        "output": result,
        "rows_processed": len(result)
    }
```

### Métodos con Implementación por Defecto

#### `run(context: Dict[str, Any], params: Dict[str, Any]) -> Any`

Template Method que orquesta la ejecución.

**Flujo:**
1. Llama `before(params)`
2. Llama `validate_params(params)`
3. Llama `execute(context, params)`
4. Llama `after(result)`
5. Si hay error, llama `on_error(e)` y relanza excepción

**No debe ser sobrescrito** (usa hooks en su lugar).

#### `before(params: Dict[str, Any]) -> None`

Hook ejecutado antes de validación y ejecución.

**Ejemplo de sobrescritura:**

```python
def before(self, params):
    super().before(params)
    print(f"[MiTarea] Configuración: {params}")
    self.start_time = time.time()
```

#### `after(result: Any) -> None`

Hook ejecutado después de ejecución exitosa.

**Ejemplo de sobrescritura:**

```python
def after(self, result):
    super().after(result)
    elapsed = time.time() - self.start_time
    print(f"[MiTarea] Completada en {elapsed:.2f}s")
```

#### `on_error(error: Exception) -> Dict[str, Any]`

Hook de manejo de errores.

**Parámetros:**
- `error` (Exception): Excepción capturada

**Retorna:**
- `Dict[str, Any]`: Resultado de error (actualmente no se usa, solo logging)

**Ejemplo de sobrescritura:**

```python
def on_error(self, error):
    print(f"[MiTarea] Error: {error}")
    # Log adicional, alertas, etc.
    return {
        "success": False,
        "error": str(error),
        "error_type": type(error).__name__
    }
```

---

## WorkflowRepository

Gestiona persistencia de workflows y resultados.

### Constructor

```python
WorkflowRepository(db_path: str = "data/workflows.db")
```

**Parámetros:**
- `db_path` (str): Ruta al archivo SQLite

**Ejemplo:**

```python
from Worker.workflow.workflow_persistence import WorkflowRepository

# Producción
repo = WorkflowRepository(db_path="data/workflows.db")

# Tests
import tempfile
with tempfile.TemporaryDirectory() as tmpdir:
    repo = WorkflowRepository(db_path=f"{tmpdir}/test.db")
```

### Métodos

#### `save_workflow_run(...) -> int`

Guarda un registro de ejecución de workflow.

**Parámetros:**

```python
save_workflow_run(
    workflow_name: str,
    status: str,
    results: Dict[str, Any],
    started_at: datetime,
    finished_at: datetime
) -> int
```

**Retorna:**
- `int`: ID del workflow creado

**Ejemplo:**

```python
from datetime import datetime

workflow_id = repo.save_workflow_run(
    workflow_name="Mi Workflow",
    status="RUNNING",
    results={},
    started_at=datetime.now(),
    finished_at=datetime.now()
)
```

#### `update_workflow_run(...) -> None`

Actualiza un registro existente de workflow.

**Parámetros:**

```python
update_workflow_run(
    workflow_id: int,
    status: str,
    results: Dict[str, Any],
    finished_at: datetime
) -> None
```

**Ejemplo:**

```python
repo.update_workflow_run(
    workflow_id=workflow_id,
    status="SUCCESS",
    results={"task1": {...}, "task2": {...}},
    finished_at=datetime.now()
)
```

#### `save_node_run(...) -> None`

Guarda resultado de ejecución de un nodo.

**Parámetros:**

```python
save_node_run(
    workflow_id: int,
    node_id: str,
    node_type: str,
    status: str,
    started_at: datetime,
    finished_at: datetime,
    result: Dict[str, Any]
) -> None
```

**Ejemplo:**

```python
repo.save_node_run(
    workflow_id=workflow_id,
    node_id="task1",
    node_type="http_get",
    status="SUCCESS",
    started_at=start_time,
    finished_at=end_time,
    result={"status_code": 200, "body": "..."}
)
```

---

## Models

### WorkflowDefinition

Definición de un workflow.

```python
@dataclass
class WorkflowDefinition:
    name: str
    nodes: List[WorkflowNode]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowDefinition"
```

**Ejemplo:**

```python
workflow = WorkflowDefinition(
    name="Mi Workflow",
    nodes=[
        WorkflowNode(id="task1", type="http_get", params={...}),
        WorkflowNode(id="task2", type="save_db", params={...}, depends_on=["task1"])
    ]
)

# O desde dict/JSON
workflow = WorkflowDefinition.from_dict({
    "name": "Mi Workflow",
    "nodes": [...]
})
```

### WorkflowNode

Nodo individual dentro de un workflow.

```python
@dataclass
class WorkflowNode:
    id: str                              # Identificador único en el workflow
    type: str                            # Tipo de tarea
    params: Dict[str, Any]              # Parámetros de configuración
    depends_on: List[str] = []          # IDs de nodos de los que depende
```

**Ejemplo:**

```python
node = WorkflowNode(
    id="fetch_data",
    type="http_get",
    params={"url": "https://api.example.com/data"},
    depends_on=[]  # Sin dependencias
)

node2 = WorkflowNode(
    id="save_data",
    type="save_db",
    params={"table": "data", "mode": "append"},
    depends_on=["fetch_data"]  # Depende de fetch_data
)
```

### WorkflowResult

Resultado de ejecución de un workflow.

```python
@dataclass
class WorkflowResult:
    workflow_name: str
    status: str                          # SUCCESS, PARTIAL_SUCCESS, FAILED
    results: Dict[str, Any] = {}        # Resultados por node_id
```

**Ejemplo:**

```python
result = engine.run(workflow)

print(result.workflow_name)  # "Mi Workflow"
print(result.status)          # "SUCCESS"
print(result.results["task1"])  # {"success": True, ...}
```

### TaskCommand

Comando para ejecutar una tarea (patrón Command).

```python
@dataclass
class TaskCommand:
    run_id: str                          # ID de ejecución
    node_key: str                        # Identificador del nodo
    type: str                            # Tipo de tarea
    params: Dict[str, Any] = {}         # Parámetros
    metadata: Dict[str, Any] = {}       # Metadata opcional
```

**Ejemplo:**

```python
from Worker.Task_command import TaskCommand

command = TaskCommand(
    run_id="workflow_123_task_1",
    node_key="task1",
    type="http_get",
    params={"url": "https://..."},
    metadata={"user_id": "user_123"}
)
```

### WorkflowRun (SQLModel)

Registro en BD de ejecución de workflow.

```python
class WorkflowRun(SQLModel, table=True):
    id: Optional[int]
    name: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime]
    duration: Optional[float]
    result_summary: Optional[str]  # JSON
```

**Consultar desde BD:**

```python
from sqlmodel import Session, select
from Worker.workflow.workflow_persistence import WorkflowRun

with Session(repo.engine) as session:
    # Obtener por ID
    run = session.get(WorkflowRun, 1)
    
    # Buscar por nombre
    runs = session.exec(
        select(WorkflowRun).where(WorkflowRun.name == "Mi Workflow")
    ).all()
    
    # Últimas 10 ejecuciones
    recent = session.exec(
        select(WorkflowRun)
        .order_by(WorkflowRun.started_at.desc())
        .limit(10)
    ).all()
```

### NodeRun (SQLModel)

Registro en BD de ejecución de nodo.

```python
class NodeRun(SQLModel, table=True):
    id: Optional[int]
    workflow_id: int
    node_id: str
    type: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime]
    duration: Optional[float]
    result_data: Optional[str]  # JSON
```

**Consultar desde BD:**

```python
from Worker.workflow.workflow_persistence import NodeRun

with Session(repo.engine) as session:
    # Nodos de un workflow
    nodes = session.exec(
        select(NodeRun).where(NodeRun.workflow_id == workflow_id)
    ).all()
    
    # Nodos fallidos
    failed = session.exec(
        select(NodeRun).where(NodeRun.status == "FAILED")
    ).all()
```

---

## Decorators

### TimeDecorator

Mide tiempo de ejecución de tareas.

```python
from Worker.decorador import TimeDecorator

decorated_task = TimeDecorator(task)
result = decorated_task.run(context, params)

# Output:
# [TaskName] ✅ Finalizada en 0.234s
```

### LoggingDecorator

Registra parámetros y resultados.

```python
from Worker.decorador import LoggingDecorator

decorated_task = LoggingDecorator(task)
result = decorated_task.run(context, params)

# Output:
# [TaskName] 📋 Registro de ejecución:
# {
#   "param1": "value1",
#   ...
# }
# [TaskName] 📤 Resultado: {...}
```

### Crear Decorador Personalizado

```python
from Worker.decorador import TaskDecorator
from typing import Dict, Any

class MiDecorador(TaskDecorator):
    """Decorador personalizado"""
    
    def run(self, context: Dict[str, Any], params: Dict[str, Any]) -> Any:
        # Antes
        print("Antes de ejecutar")
        
        try:
            # Ejecutar tarea envuelta
            result = self._wrapped_Task.run(context, params)
            
            # Después (si exitoso)
            print("Después de ejecutar")
            return result
            
        except Exception as e:
            # En caso de error
            print(f"Error: {e}")
            raise  # Re-lanzar para que WorkflowEngine lo detecte
```

**Configurar decoradores:**

```python
# Worker/config/decoradores_config.py
from Worker.decorador import TimeDecorator, LoggingDecorator, MiDecorador

TASK_DECORATOR_MAP = {
    "http_get": [TimeDecorator, LoggingDecorator],
    "mi_tarea": [TimeDecorator, MiDecorador],
}
```

---

## Tareas Incluidas

### HttpGetTask

Realiza solicitudes HTTP GET.

**Tipo:** `http_get`

**Parámetros:**

```python
{
    "url": str,              # URL a consultar (requerido)
    "headers": Dict[str, str]  # Headers HTTP (opcional)
}
```

**Resultado:**

```python
{
    "success": bool,
    "status_code": int,
    "body": str              # Primeros 500 caracteres
}
```

**Ejemplo:**

```json
{
  "id": "fetch",
  "type": "http_get",
  "params": {
    "url": "https://jsonplaceholder.typicode.com/todos/1",
    "headers": {"Authorization": "Bearer token"}
  }
}
```

### ValidateCSVTask

Valida estructura de archivo CSV.

**Tipo:** `validate_csv`

**Parámetros:**

```python
{
    "path": str,            # Ruta al archivo CSV (requerido)
    "columns": List[str]    # Columnas esperadas (requerido)
}
```

**Resultado:**

```python
{
    "valid": bool,
    "rows": int,
    "columns": List[str]
}
```

**Ejemplo:**

```json
{
  "id": "validate",
  "type": "validate_csv",
  "params": {
    "path": "data/input.csv",
    "columns": ["id", "nombre", "edad"]
  }
}
```

### TransformSimpleTask

Transforma datos de CSV (selección y renombre de columnas).

**Tipo:** `transform_simple`

**Parámetros:**

```python
{
    "input_path": str,                    # CSV de entrada (requerido)
    "output_path": str,                   # CSV de salida (requerido)
    "select_columns": List[str],          # Columnas a conservar (opcional)
    "rename_map": Dict[str, str]          # Renombres (opcional)
}
```

**Resultado:**

```python
{
    "output_path": str,
    "rows": int,
    "columns": List[str]
}
```

**Ejemplo:**

```json
{
  "id": "transform",
  "type": "transform_simple",
  "params": {
    "input_path": "data/input.csv",
    "output_path": "data/output.csv",
    "select_columns": ["id", "nombre"],
    "rename_map": {"nombre": "name"}
  }
}
```

### SaveDBTask

Guarda CSV en base de datos SQLite.

**Tipo:** `save_db`

**Parámetros:**

```python
{
    "path": str,            # Ruta al CSV (requerido)
    "table": str,           # Nombre de tabla (requerido)
    "mode": str             # "append" o "replace" (opcional, default: "append")
}
```

**Resultado:**

```python
{
    "success": bool,
    "table": str,
    "rows_inserted": int,
    "mode": str
}
```

**Ejemplo:**

```json
{
  "id": "save",
  "type": "save_db",
  "params": {
    "path": "data/output.csv",
    "table": "usuarios",
    "mode": "replace"
  }
}
```

### NotifyMockTask

Simula envío de notificación.

**Tipo:** `notify_mock`

**Parámetros:**

```python
{
    "channel": str,         # Canal de notificación (requerido)
    "message": str          # Mensaje a enviar (requerido)
}
```

**Resultado:**

```python
{
    "sent": bool,
    "channel": str,
    "message": str,
    "timestamp": str
}
```

**Ejemplo:**

```json
{
  "id": "notify",
  "type": "notify_mock",
  "params": {
    "channel": "slack",
    "message": "Workflow completado exitosamente"
  }
}
```

---

## Códigos de Error

| Error | Descripción | Solución |
|-------|-------------|----------|
| `ValueError: Unknown task type` | Tipo de tarea no registrado | Verificar `registry.register()` |
| `ValueError: Faltan parámetros` | Parámetros requeridos faltantes | Revisar `params` en JSON |
| `FileNotFoundError` | Archivo no encontrado | Verificar ruta del archivo |
| `RuntimeError: Dependencias circulares` | Ciclo en dependencias | Revisar `depends_on` en workflow |
| `ConnectionError` | Error de red/BD | Verificar conectividad |
| `TimeoutError` | Tarea excedió tiempo | Aumentar timeout o optimizar tarea |

---

## Versionamiento

Este proyecto sigue [Semantic Versioning](https://semver.org/):

- **MAJOR**: Cambios incompatibles en API
- **MINOR**: Nueva funcionalidad compatible
- **PATCH**: Bug fixes compatibles

**Versión actual:** 1.0.0