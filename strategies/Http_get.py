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
        response = requests.get(params["url"], headers=params.get("headers"))
        return {"status_code": response.status_code, "body": response.text[:500]}
