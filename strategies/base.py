from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging

class ITask(ABC):
    """
    Clase base para todas las tareas del Worker usando Template Method Pattern..

    Implementa el patrón Template Method:
    - Define la estructura de ejecución estándar (`run()`).
    - Permite personalizar pasos específicos mediante hooks (`before`, `after`, `on_error`).
    - Obliga a implementar `validate_params()` y `execute()` en subclases.

    Todas las tareas que hereden de esta clase deben:
    1. Definir el atributo metadatos de cada tarea.
    2. Implementar `validate_params()` → valida los parámetros de entrada.
    3. Implementar `execute()` → realiza la lógica principal de la tarea.
    4. (Opcional) Sobrescribir `on_error()` si necesitan manejo de errores personalizado.
    """
    """Cumple otras funciones como Class component del patrón decorator
    Tambien tiene la funcion de Class product en el patrón Factory Method
    """
    
    # ========== METADATOS DE LA TAREA ==========
    # Estos deben ser definidos por cada subclase
    type: str = NotImplemented
    display_name: str = NotImplemented
    description: str = NotImplemented
    category: str = "General"
    icon: str = "box"
    params_schema: Dict[str, Any] = {}
    
    def __init__(self):
        """Constructor que inicializa logger y estado"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self._execution_state = {
            "started": False,
            "completed": False,
            "failed": False,
            "error": None
        }
    
    # ========== TEMPLATE METHOD (NO SOBRESCRIBIR) ==========
    
    def run(self, context: Dict[str, Any], params: Dict[str, Any]) -> Any:
        """
        Template Method que define el flujo de ejecución estándar.
        
        Flujo:
        1. before() - Hook pre-ejecución
        2. validate_params() - Validación obligatoria
        3. execute() - Ejecución principal obligatoria
        4. after() - Hook post-ejecución
        5. on_error() - Hook de error (si ocurre)
        
        Args:
            context: Contexto compartido entre tareas (resultados previos)
            params: Parámetros específicos de esta tarea
            
        Returns:
            Resultado de execute() o dict de error si falla
            
        Raises:
            Exception: Solo si on_error() no puede manejar el error
        """
        self._execution_state["started"] = True
        
        # Hook 1: Antes de ejecutar (opcional)
        try:
            self.before(context, params)
        except Exception as e:
            self.logger.warning(f"Error en hook before(): {e}")
            # No detenemos la ejecución por error en hook
        
        try:
            # Paso 1: Validar parámetros (obligatorio)
            self.logger.debug(f"Validando parámetros: {params}")
            self.validate_params(params)
            
            # Paso 2: Ejecutar lógica principal (obligatorio)
            self.logger.debug(f"Ejecutando tarea con contexto: {list(context.keys())}")
            result = self.execute(context, params)
            
            # Marcar como completado
            self._execution_state["completed"] = True
            
            # Hook 2: Después de ejecutar exitosamente (opcional)
            try:
                self.after(result)
            except Exception as e:
                self.logger.warning(f"Error en hook after(): {e}")
                # No afecta el resultado
            
            return result
            
        except Exception as e:
            # Marcar como fallido
            self._execution_state["failed"] = True
            self._execution_state["error"] = e
            
            self.logger.error(f"Error ejecutando tarea: {e}", exc_info=True)
            
            # Hook 3: Manejo de error (opcional pero importante)
            try:
                error_result = self.on_error(e, context, params)
                
                # Si on_error retorna algo, usarlo como resultado
                if error_result is not None:
                    return error_result
                    
            except Exception as error_handler_exception:
                self.logger.error(
                    f"Error en on_error handler: {error_handler_exception}",
                    exc_info=True
                )
            
            # Re-lanzar excepción para que WorkerEngine la capture
            raise
    
    # ========== MÉTODOS ABSTRACTOS (OBLIGATORIOS) ==========
    
    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> None:
        """
        Valida los parámetros antes de ejecutar la tarea.
        
        DEBE implementarse en cada subclase.
        
        Args:
            params: Parámetros a validar
            
        Raises:
            ValueError: Si hay parámetros inválidos o faltantes
            TypeError: Si hay tipos incorrectos
            
        Ejemplo:
            def validate_params(self, params):
                if "url" not in params:
                    raise ValueError("Parámetro 'url' es obligatorio")
                if not isinstance(params["url"], str):
                    raise TypeError("'url' debe ser string")
        """
        pass
    
    @abstractmethod
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta la lógica principal de la tarea.
        
        DEBE implementarse en cada subclase.
        
        Args:
            context: Contexto compartido (ej: resultados de tareas previas)
            params: Parámetros de configuración de esta tarea
            
        Returns:
            Dict con el resultado de la ejecución. Debe incluir:
            - success (bool): Si la operación fue exitosa
            - Otros campos específicos de la tarea
            
        Ejemplo:
            def execute(self, context, params):
                result = do_something(params["input"])
                return {
                    "success": True,
                    "output": result,
                    "rows_processed": 100
                }
        """
        pass
    
    # ========== HOOKS OPCIONALES (PUEDEN SOBRESCRIBIRSE) ==========
    
    def before(self, context: Dict[str, Any], params: Dict[str, Any]) -> None:
        """
        Hook opcional ejecutado ANTES de validate_params() y execute().
        
        Por defecto no hace nada (silencioso).
        Sobrescribir si necesitas lógica pre-ejecución.
        
        Args:
            context: Contexto compartido
            params: Parámetros de la tarea
            
        Ejemplo:
            def before(self, context, params):
                super().before(context, params)
                self.logger.info(f"Preparando ejecución con {params}")
                self.setup_resources()
        """
        pass
    
    def after(self, result: Any) -> None:
        """
        Hook opcional ejecutado DESPUÉS de execute() exitoso.
        
        Por defecto no hace nada (silencioso).
        Sobrescribir si necesitas lógica post-ejecución.
        
        Args:
            result: Resultado retornado por execute()
            
        Ejemplo:
            def after(self, result):
                super().after(result)
                self.logger.info(f"Tarea completada: {result}")
                self.cleanup_resources()
        """
        pass
    
    def on_error(self, error: Exception, context: Dict[str, Any], params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Hook de manejo de errores ejecutado cuando falla validate_params() o execute().
        
        Por defecto solo registra el error.
        Sobrescribir para manejo personalizado.
        
        Args:
            error: Excepción capturada
            context: Contexto en el momento del error
            params: Parámetros que causaron el error
            
        Returns:
            Dict opcional con resultado de error. Si retorna None, se propaga la excepción.
            Si retorna dict, ese será el resultado de run() sin lanzar excepción.
        """
        self.logger.error(f"Error en {self.__class__.__name__}: {error}")
        # Por defecto no retorna nada, permitiendo que la excepción se propague
        return None
    
    # ========== MÉTODOS AUXILIARES ==========
    
    def get_execution_state(self) -> Dict[str, Any]:
        """
        Retorna el estado actual de ejecución de la tarea.
        
        Returns:
            Dict con started, completed, failed, error
        """
        return self._execution_state.copy()
    
    def is_completed(self) -> bool:
        """Retorna True si la tarea completó exitosamente"""
        return self._execution_state["completed"]
    
    def is_failed(self) -> bool:
        """Retorna True si la tarea falló"""
        return self._execution_state["failed"]
    
    def get_error(self) -> Optional[Exception]:
        """Retorna la excepción si la tarea falló, None en caso contrario"""
        return self._execution_state.get("error")
    