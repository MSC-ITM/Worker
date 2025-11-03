
from typing import Dict, Any, Optional
import json
import time
import logging
from datetime import datetime, UTC
from functools import wraps
from abc import ABC
from strategies.base import ITask #Class component, 

class TaskDecorator(ITask):
    """
    Decorator:Clase base para los decoradores de tareas.
    Implementa la misma interfaz de BaseTask (ITask como Class component) para poder anidarse.
    Las concrete components son las tareas HttpGetTask, NotifyMockTask, SaveDBTask, TransformSimpleTask, ValidateCSVTask
    """
    def __init__(self, wrapped_task: ITask):
        """
        Args:
            wrapped_task: Tarea a decorar
        """
        super().__init__()  # Inicializar logger y estado
        self._wrapped_task = wrapped_task
        
        # Copiar metadata de la tarea envuelta
        self.type = wrapped_task.type
        self.display_name = wrapped_task.display_name
        self.description = wrapped_task.description
        self.category = wrapped_task.category
        self.icon = wrapped_task.icon
        self.params_schema = wrapped_task.params_schema
    
    @property
    def wrapped_task(self) -> ITask:
        """Acceso a la tarea envuelta"""
        return self._wrapped_task
    
    # Delegar métodos abstractos a la tarea envuelta
    def validate_params(self, params: Dict[str, Any]) -> None:
        """Delega validación a la tarea envuelta"""
        return self._wrapped_task.validate_params(params)
    
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Delega ejecución a la tarea envuelta"""
        return self._wrapped_task.execute(context, params)
    
    # Los hooks se pueden sobrescribir en decoradores específicos
    def before(self, context: Dict[str, Any], params: Dict[str, Any]) -> None:
        """Por defecto delega al wrapped task"""
        self._wrapped_task.before(context, params)
    
    def after(self, result: Any) -> None:
        """Por defecto delega al wrapped task"""
        self._wrapped_task.after(result)
    
    def on_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Por defecto delega al wrapped task"""
        return self._wrapped_task.on_error(error, context, params)


class TimeDecorator(TaskDecorator):
    """
    Decorador de tiempo de ejecución.
    Mide cuánto tarda la tarea en completarse y captura errores sin romper el flujo.
    """
    def run(self, context: Dict[str, Any], params: Dict[str, Any]) -> Any:
        task_name = self._wrapped_task.__class__.__name__
        start_time = time.time()

        self.logger.info(f"⏱️  [{task_name}] Iniciando ejecución...")

        try:
            # ✅ Ejecuta la tarea envuelta
            result = self._wrapped_task.run(context, params)
            duration = time.time() - start_time
            # Añadir duración al resultado
            if isinstance(result, dict):
                result["_execution_time_seconds"] = round(duration, 3)
            
            self.logger.info(f"✅ [{task_name}] Completada en {duration:.3f}s")
            
            return result

        except Exception as e:
            # Registrar tiempo incluso si falla
            duration = time.time() - start_time
            self.logger.error(f"❌ [{task_name}] Falló después de {duration:.3f}s")
            raise

class LoggingDecorator(TaskDecorator):
    """
    Decorador que imprime logs estructurados antes y después de la ejecución.
    """
    def __init__(self, wrapped_task: ITask, truncate_length: int = 200):
        super().__init__(wrapped_task)
        self.truncate_length = truncate_length
        
    def run(self, context: Dict[str, Any], params: Dict[str, Any]) -> Any:
        """Registra parámetros, ejecución y resultado
         - ✅ JSON formateado legible
         - ✅ Trunca valores largos
         - ✅ Sanitiza información sensible
        """
        task_name = self._wrapped_task.__class__.__name__
        
        # Log de parámetros (sanitizados)
        sanitized_params = self._sanitize_params(params)
        self.logger.info(
            f"📋 [{task_name}] Parámetros:\n"
            f"{json.dumps(sanitized_params, indent=2, ensure_ascii=False)}"
        )
        
        try:
            # Ejecutar tarea
            result = self._wrapped_task.run(context, params)
            
            # Log de resultado (truncado)
            truncated_result = self._truncate_result(result)
            self.logger.info(
                f"📤 [{task_name}] Resultado:\n"
                f"{json.dumps(truncated_result, indent=2, ensure_ascii=False)}"
            )
            
            return result
            
        except Exception as e:
            # Log de error
            self.logger.error(
                f"💥 [{task_name}] Error:\n"
                f"  Tipo: {type(e).__name__}\n"
                f"  Mensaje: {str(e)}"
            )
            raise
    
    def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitiza información sensible"""
        sanitized = params.copy()
        
        # Ocultar campos sensibles
        sensitive_keys = ["password", "token", "api_key", "secret", "auth"]
        for key in sanitized:
            if any(sens in key.lower() for sens in sensitive_keys):
                sanitized[key] = "***HIDDEN***"
        
        return sanitized
    
    def _truncate_result(self, result: Any) -> Any:
        """Trunca resultados largos para logging"""
        if isinstance(result, dict):
            truncated = {}
            for key, value in result.items():
                if isinstance(value, str) and len(value) > self.truncate_length:
                    truncated[key] = value[:self.truncate_length] + "..."
                else:
                    truncated[key] = value
            return truncated
        return result


class RetryDecorator(TaskDecorator):
    """
    Decorador que reintenta la tarea si falla.
    
    NUEVO: No existía en versión anterior.
    Útil para tareas con fallos transitorios (HTTP, BD, etc.)
    """
    
    def __init__(
        self,
        wrapped_task: ITask,
        max_retries: int = 3,
        delay_seconds: float = 1.0,
        backoff_multiplier: float = 2.0
    ):
        super().__init__(wrapped_task)
        self.max_retries = max_retries
        self.delay_seconds = delay_seconds
        self.backoff_multiplier = backoff_multiplier
    
    def run(self, context: Dict[str, Any], params: Dict[str, Any]) -> Any:
        """Ejecuta con reintentos exponenciales"""
        task_name = self._wrapped_task.__class__.__name__
        last_exception = None
        current_delay = self.delay_seconds
        
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    self.logger.warning(
                        f"🔄 [{task_name}] Reintento {attempt}/{self.max_retries} "
                        f"después de {current_delay:.1f}s"
                    )
                    time.sleep(current_delay)
                    current_delay *= self.backoff_multiplier
                
                # Intentar ejecutar
                result = self._wrapped_task.run(context, params)
                
                if attempt > 0:
                    self.logger.info(f"✅ [{task_name}] Éxito en intento {attempt + 1}")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    self.logger.warning(
                        f"⚠️  [{task_name}] Intento {attempt + 1} falló: {e}"
                    )
                else:
                    self.logger.error(
                        f"❌ [{task_name}] Todos los intentos fallaron después de "
                        f"{self.max_retries + 1} intentos"
                    )
        
        # Si llegamos aquí, todos los intentos fallaron
        raise last_exception

