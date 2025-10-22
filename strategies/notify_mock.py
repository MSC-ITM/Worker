# app/tasks/notify_mock.py
import time
from typing import Any, Dict, List
from strategies.base import ITask


class NotifyMockTask(ITask):
    type = "notify_mock"
    display_name = "Notificación Simulada"
    description = "Simula enviar una notificación a un canal (por ejemplo, Slack o email)."
    category = "Notificación"
    icon = "bell"

    params_schema = {
        "type": "object",
        "properties": {
            "channel": {"type": "string", "title": "Canal de notificación"},
            "message": {"type": "string", "title": "Mensaje a enviar"}
        },
        "required": ["channel", "message"]
    }

    def validate_params(self, params):
        if "channel" not in params or "message" not in params:
            raise ValueError("Se requieren 'channel' y 'message'.")

    def execute(self, context, params):
        time.sleep(1)  # simulamos retardo
        return {
            "sent": True,
            "channel": params["channel"],
            "message": params["message"]
        }

