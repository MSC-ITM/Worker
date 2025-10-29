# config/decorators_config.py
from Worker.decorador import TimeDecorator, LoggingDecorator

# Mapeo: tipo_de_tarea → lista de decoradores (en orden de aplicación)
TASK_DECORATOR_MAP = {
    "http_get": [
        TimeDecorator,
        LoggingDecorator
    ],
    "validate_csv": [
        TimeDecorator,
        LoggingDecorator
    ],
    "transform_simple": [
        TimeDecorator,
        LoggingDecorator
    ],
    "save_db": [
        TimeDecorator,
        LoggingDecorator
    ],
    "notify_mock": [
        TimeDecorator
    ]
}