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
        try:
            time.sleep(1)  # Simula retardo
            print(f"[NotifyMockTask] Enviando notificación a {params['channel']}: {params['message']}")
            return {
                "sent": True,
                "channel": params["channel"],
                "message": params["message"],
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        except Exception as e:
            raise RuntimeError(f"Fallo al simular notificación: {e}")

    def on_error(self, error):
        print(f"[{self.__class__.__name__}] ⚠️ Error manejado: {error}")
        return {
            "sent": False,
            "channel": None,
            "message": None,
            "error": str(error)
        }

