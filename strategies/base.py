from abc import ABC, abstractmethod
from typing import Any, Dict
#from Worker.Borrador_Decorator import task_wrapper

class ITask(ABC):
    """
    Clase base para todas las tareas del Worker.

    Implementa el patrón Template Method:
    - Define la estructura de ejecución estándar (`run()`).
    - Permite personalizar pasos específicos mediante hooks (`before`, `after`, `on_error`).
    - Obliga a implementar `validate_params()` y `execute()` en subclases.

    Todas las tareas que hereden de esta clase deben:
    1. Definir el atributo `type` (string) que las identifique.
    2. Implementar `validate_params()` → valida los parámetros de entrada.
    3. Implementar `execute()` → realiza la lógica principal de la tarea.
    4. (Opcional) Sobrescribir `on_error()` si necesitan manejo de errores personalizado.
    """
    #@abstractmethod
    def execute(self, params: dict) -> dict:
        """Ejecuta la tarea y retorna resultado"""
        pass
    
    #@abstractmethod
    def validate_params(self, params: dict) -> bool:
        """Valida parámetros antes de ejecutar"""
        pass

    # ======== Hooks opcionales (Template Method) ========

    def before(self, params: Dict[str, Any]):
        """Hook opcional que se ejecuta antes de la validación y ejecución."""
        print(f"[{self.__class__.__name__}] ▶️ Iniciando tarea con params: {params}")

    def after(self, result: Any):
        """Hook opcional que se ejecuta después de la ejecución exitosa."""
        print(f"[{self.__class__.__name__}] ✅ Finalizó correctamente con resultado: {result}")

    def on_error(self, error: Exception):
        """
        Hook de manejo de errores.
        - Se ejecuta automáticamente si ocurre una excepción en `validate_params()` o `execute()`.
        - Puede ser sobrescrito por cada subclase para devolver un resultado personalizado.

        Por defecto, devuelve un diccionario genérico con el mensaje de error.
        """
        print(f"[{self.__class__.__name__}] ❌ Error manejado por ITask: {error}")
        return {
            "success": False,
            "error": str(error)
        }
    # ======== Plantilla de ejecución ========
    #@task_wrapper
    def run(self, context: Dict[str, Any], params: Dict[str, Any]) -> Any:
        """
        Define el ciclo de vida estándar de ejecución de una tarea.
        Este método puede ser llamado por el Worker o el Orchestrator.

        Flujo:
        1. before(params)
        2. validate_params(params)
        3. execute(context, params)
        4. after(result)

        Maneja excepciones y llama `on_error()` si ocurre un fallo.

        Returns:
            Resultado de `execute()`, o relanza la excepción capturada.
        """
        self.before(params)
        try:
            self.validate_params(params)
            result = self.execute(context, params)
            self.after(result)
            return result
        except Exception as e:
            self.on_error(e)
            raise

