
import time
import functools

def task_wrapper(func):
    """
    Decorador genérico para métodos de tarea.
    - Mide tiempo de ejecución.
    - Imprime inicio y fin.
    - Captura errores.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        task_name = self.__class__.__name__
        start = time.time()
        print(f"[{task_name}] ▶️ Inicio de ejecución de '{func.__name__}'")
        try:
            result = func(self, *args, **kwargs)
            elapsed = round(time.time() - start, 3)
            print(f"[{task_name}] ✅ Finalizada en {elapsed}s")
            return result
        except Exception as e:
            elapsed = round(time.time() - start, 3)
            print(f"[{task_name}] ❌ Error tras {elapsed}s: {e}")
            raise
    return wrapper


"""
Versión de Decorator según clase
"""
