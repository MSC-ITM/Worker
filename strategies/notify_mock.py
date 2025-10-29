# app/tasks/notify_mock.py

import time
from typing import Any, Dict, List
from Worker.strategies.base import ITask


class NotifyMockTask(ITask):
    type = "notify_mock"
    display_name = "Notificación Simulada"
    description = "Simula enviar una notificación a un canal (por ejemplo, Slack o email)."
    category = "Notificación"
    icon = "bell"

    params_schema = {
        "type": "object",
        "properties": {
            "channel": {
                "type": "string",
                "title": "Canal de notificación",
                "enum": ["email", "slack", "console", "webhook"],
                "description": "Canal donde enviar la notificación"
            },
            "message": {
                "type": "string",
                "title": "Mensaje a enviar",
                "minLength": 1,
                "maxLength": 500
            },
            "delay": {
                "type": "number",
                "title": "Delay en segundos",
                "default": 0.5,
                "minimum": 0,
                "maximum": 10
            }
        },
        "required": ["channel", "message"]
    }

    def validate_params(self, params):
        """Valida parámetros"""
        if "channel" not in params:
            raise ValueError("Parámetro 'channel' es obligatorio")
        
        if "message" not in params:
            raise ValueError("Parámetro 'message' es obligatorio")
        
        valid_channels = ["email", "slack", "console", "webhook"]
        if params["channel"] not in valid_channels:
            raise ValueError(f"'channel' debe ser uno de: {valid_channels}")
        
        if not isinstance(params["message"], str) or len(params["message"]) == 0:
            raise ValueError("'message' debe ser string no vacío")

  
    def execute(self, context, params):
        """Simula envío de notificación"""
        try:
            channel = params["channel"]
            message = params["message"]
            delay = params.get("delay", 0.5)
            
            # Simular delay de red
            time.sleep(delay)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
            self.logger.info(f"📢 Notificación enviada a {channel}: {message[:50]}...")
            
            return {
                "sent": True,
                "channel": channel,
                "message": message,
                "timestamp": timestamp,
            }
        except Exception as e:
            raise RuntimeError(f"Fallo al simular notificación: {e}")

    def before(self, context: Dict[str, Any], params: Dict[str, Any]) -> None:
        """Hook: Log antes"""
        channel = params.get("channel", "N/A")
        msg_preview = params.get("message", "")[:30]
        self.logger.info(f"📢 Enviando notificación a {channel}: {msg_preview}...")
    
    def after(self, result: Any) -> None:
        """Hook: Log después"""
        channel = result.get("channel", "N/A")
        self.logger.info(f"✅ Notificación enviada exitosamente a {channel}")
    
    def on_error(self, error: Exception, context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Manejo de error"""
        self.logger.error(f"❌ Error enviando notificación: {error}")
        
        return {
            "success": False,
            "sent": False,
            "error": str(error),
            "error_type": type(error).__name__,
            "channel": params.get("channel", "N/A"),
            "message": None
        }
