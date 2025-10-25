# 🤝 Guía de Contribución

¡Gracias por tu interés en contribuir al Worker Engine! Esta guía te ayudará a hacer contribuciones efectivas.

---

## 📋 Tabla de Contenidos

- [Código de Conducta](#código-de-conducta)
- [Cómo Contribuir](#cómo-contribuir)
- [Configuración del Entorno](#configuración-del-entorno)
- [Estándares de Código](#estándares-de-código)
- [Testing](#testing)
- [Pull Requests](#pull-requests)
- [Reportar Bugs](#reportar-bugs)

---

## 📜 Código de Conducta

Este proyecto sigue el [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/). Al participar, se espera que mantengas este código.

---

## 🚀 Cómo Contribuir

### Tipos de Contribuciones

Aceptamos varios tipos de contribuciones:

- 🐛 **Bug fixes**: Corrección de errores
- ✨ **Features**: Nuevas funcionalidades
- 📝 **Documentación**: Mejoras en la documentación
- ✅ **Tests**: Añadir o mejorar tests
- 🎨 **Refactoring**: Mejoras en el código sin cambiar funcionalidad
- 🔧 **Tareas personalizadas**: Nuevos tipos de tareas

### Proceso General

1. **Fork** el repositorio
2. **Crea una rama** desde `main`
3. **Haz tus cambios** siguiendo los estándares
4. **Escribe tests** para tus cambios
5. **Asegúrate** que todos los tests pasen
6. **Commit** con mensajes descriptivos
7. **Push** a tu fork
8. **Crea un Pull Request**

---

## ⚙️ Configuración del Entorno

### 1. Fork y Clone

```bash
# Fork en GitHub, luego:
git clone https://github.com/TU_USUARIO/worker-engine.git
cd worker-engine

# Añade el repositorio original como upstream
git remote add upstream https://github.com/ORIGINAL_OWNER/worker-engine.git
```

### 2. Crear Entorno Virtual

```bash
# Crear entorno virtual
python -m venv venv

# Activar
# En Linux/Mac:
source venv/bin/activate
# En Windows:
venv\Scripts\activate
```

### 3. Instalar Dependencias

```bash
# Dependencias de producción
pip install -r requirements.txt

# Dependencias de desarrollo
pip install -r requirements-dev.txt
```

#### `requirements-dev.txt`

```txt
# Testing
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.11.0

# Linting
black>=23.0.0
flake8>=6.0.0
isort>=5.12.0
mypy>=1.5.0

# Documentation
sphinx>=7.0.0
sphinx-rtd-theme>=1.3.0
```

### 4. Verificar Instalación

```bash
# Ejecutar tests
pytest Worker/Tests/ -v

# Debe mostrar:
# ===== 5 passed in X.XXs =====
```

---

## 📏 Estándares de Código

### Estilo de Código

Seguimos [PEP 8](https://pep8.org/) con algunas extensiones:

```bash
# Formatear código con black
black Worker/

# Ordenar imports con isort
isort Worker/

# Verificar con flake8
flake8 Worker/ --max-line-length=100
```

### Configuración de Herramientas

#### `.flake8`

```ini
[flake8]
max-line-length = 100
exclude = 
    .git,
    __pycache__,
    venv,
    .pytest_cache
ignore = E203, W503
```

#### `pyproject.toml`

```toml
[tool.black]
line-length = 100
target-version = ['py39', 'py310', 'py311']
include = '\.pyi?$'

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

### Convenciones de Nombres

```python
# Clases: PascalCase
class HttpGetTask(ITask):
    pass

# Funciones y métodos: snake_case
def execute_command(self, command: TaskCommand):
    pass

# Constantes: UPPER_SNAKE_CASE
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# Variables privadas: _prefijo
class MyClass:
    def __init__(self):
        self._internal_state = {}
```

### Type Hints

Usa type hints en todas las funciones públicas:

```python
from typing import Dict, Any, Optional

def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ejecuta la tarea.
    
    Args:
        context: Contexto compartido entre tareas
        params: Parámetros de configuración
        
    Returns:
        Diccionario con el resultado de la ejecución
        
    Raises:
        ValueError: Si los parámetros son inválidos
    """
    pass
```

### Documentación de Código

#### Docstrings

Usa docstrings estilo Google:

```python
def mi_funcion(param1: str, param2: int) -> bool:
    """
    Descripción breve de la función.
    
    Descripción más detallada si es necesaria. Puede ser de varias líneas
    y explicar el comportamiento en detalle.
    
    Args:
        param1: Descripción del primer parámetro
        param2: Descripción del segundo parámetro
        
    Returns:
        True si la operación fue exitosa, False en caso contrario
        
    Raises:
        ValueError: Si param2 es negativo
        TypeError: Si param1 no es string
        
    Example:
        >>> mi_funcion("test", 5)
        True
    """
    pass
```

#### Comentarios

```python
# ✅ Buenos comentarios (explican el "por qué")
# Necesitamos timeout porque el servicio externo puede colgar
response = requests.get(url, timeout=30)

# ❌ Malos comentarios (repiten el código)
# Hace un GET request
response = requests.get(url)
```

---

## ✅ Testing

### Escribir Tests

#### Test de Unidad

```python
# Worker/Tests/test_mi_tarea.py
import pytest
from Worker.strategies.mi_tarea import MiTarea

class TestMiTarea:
    """Tests para MiTarea"""
    
    def setup_method(self):
        """Se ejecuta antes de cada test"""
        self.task = MiTarea()
    
    def test_execute_success(self):
        """Test de ejecución exitosa"""
        result = self.task.execute(
            context={},
            params={"key": "value"}
        )
        
        assert result["success"] == True
        assert "output" in result
    
    def test_validate_params_missing_required(self):
        """Test de validación con parámetro faltante"""
        with pytest.raises(ValueError, match="key es requerido"):
            self.task.validate_params({})
    
    def test_execute_with_context(self):
        """Test usando contexto de tareas previas"""
        context = {"prev_task": {"data": "test"}}
        result = self.task.execute(context, {"key": "value"})
        
        assert result["success"] == True
```

#### Test de Integración

```python
def test_workflow_integration(tmp_path):
    """Test de workflow completo"""
    # Arrange
    db_path = tmp_path / "test.db"
    repo = WorkflowRepository(db_path=str(db_path))
    # ... setup completo
    
    # Act
    result = engine.run(workflow)
    
    # Assert
    assert result.status == "SUCCESS"
    # ... más assertions
```

### Ejecutar Tests

```bash
# Todos los tests
pytest Worker/Tests/ -v

# Un archivo específico
pytest Worker/Tests/test_mi_tarea.py -v

# Un test específico
pytest Worker/Tests/test_mi_tarea.py::test_execute_success -v

# Con cobertura
pytest Worker/Tests/ --cov=Worker --cov-report=html

# Ver reporte de cobertura
open htmlcov/index.html
```

### Cobertura Mínima

- **Coverage global**: 80% mínimo
- **Nuevas funcionalidades**: 90% mínimo
- **Código crítico**: 100%

---

## 🔄 Pull Requests

### Antes de Crear un PR

1. **Actualiza tu fork**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Ejecuta todos los tests**:
   ```bash
   pytest Worker/Tests/ -v
   ```

3. **Verifica el estilo**:
   ```bash
   black Worker/ --check
   flake8 Worker/
   ```

4. **Actualiza documentación** si es necesario

### Estructura del PR

#### Título

Usa prefijos descriptivos:

```
feat: Añade tarea de envío de email
fix: Corrige bug en resolución de dependencias
docs: Actualiza README con ejemplos
test: Añade tests para HttpGetTask
refactor: Simplifica lógica de WorkflowEngine
```

#### Descripción

```markdown
## Descripción
Breve descripción de los cambios.

## Motivación
¿Por qué son necesarios estos cambios?

## Cambios
- Cambio 1
- Cambio 2
- Cambio 3

## Tests
- Test 1: describe qué prueba
- Test 2: describe qué prueba

## Screenshots (si aplica)
[Imágenes o GIFs]

## Checklist
- [ ] Los tests pasan localmente
- [ ] Añadí tests para mi cambio
- [ ] Actualicé la documentación
- [ ] El código sigue los estándares
- [ ] No hay conflictos con main
```

### Review Process

1. Un mantenedor revisará tu PR
2. Puede haber comentarios o solicitudes de cambios
3. Haz los cambios solicitados
4. Una vez aprobado, se hará merge

---

## 🐛 Reportar Bugs

### Antes de Reportar

1. Verifica que no sea un bug conocido en [Issues](https://github.com/OWNER/worker-engine/issues)
2. Asegúrate de usar la última versión
3. Intenta reproducir en un entorno limpio

### Template de Bug Report

```markdown
## Descripción del Bug
Descripción clara y concisa del bug.

## Para Reproducir
Pasos para reproducir el comportamiento:
1. Ir a '...'
2. Ejecutar '...'
3. Ver error

## Comportamiento Esperado
Qué esperabas que sucediera.

## Comportamiento Actual
Qué sucedió en realidad.

## Screenshots/Logs
Si aplica, añade screenshots o logs.

## Entorno
- OS: [e.g. Ubuntu 22.04]
- Python: [e.g. 3.11.2]
- Versión del Worker Engine: [e.g. 1.0.0]

## Contexto Adicional
Cualquier otra información relevante.
```

---

## 💡 Proponer Features

### Template de Feature Request

```markdown
## Problema/Necesidad
Describe el problema o necesidad que esta feature resolvería.

## Solución Propuesta
Describe la solución que te gustaría ver.

## Alternativas Consideradas
Describe otras alternativas que consideraste.

## Ejemplo de Uso
```python
# Código de ejemplo de cómo se usaría
```

## Impacto
- ¿Afecta a usuarios existentes?
- ¿Requiere breaking changes?
- ¿Qué complejidad tiene?
```

---

## 📦 Añadir Nueva Tarea

### Checklist

- [ ] Crear archivo en `Worker/strategies/`
- [ ] Heredar de `ITask`
- [ ] Implementar `validate_params()` y `execute()`
- [ ] Definir `type`, `display_name`, `description`
- [ ] Crear `params_schema` con JSON Schema
- [ ] Añadir tests completos
- [ ] Documentar en README
- [ ] Añadir ejemplo de uso

### Template

```python
# Worker/strategies/nueva_tarea.py
from Worker.strategies.base import ITask

class NuevaTarea(ITask):
    """
    Descripción de lo que hace la tarea.
    """
    type = "nueva_tarea"
    display_name = "Nueva Tarea"
    description = "Descripción para UI"
    category = "Categoría"
    icon = "icon-name"
    
    params_schema = {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "title": "Parámetro 1"}
        },
        "required": ["param1"]
    }
    
    def validate_params(self, params):
        """Valida parámetros de entrada"""
        if "param1" not in params:
            raise ValueError("param1 es requerido")
    
    def execute(self, context, params):
        """Ejecuta la lógica principal"""
        # Tu implementación
        return {"success": True, "result": "..."}
```

---

## 🎯 Prioridades Actuales

### High Priority
- [ ] Sistema de ejecución paralela
- [ ] API REST completa
- [ ] Dashboard web

### Medium Priority
- [ ] Más tipos de tareas (Email, Slack, etc.)
- [ ] Sistema de retry automático
- [ ] Integración con servicios cloud

### Low Priority
- [ ] Traducción a otros idiomas
- [ ] Temas personalizables
- [ ] Plugin system

---

## 📞 Contacto

- **GitHub Issues**: Para bugs y features
- **Email**: tu.email@ejemplo.com
- **Discord**: [Link al servidor] (si aplica)

---

## 🙏 Reconocimientos

Gracias a todos los que contribuyen a hacer este proyecto mejor:

- Contributor 1
- Contributor 2
- ...

---

¡Esperamos tu contribución! 🚀