# Worker/strategies/transform_simply.py

import pandas as pd
import os
from typing import Any, Dict, List, Optional
from Worker.strategies.base import ITask


class TransformSimpleTask(ITask):
    """Tarea para transformaciones básicas de datos CSV"""
    
    type = "transform_simple"
    display_name = "Transformar Datos (Simple)"
    description = "Realiza transformaciones básicas sobre CSV (selección y renombre)"
    category = "Transformación"
    icon = "wand-2"
    params_schema = {
        "type": "object",
        "properties": {
            "input_path": {
                "type": "string",
                "title": "Ruta del CSV de entrada"
            },
            "output_path": {
                "type": "string",
                "title": "Ruta de salida"
            },
            "select_columns": {
                "type": "array",
                "title": "Columnas a conservar",
                "items": {"type": "string"},
                "description": "Lista de columnas a mantener (opcional)"
            },
            "rename_map": {
                "type": "object",
                "title": "Mapa de renombres",
                "additionalProperties": {"type": "string"},
                "description": "Dict con columna_vieja: columna_nueva (opcional)"
            }
        },
        "required": ["input_path", "output_path"]
    }
    
    def validate_params(self, params: Dict[str, Any]) -> None:
        """Valida parámetros"""
        if "input_path" not in params:
            raise ValueError("Parámetro 'input_path' es obligatorio")
        
        if "output_path" not in params:
            raise ValueError("Parámetro 'output_path' es obligatorio")
        
        # Validar que input y output sean diferentes
        if params["input_path"] == params["output_path"]:
            raise ValueError("input_path y output_path deben ser diferentes")
        
        # Validar select_columns si existe
        if "select_columns" in params:
            if not isinstance(params["select_columns"], list):
                raise TypeError("'select_columns' debe ser lista")
            if len(params["select_columns"]) == 0:
                raise ValueError("'select_columns' no puede estar vacía")
        
        # Validar rename_map si existe
        if "rename_map" in params:
            if not isinstance(params["rename_map"], dict):
                raise TypeError("'rename_map' debe ser diccionario")
    
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Transforma datos CSV"""
        input_path = params["input_path"]
        output_path = params["output_path"]
        select_columns = params.get("select_columns")
        rename_map = params.get("rename_map")
        
        # 1. Verificar entrada
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Archivo de entrada no encontrado: {input_path}")
        
        # 2. Leer CSV
        try:
            df = pd.read_csv(input_path)
        except Exception as e:
            raise RuntimeError(f"Error leyendo CSV: {e}")
        
        if df.empty:
            raise ValueError("El archivo CSV de entrada está vacío")
        
        original_shape = df.shape
        
        # 3. Seleccionar columnas si se especifica
        if select_columns:
            missing = [c for c in select_columns if c not in df.columns]
            if missing:
                raise ValueError(
                    f"Columnas faltantes en input: {missing}. "
                    f"Disponibles: {list(df.columns)}"
                )
            df = df[select_columns]
        
        # 4. Renombrar columnas si se especifica
        if rename_map:
            # Verificar que columnas a renombrar existan
            missing = [c for c in rename_map.keys() if c not in df.columns]
            if missing:
                raise ValueError(
                    f"Columnas a renombrar no encontradas: {missing}. "
                    f"Disponibles: {list(df.columns)}"
                )
            df = df.rename(columns=rename_map)
        
        # 5. Guardar resultado
        try:
            # Crear directorio si no existe
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            df.to_csv(output_path, index=False)
        except Exception as e:
            raise RuntimeError(f"Error guardando CSV transformado: {e}")
        
        return {
            "success": True,
            "input_path": input_path,
            "output_path": output_path,
            "rows": len(df),
            "columns": list(df.columns),
            "original_columns": original_shape[1],
            "final_columns": len(df.columns),
            "columns_dropped": original_shape[1] - len(df.columns),
            "columns_renamed": len(rename_map) if rename_map else 0
        }
    
    def before(self, context: Dict[str, Any], params: Dict[str, Any]) -> None:
        """Hook: Log antes"""
        input_file = os.path.basename(params.get("input_path", "N/A"))
        self.logger.info(f"🔄 Transformando: {input_file}")
    
    def after(self, result: Any) -> None:
        """Hook: Log después"""
        rows = result.get("rows", 0)
        cols = len(result.get("columns", []))
        dropped = result.get("columns_dropped", 0)
        self.logger.info(
            f"✅ Transformación completada: {rows} filas, {cols} columnas "
            f"({dropped} eliminadas)"
        )
    
    def on_error(self, error: Exception, context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Manejo de error"""
        self.logger.error(f"❌ Error en transformación: {error}")
        
        return {
            "success": False,
            "error": str(error),
            "error_type": type(error).__name__,
            "input_path": params.get("input_path", "N/A"),
            "output_path": params.get("output_path", "N/A"),
            "rows": 0,
            "columns": []
            }
