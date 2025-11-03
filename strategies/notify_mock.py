import time
from typing import Any, Dict, List
from strategies.base import ITask
import platform
import subprocess
from win10toast import ToastNotifier

class NotifyMockTask(ITask):
    """Clase para enviar una notificacion del sistema al desktop"""
    """Subclase concrete del patrón template"""
    """Subclase  concrete component del patrón decorator"""
    """Sublcase concrete product del patrón factory method"""
    type = "notify_mock"
    display_name = "Notificación Simulada"
    description = "Simula enviar una notificación a un canal (por ejemplo, Slack o email)."
    category = "Notificación"
    icon = "bell"

    params_schema = {
        "type": "object",
        "properties": {
            "channel": "desknotification",
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
        if params["channel"] != "desknotification":
            raise ValueError(f"'channel' debe ser desknotification")
        
        if not isinstance(params["message"], str) or len(params["message"]) == 0:
            raise ValueError("'message' debe ser string no vacío")

  
    def execute(self, context, params):
        """Notificaciones nativas del sistema operativo"""
    
        sistema = platform.system()
        channel = params["channel"]
        titulo="Notificacion del Workflow"
        mensaje = params["message"]
        duration = 15
        
        try:
            if sistema == "Windows":
                # Windows 10/11 - toast notification
                toaster = ToastNotifier()
                toaster.show_toast(title=titulo, msg=mensaje, duration=duration)
                
            elif sistema == "Darwin":  # macOS
                # macOS notification
                subprocess.run([
                    'osascript', '-e',
                    f'display notification "{mensaje}" with title "{titulo}"'
                ])
                
            elif sistema == "Linux":
                # Linux (requiere libnotify)
                subprocess.run([
                    'notify-send', titulo, mensaje, '-t', str(duration * 1000)
                ])
                
            else:
                print(f"Notificación: {titulo} - {mensaje}")
            
            self.logger.info(f"📢 Notificación enviada a {channel}: {mensaje[:50]}...")
            
            return {
                "sent": True,
                "channel": channel,
                "message": mensaje,
            }
                
        except Exception as e:
            raise RuntimeError(f"Fallo al enviar notificación: {e}")
        

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