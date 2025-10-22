# app/tasks/http_get.py
import requests
from typing import Any, Dict, List
from strategies.base import ITask


class HttpGetTask(ITask):
    type = "http_get"
    display_name = "HTTP GET Request"
    description = "Realiza una solicitud HTTP GET a una URL."
    category = "Entrada"
    icon = "globe"
    params_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "title": "URL", "format": "uri"},
            "headers": {"type": "object", "title": "Encabezados", "additionalProperties": {"type": "string"}}
        },
        "required": ["url"]
    }

    def validate_params(self, params):
        if "url" not in params:
            raise ValueError("El parámetro 'url' es obligatorio.")

    def execute(self, context, params):
        try:
            response = requests.get(params["url"], headers=params.get("headers"))
            response.raise_for_status()
            return {
                "success":True,
                "status_code": response.status_code,
                "body": response.text[:500]
            }
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Error al realizar la solicitud HTTP: {e}")

    def on_error(self, error):
        print(f"[{self.__class__.__name__}] ⚠️ Error manejado: {error}")
        return {
            "status_code": None,
            "body": None,
            "error": str(error),
            "success": False
        }