# config/decorators_config.py
from Worker.decorador import TimeDecorator, LoggingDecorator

# Mapeo: tipo_de_tarea → lista de decoradores (en orden de aplicación)
TASK_DECORATOR_MAP = {
    "http_get": [TimeDecorator],
    "validate_csv": [TimeDecorator],
    "transform_simple": [TimeDecorator],
    "save_db": [TimeDecorator, LoggingDecorator],
    "notify_mock": []  # opcional, sin decoradores
}
