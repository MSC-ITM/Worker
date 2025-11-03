import requests
from typing import Any, Dict, List
from strategies.base import ITask


class HttpGetTask(ITask):
    """Tarea que obtiene datos de una URL"""
    """Subclase concrete del patrón template"""
    """Subclase  concrete component del patrón decorator"""
    """Sublcase concrete product del patrón factory method"""
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
        
        if not isinstance(params["url"], str):
            raise TypeError("'url' debe ser string")
        
        if not params["url"].startswith(("http://", "https://")):
            raise ValueError("'url' debe comenzar con http:// o https://")

    def execute(self, context, params):
        """Ejecuta solicitud HTTP GET"""
        url = params["url"]
        headers = params.get("headers", {})
        timeout = params.get("timeout", 10)
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()

            # Intentar parsear como JSON, si falla usar texto
            try:
                data = response.json()
            except:
                data = response.text[:500]  # Primeros 500 caracteres si no es JSON

            return {
                "success": True,
                "status_code": response.status_code,
                "data": data,  # JSON parseado o texto
                "body": response.text[:500],  # Mantener por compatibilidad
                "headers": dict(response.headers),
                "url": url
            }
        except requests.exceptions.Timeout as e:  
            raise TimeoutError(f"Timeout al conectar a {url}: {e}")
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Error de conexión a {url}: {e}")
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"Error HTTP en {url}: {e}")
        except Exception as e:
            raise RuntimeError(f"Error inesperado en HTTP GET: {e}")
        
    #--- Hooks del template-----

    def before(self, context: Dict[str, Any], params: Dict[str, Any]) -> None:
        """Hook: Log antes de ejecutar"""
        self.logger.info(f"🌐 Realizando GET a: {params.get('url', 'N/A')}")
    
    def after(self, result: Any) -> None:
        """Hook: Log después de ejecutar"""
        status = result.get("status_code", "N/A")
        self.logger.info(f"✅ HTTP GET completado: Status {status}")

    def on_error(self, error: Exception, context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Manejo de error personalizado"""
        self.logger.error(f"❌ Error en HTTP GET: {error}")
        
        return {
            "success": False,
            "error": str(error),
            "error_type": type(error).__name__,
            "url": params.get("url", "N/A"),
            "status_code": None,
            "body": None
        }