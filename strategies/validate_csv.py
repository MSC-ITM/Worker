
import pandas as pd
import os
from typing import Any, Dict, List
from Worker.strategies.base import ITask


class ValidateCSVTask(ITask):
    """Tarea para validar estructura de archivos CSV"""
    type = "validate_csv"
    display_name = "Validar CSV"
    description = "Verifica que un archivo CSV tenga las columnas esperadas"
    category = "Validación"
    icon = "file-text"
    params_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "title": "Ruta del archivo CSV",
                "description": "Ruta absoluta o relativa"
            },
            "columns": {
                "type": "array",
                "title": "Columnas esperadas",
                "items": {"type": "string"},
                "minItems": 1,
                "description": "Lista de columnas que deben existir"
            },
            "allow_extra_columns": {
                "type": "boolean",
                "title": "Permitir columnas extra",
                "default": True
            }
        },
        "required": ["path", "columns"]
    }
    
    def validate_params(self, params: Dict[str, Any]) -> None:
        """Valida parámetros"""
        if "path" not in params:
            raise ValueError("Parámetro 'path' es obligatorio")
        
        if "columns" not in params:
            raise ValueError("Parámetro 'columns' es obligatorio")
        
        if not isinstance(params["columns"], list) or len(params["columns"]) == 0:
            raise ValueError("'columns' debe ser lista no vacía")
    
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Valida archivo CSV"""
        path = params["path"]
        expected_cols = params["columns"]
        allow_extra = params.get("allow_extra_columns", True)
        
        # 1. Verificar existencia
        if not os.path.exists(path):
            raise FileNotFoundError(f"Archivo no encontrado: {path}")
        
        # 2. Leer CSV
        try:
            df = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            raise ValueError(f"El archivo CSV está vacío: {path}")
        except Exception as e:
            raise RuntimeError(f"Error leyendo CSV: {e}")
        
        # 3. Verificar vacío
        if df.empty:
            raise ValueError("El archivo CSV no contiene datos")
        
        # 4. Verificar columnas
        actual_cols = list(df.columns)
        missing = [c for c in expected_cols if c not in actual_cols]
        
        if missing:
            raise ValueError(
                f"Columnas faltantes: {missing}. "
                f"Esperadas: {expected_cols}, "
                f"Encontradas: {actual_cols}"
            )
        
        # 5. Verificar columnas extra si no se permiten
        if not allow_extra:
            extra = [c for c in actual_cols if c not in expected_cols]
            if extra:
                raise ValueError(f"Columnas no esperadas: {extra}")
        
        return {
            "success": True,
            "valid": True,
            "path": path,
            "rows": len(df),
            "columns": actual_cols,
            "expected_columns": expected_cols,
            "has_extra_columns": len(actual_cols) > len(expected_cols)
        }
    
    def before(self, context: Dict[str, Any], params: Dict[str, Any]) -> None:
        """Hook: Log antes"""
        path = params.get("path", "N/A")
        expected = params.get("columns", [])
        self.logger.info(f"📄 Validando CSV: {path} (esperando {len(expected)} columnas)")
    
    def after(self, result: Any) -> None:
        """Hook: Log después"""
        rows = result.get("rows", 0)
        cols = len(result.get("columns", []))
        self.logger.info(f"✅ CSV válido: {rows} filas, {cols} columnas")
    
    def on_error(self, error: Exception, context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Manejo de error"""
        self.logger.error(f"❌ Validación CSV falló: {error}")
        
        return {
            "success": False,
            "valid": False,
            "error": str(error),
            "error_type": type(error).__name__,
            "path": params.get("path", "N/A"),
            "rows": 0,
            "columns": []
        }
