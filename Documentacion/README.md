# 🚀 Worker Engine - Sistema de Orquestación de Workflows

El **Worker** es el componente encargado de ejecutar de forma automática los workflows definidos desde el **Backend/API**, procesando cada tarea en el orden correcto, aplicando validaciones, registrando resultados y manejando errores.

Trabaja en segundo plano, monitoreando la base de datos compartida, detectando workflows pendientes y ejecutándolos paso a paso.

---

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Arquitectura](#-arquitectura)
- [Patrones de diseño utilizados](#️-patrones-de-diseño-utilizados)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Componentes Principales](#-componentes-principales)
- [Tareas incluidas por defecto](#-tareas-incluidas-por-defecto)
- [Problemas comunes y soluciones](#-problemas-comunes-y-soluciones)

---

## ✨ Características

- **Orquestación de Workflows**: Ejecuta flujos de trabajo con dependencias entre tareas
- **Comunicación APi-Worker**: Usa base de datos compartida (`workflows.db`) para comunicación API ↔ Worker
- **Sistema de Tareas Pluggable**: Añade nuevas tareas sin modificar el core
- **Persistencia Automática**: Guarda el historial de ejecuciones en SQLite
- **Extensible**: mediante patrones de diseño (Strategy, Factory, Template, Decorator)
- **Decoradores Configurables**: Añade logging, timing y otras funcionalidades cross-cutting
- **Manejo Robusto de Errores**: Gestión de fallos con recuperación parcial
- **Validación de Parámetros**: Valida inputs antes de la ejecución
- **Tests Automatizados**: Suite completa de tests con pytest

---



## 🏗️ Arquitectura

┌─────────────────────────────────────────────────────────────────┐
│                     CAPA DE PRESENTACIÓN                        │
│                        (Entry Point)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐                                               │
│  │  main.py    │  Punto de entrada CLI                         │
│  │             │  - Parse argumentos                           │
│  │             │  - Inicia WorkerService                       │
│  └─────────────┘                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    CAPA DE SERVICIOS                            │
│                   (Business Logic)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────┐        ┌──────────────────────┐     │
│  │  WorkerService       │───────→│  WorkflowEngine      │     │
│  │  (Polling Loop)      │        │  (Orchestration)     │     │
│  │                      │        │                      │     │
│  │ - Lee BD compartida  │        │ - Resuelve deps      │     │
│  │ - Convierte formatos │        │ - Ejecuta nodos      │     │
│  │ - Ejecuta workflows  │        │ - Propaga contexto   │     │
│  │ - Actualiza BD       │        │ - Maneja errores     │     │
│  └──────────────────────┘        └──────────────────────┘     │
│           │                                 │                  │
│           └─────────────┬───────────────────┘                  │
│                         ↓                                      │
│  ┌──────────────────────────────────────────────┐             │
│  │          WorkerEngine                        │             │
│  │          (Task Executor)                     │             │
│  │                                              │             │
│  │ - Recibe TaskCommand                        │             │
│  │ - Aplica Decoradores                        │             │
│  │ - Ejecuta Tareas (ITask)                    │             │
│  └──────────────────────────────────────────────┘             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    CAPA DE DOMINIO                              │
│              (Core Business Objects)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────────┐  ┌─────────────────┐  ┌────────────────┐  │
│  │ WorkflowNode   │  │ TaskCommand     │  │ WorkflowResult │  │
│  │                │  │                 │  │                │  │
│  │ - id           │  │ - run_id        │  │ - name         │  │
│  │ - type         │  │ - node_key      │  │ - status       │  │
│  │ - params       │  │ - type          │  │ - results      │  │
│  │ - depends_on   │  │ - params        │  │                │  │
│  └────────────────┘  └─────────────────┘  └────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────┐      │
│  │          WorkflowDefinition                          │      │
│  │          (Agregado raíz)                             │      │
│  │                                                      │      │
│  │ - name: str                                         │      │
│  │ - nodes: List[WorkflowNode]                        │      │
│  │ - from_dict() → crea desde JSON                    │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                 CAPA DE ESTRATEGIAS                             │
│              (Strategy + Template Method)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│              ┌───────────────────────┐                          │
│              │   ITask (Abstract)    │                          │
│              │   [Template Method]   │                          │
│              │                       │                          │
│              │ + run() [TEMPLATE]    │                          │
│              │ + validate_params()*  │                          │
│              │ + execute()*          │                          │
│              │ + before()            │                          │
│              │ + after()             │                          │
│              │ + on_error()          │                          │
│              └───────────────────────┘                          │
│                         △                                       │
│          ┌──────────────┼──────────────┐                       │
│          │              │              │                        │
│  ┌───────────┐  ┌──────────┐  ┌─────────────┐                │
│  │HttpGetTask│  │ValidateCSV│  │TransformTask│  ...           │
│  │           │  │Task       │  │             │                │
│  │[Strategy] │  │[Strategy] │  │  [Strategy] │                │
│  └───────────┘  └──────────┘  └─────────────┘                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                  CAPA DE DECORADORES                            │
│                  (Decorator Pattern)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│         ┌────────────────────────────────┐                     │
│         │   TaskDecorator (Base)         │                     │
│         │   - Envuelve ITask             │                     │
│         │   - Delega a _wrapped_task     │                     │
│         └────────────────────────────────┘                     │
│                      △                                          │
│         ┌────────────┼────────────┐                            │
│         │            │            │                            │
│  ┌─────────┐  ┌────────────┐  ┌───────────┐                  │
│  │  Time   │  │  Logging   │  │  Retry    │                  │
│  │Decorator│  │ Decorator  │  │ Decorator │                  │
│  │         │  │            │  │           │                  │
│  │- Mide   │  │- Logs      │  │- Reintentos│                  │
│  │  tiempo │  │  I/O       │  │- Backoff  │                  │
│  └─────────┘  └────────────┘  └───────────┘                  │
│                                                                 │
│  Ejemplo de aplicación:                                        │
│  TimeDecorator(LoggingDecorator(RetryDecorator(HttpGetTask))) │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│               CAPA DE FABRICACIÓN                               │
│          (Factory Method + Registry)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────┐                 │
│  │        TaskFactoryDirector                │                 │
│  │        (Director Pattern)                 │                 │
│  │                                           │                 │
│  │ + create(type: str) → ITask              │                 │
│  │                                           │                 │
│  │   All_posible_tasks = {                  │                 │
│  │     "http_get": http_getFactory,         │                 │
│  │     "validate_csv": validate_csvFactory, │                 │
│  │     ...                                   │                 │
│  │   }                                       │                 │
│  └───────────────────────────────────────────┘                 │
│                      △                                          │
│  ┌───────────────────┼────────────────────┐                   │
│  │                   │                    │                   │
│  │  http_getFactory  │  validate_csv...   │   ...             │
│  │  + create()       │  + create()        │                   │
│  └───────────────────┴────────────────────┘                   │
│                                                                 │
│  ┌───────────────────────────────────────────┐                 │
│  │        TaskRegistry                       │                 │
│  │        (Registry Pattern)                 │                 │
│  │                                           │                 │
│  │ - _registry: Dict[str, Type[ITask]]      │                 │
│  │ + register(task_name: str)               │                 │
│  │ + create(task_type: str) → ITask         │                 │
│  │ + list() → List[Type[ITask]]             │                 │
│  │ + clear()                                 │                 │
│  └───────────────────────────────────────────┘                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                 CAPA DE PERSISTENCIA                            │
│              (Repository Pattern)                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────────────────────────────────────┐                │
│  │      WorkflowRepository                    │                │
│  │      (Data Access Layer)                   │                │
│  │                                            │                │
│  │ + save_workflow_run()                      │                │
│  │ + save_node_run()                          │                │
│  │ + update_workflow_run()                    │                │
│  │ + create_workflow()                        │                │
│  │ + get_workflow()                           │                │
│  │ + list_workflows()                         │                │
│  │ + list_pending()                           │                │
│  └────────────────────────────────────────────┘                │
│                      │                                          │
│                      ↓                                          │
│  ┌────────────────────────────────────────────┐                │
│  │         SQLModel (ORM)                     │                │
│  │                                            │                │
│  │ - WorkflowDefinition (tabla)              │                │
│  │ - WorkflowRun (tabla)                     │                │
│  │ - NodeRun (tabla)                         │                │
│  └────────────────────────────────────────────┘                │
│                      │                                          │
│                      ↓                                          │
│              ┌───────────────┐                                 │
│              │  SQLite DB    │                                 │
│              │               │                                 │
│              │ - worker_     │                                 │
│              │   workflows.db│                                 │
│              └───────────────┘                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘


---

### 🔄 FLUJO DE DATOS (SECUENCIA)
```
┌────────┐
│  API   │ Crea workflow en database.db (status='en_espera')
└────┬───┘
     │
     ↓ (BD Compartida)
┌────────────────┐
│  database.db   │
│  ┌──────────┐  │
│  │Workflow  │  │ id: "wf-123"
│  │Table     │  │ status: "en_espera"
│  └──────────┘  │ definition: {...}
└────────────────┘
     │
     ↓ (Polling cada 10s)
┌──────────────────────────────────────────┐
│  WorkerService._poll_loop()              │
│                                          │
│  1. _get_pending_workflows_from_db()    │
│     → SELECT * WHERE status='en_espera' │
│                                          │
│  2. Para cada workflow:                 │
│     _execute_workflow(workflow)         │
└──────────────────────────────────────────┘
     │
     ↓
┌──────────────────────────────────────────┐
│  WorkerService._execute_workflow()       │
│                                          │
│  1. _update_workflow_status_in_db()     │
│     → UPDATE status='en_progreso'       │
│                                          │
│  2. _convert_api_workflow_to_definition│
│     API Format → WorkflowDefinition     │
│     {                                    │
│       steps: [...]  → nodes: [...]     │
│     }                                    │
│                                          │
│  3. workflow_engine.run(workflow_def)   │
└──────────────────────────────────────────┘
     │
     ↓
┌──────────────────────────────────────────┐
│  WorkflowEngine.run()                    │
│                                          │
│  Para cada nodo en orden topológico:    │
│                                          │
│  1. Crear TaskCommand                   │
│     {                                    │
│       run_id: "wf-123",                 │
│       node_key: "step_0",               │
│       type: "http_get",                 │
│       params: {...}                     │
│     }                                    │
│                                          │
│  2. worker_engine.execute_command(cmd)  │
└──────────────────────────────────────────┘
     │
     ↓
┌──────────────────────────────────────────┐
│  WorkerEngine.execute_command()          │
│                                          │
│  1. registry.create(type)               │
│     → HttpGetTask()                     │
│                                          │
│  2. _apply_decorators(task)             │
│     → TimeDecorator(                    │
│         LoggingDecorator(               │
│           RetryDecorator(               │
│             HttpGetTask())))            │
│                                          │
│  3. decorated_task.run(context, params) │
└──────────────────────────────────────────┘
     │
     ↓
┌──────────────────────────────────────────┐
│  ITask.run() [TEMPLATE METHOD]           │
│                                          │
│  1. before(context, params)             │
│     → Log: "Ejecutando HTTP GET..."    │
│                                          │
│  2. validate_params(params)             │
│     → Valida URL obligatoria            │
│                                          │
│  3. execute(context, params)            │
│     → requests.get(url)                 │
│     → return {status: 200, body: "..."} │
│                                          │
│  4. after(result)                       │
│     → Log: "Completado con status 200" │
│                                          │
│  5. [si error] on_error(error)          │
│     → return {success: false, error}    │
└──────────────────────────────────────────┘
     │
     ↓ (Resultado)
┌──────────────────────────────────────────┐
│  WorkflowEngine (continuación)           │
│                                          │
│  - Guardar resultado en context         │
│  - context["step_0"] = {status: 200...} │
│                                          │
│  - repo.save_node_run()                 │
│    → INSERT INTO noderun (...)          │
│                                          │
│  - Pasar al siguiente nodo              │
│    con contexto actualizado              │
└──────────────────────────────────────────┘
     │
     ↓ (Al terminar todos los nodos)
┌──────────────────────────────────────────┐
│  WorkflowEngine.run() [finalización]     │
│                                          │
│  - Determinar estado global:            │
│    * Todos SUCCESS → "SUCCESS"          │
│    * Alguno SUCCESS → "PARTIAL_SUCCESS" │
│    * Todos FAILED → "FAILED"            │
│                                          │
│  - repo.update_workflow_run()           │
│    → UPDATE workflowrun SET status=...  │
│                                          │
│  - return WorkflowResult(               │
│      name="simple_flow",                │
│      status="SUCCESS",                  │
│      results={...}                      │
│    )                                     │
└──────────────────────────────────────────┘
     │
     ↓
┌──────────────────────────────────────────┐
│  WorkerService (finalización)            │
│                                          │
│  - _map_worker_status_to_api()          │
│    "SUCCESS" → "completado"             │
│                                          │
│  - _update_workflow_status_in_db()      │
│    → UPDATE database.db                 │
│      SET status='completado',           │
│          definition={...results...}     │
└──────────────────────────────────────────┘
     │
     ↓
┌────────────────┐
│  database.db   │ status: "completado"
│  ┌──────────┐  │ definition: {
│  │Workflow  │  │   ...original...,
│  │Table     │  │   execution_results: {...}
│  └──────────┘  │ }
└────────────────┘
     │
     ↓
┌────────┐
│  API   │ Lee estado actualizado
└────────┘ GET /workflows/{id}/status
           → { status: "completado" }

```


### 🔧 ¿Cómo funciona el flujo de ejecución?

| Etapa | Componente | Descripción |
|-------|------------|-------------|
| 1️⃣ Polling | `WorkerService` | Busca workflows con estado `en_espera` en la BD |
| 2️⃣ Preparación | `WorkflowEngine` | Convierte nodos a tareas ejecutables |
| 3️⃣ Resolución | `TaskRegistry + Factory` | Crea la clase concreta correspondiente a cada task (`http_get`, `validate_csv`, etc.) |
| 4️⃣ Ejecución | `ITask.run()` | Ejecuta lógica con Template Method (`before → validate → execute → after`) |
| 5️⃣ Decoradores | `TimeLogger / Retry / etc.` | Se aplican dinámicamente a las tareas (Decorator Pattern) |
| 6️⃣ Persistencia | `workflow_persistence.py` | Se almacenan resultados, duración, errores, etc. en la BD |

---

## 🏗️ Patrones de diseño utilizados

| Patrón | Aplicación en el Worker |
|--------|-------------------------|
| **Template Method** | `ITask.run()` define ejecución estándar, subclases solo implementan `validate` y `execute` |
| **Strategy** | Cada tarea es una estrategia intercambiable (`HttpGetTask`, `SaveDBTask`, etc.) |
| **Factory Method** | `FactoryM.create_task()` crea instancias basadas en tipo dinámico `"http_get"` |
| **Registry Pattern** | `TaskRegistry` mantiene un mapa `{ "http_get": Clase }` |
| **Decorator Pattern** | Decoradores como timeout, logging o retry envuelven la ejecución de tareas |
| **Repository Pattern** | `workflow_persistence.py` y `WorkflowRepository` gestionan BD |
| **Polling Service** | Worker es un servicio que se ejecuta en loop esperando trabajo |

---



## 📁 Estructura del Proyecto

```
Proyecto U2/
└── Worker/
    │
    ├── main.py # Punto de entrada del Worker
    ├── Task_command.py # DTO de comandos de tarea
    ├── worker_engine.py # Motor de ejecución de tareas
    ├── registry.py # Registro dinámico de clases de tarea
    ├── FactoryM.py # Factory Method para instancias ITask
    ├── decorador.py # Decoradores aplicables a tareas
    │
    ├── service/
    │ └── worker_service.py # Servicio que lee BD y dispara workflows
    │
    ├── Models/
    │ └── shared_workflow_table.py # Modelo de tabla que se usa en BD del API
    │
    ├── workflow/
    │ ├── workflow_engine.py # Ejecuta nodo por nodo
    │ ├── workflow_models.py # Dataclasses de workflow y nodos
    │ └── workflow_persistence.py # Persistencia de ejecución
    │
    ├── strategies/ # Catálogo de tareas implementadas
    │ ├── base.py # ITask: clase padre (Template Method)
    │ ├── Http_get.py
    │ ├── validate_csv.py
    │ ├── transform_simply.py
    │ ├── save_db.py
    │ └── notify_mock.py
    │
    ├── config/
    │ └── decoradores_config.py # Mapeo de decoradores por tarea
    └── Tests/                    # Suite de tests
        ├── test_factory_method.py              # ✅ Tests de Factory Method
        │   ├── test_create_http_get()
        │   ├── test_create_notify_mock()
        │   ├── test_create_save_db()
        │   ├── test_create_transform_simple()
        │   ├── test_create_validate_csv()
        │   └── test_invalid_task_type()
        │
        ├── test_registry.py                    # ✅ Tests de Registry
        │   ├── test_register_and_create()
        │   ├── test_register_invalid_task()
        │   ├── test_duplicate_registration()
        │   ├── test_list_tasks()
        │   └── test_clear_registry()
        │
        ├── test_workflow_integration.py        # ✅ Tests de Workflows
        │   ├── test_run_simple_workflow()
        │   ├── test_run_workflow_with_error()
        │   ├── test_workflow_with_branching()
        │   ├── test_workflow_persistence_in_db()
        │   ├── test_workflow_list_all()
        │   ├── test_workflow_status_update()
        │   ├── test_workflow_list_pending()
        │   ├── test_workflow_with_dependencies()
        │   ├── test_workflow_skips_on_failed_dependency()
        │   └── test_workflow_from_dict()
        │
        ├── test_worker_service.py              # ✅ Tests del Servicio de Polling
        │   ├── test_get_pending_workflows_empty_db()
        │   ├── test_get_pending_workflows_with_data()
        │   ├── test_get_pending_workflows_structure()
        │   ├── test_update_workflow_status_success()
        │   ├── test_update_workflow_status_with_results()
        │   ├── test_update_workflow_status_nonexistent()
        │   ├── test_convert_api_workflow_to_definition_simple()
        │   ├── test_convert_api_workflow_empty_steps()
        │   ├── test_map_step_type_all_types()
        │   ├── test_map_step_type_unknown()
        │   ├── test_map_worker_status_to_api()
        │   ├── test_execute_workflow_success()
        │   ├── test_execute_workflow_marks_in_progress()
        │   ├── test_execute_workflow_with_error()
        │   ├── test_worker_service_initialization()
        │   ├── test_worker_service_start_stop()
        │   ├── test_worker_service_get_stats()
        │   ├── test_worker_service_processes_multiple_workflows()
        │   └── test_end_to_end_workflow_execution()
```

---

## 🧩 Componentes Principales

### 1. WorkflowEngine

Orquesta la ejecución de workflows con dependencias entre tareas.

**Responsabilidades:**
- Resolver dependencias entre nodos
- Ejecutar tareas en orden correcto
- Manejar fallos parciales (PARTIAL_SUCCESS)
- Persistir estado de ejecución

```python
class WorkflowEngine:
    def run(self, workflow: WorkflowDefinition) -> WorkflowResult:
        """Ejecuta un workflow completo"""
```

### 2. WorkerEngine

Ejecuta comandos individuales aplicando decoradores.

**Responsabilidades:**
- Instanciar tareas desde el registry
- Aplicar decoradores configurados
- Ejecutar y capturar resultados
- Manejar errores

```python
class WorkerEngine:
    def execute_command(self, command: TaskCommand, context=None):
        """Ejecuta un comando individual"""
```

### 3. Taskregistry (Factory)

Catálogo centralizado de tareas disponibles.

```python
registry = Taskregistry()
registry.register(HttpGetTask)
registry.register(ValidateCSVTask)

# Crear instancia
task = registry.create("validate_csv")
```

### 4. ITask (Strategy Pattern)

Interfaz base para todas las tareas.

```python
class ITask(ABC):
    def execute(self, context, params) -> dict:
        """Lógica principal"""
        
    def validate_params(self, params) -> bool:
        """Validación de parámetros"""
        
    def run(self, context, params):
        """Template Method"""
```

### 5. WorkflowRepository

Gestiona la persistencia de workflows y resultados.

**Modelos:**
- `WorkflowRun`: Registro de ejecución de workflow
- `NodeRun`: Registro de ejecución de nodo individual

---

## 🧩 Tareas incluidas por defecto

| Tarea (`type`) | Propósito | Archivo |
|----------------|-----------|---------|
| `http_get` | Realiza una petición HTTP GET | `Http_get.py` |
| `validate_csv` | Valida estructura de un CSV | `validate_csv.py` |
| `transform_simple` | Aplica transformaciones simples a datos | `transform_simply.py` |
| `save_db` | Inserta datos procesados en una tabla | `save_db.py` |
| `notify_mock` | Envía una notificación de prueba (console/log) | `notify_mock.py` |

---

## 🚨 Problemas comunes y soluciones
Problema: DetachedInstanceError	
Causa: La sesión SQLAlchemy se cierra antes de leer el objeto	
Solución: Usar session.refresh() o evitar acceso después del commit

Problema: Table already defined
Causa: Múltiple carga de modelos SQLModel
Solución: Asegurar que los modelos no se redefinen en tests

Problema:Worker no ejecuta nada
Causa: No hay workflows con estado en_espera	
Solucion:Confirmar con SELECT * FROM workflowtable

Problema: str has no attribute get	
Causa:definition fue guardado como string no JSON	
Solución: Asegurarse de hacer json.dumps() al insertar y json.loads() al leer

Problema: Decoradores no aplican
Causa: Falta mapeo en decoradores_config.py	
Solución: Verificar que "http_get": ["TimeDecorator"] exista
