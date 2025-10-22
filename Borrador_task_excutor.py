#Template pattern

from typing import Dict, Any
from abc  import ABC

class TaskExecutor(ABC):
# ======== Hooks opcionales (Template Method) ========

    def before(self, params: Dict[str, Any]):
        """
        Hook opcional que se ejecuta antes de `execute()`.
        Puede ser usado para inicialización, logging o métricas.
        """
        pass

    def after(self, result: Any):
        """
        Hook opcional que se ejecuta después de `execute()`.
        Permite registrar resultados, métricas o limpieza de recursos.
        """
        pass

    def on_error(self, error: Exception):
        """
        Hook opcional que se ejecuta si ocurre un error durante `execute()`.
        Permite manejar fallos, reintentos o reportes personalizados.
        """
        print(f"[{self.__class__.__name__}] Error durante ejecución: {error}")

    # ======== Plantilla de ejecución ========

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
