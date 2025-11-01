# app/tasks/save_db.py

import sqlite3
import pandas as pd
import os
from typing import Any, Dict, List
from strategies.base import ITask


class SaveDBTask(ITask):
    type = "save_db"
    display_name = "Guardar en Base de Datos"
    description = "Guarda un archivo CSV en una tabla SQLite (modo append o replace)."
    category = "Salida"
    icon = "database"
    params_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "title": "Ruta del CSV"
            },
            "table": {
                "type": "string",
                "title": "Nombre de la tabla"
            },
            "mode": {
                "type": "string",
                "title": "Modo de inserción",
                "enum": ["append", "replace"],
                "default": "append"
            },
            "db_path": {
                "type": "string",
                "title": "Ruta de la BD",
                "default": "data.db"
            }
        },
        "required": ["path", "table"]
    }
    
    def validate_params(self, params: Dict[str, Any]) -> None:
        """Valida parámetros"""
        if "path" not in params:
            raise ValueError("Parámetro 'path' es obligatorio")
        
        if "table" not in params:
            raise ValueError("Parámetro 'table' es obligatorio")
        
        mode = params.get("mode", "append")
        if mode not in ["append", "replace"]:
            raise ValueError("'mode' debe ser 'append' o 'replace'")
        
        # Validar nombre de tabla
        table = params["table"]
        if not table or not table.replace("_", "").isalnum():
            raise ValueError("Nombre de tabla inválido")
       
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Guarda CSV en BD"""
        path = params["path"]
        table = params["table"]
        mode = params.get("mode", "append")
        db_path = params.get("db_path", "data.db")
        
        # 1. Validar archivo
        if not os.path.exists(path):
            raise FileNotFoundError(f"El archivo '{path}' no existe")
        
        # 2. Leer CSV
        try:
            df = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            raise ValueError("El archivo CSV está vacío")
        except Exception as e:
            raise RuntimeError(f"Error leyendo CSV: {e}")
        
        if df.empty:
            raise ValueError("El DataFrame está vacío, no hay datos para insertar")
        
        # 3. Conectar a BD
        try:
            conn = sqlite3.connect(db_path)
        except sqlite3.Error as e:
            raise ConnectionError(f"No se pudo conectar a la base de datos: {e}")
        
        try:
            # 4. Insertar en tabla
            df.to_sql(table, conn, if_exists=mode, index=False)
            rows_inserted = len(df)
            
            self.logger.info(f"💾 {rows_inserted} filas insertadas en '{table}'")
            
            return {
                "success": True,
                "table": table,
                "rows_inserted": rows_inserted,
                "mode": mode,
                "db_path": db_path,
                "columns": list(df.columns)
            }
            
        except sqlite3.Error as e:
            raise RuntimeError(f"Error al guardar en la base de datos: {e}")
        finally:
            conn.close()

    #----------------------------------------Hooks-----------------------------------------
    def before(self, context: Dict[str, Any], params: Dict[str, Any]) -> None:
        """Hook: Log antes"""
        table = params.get("table", "N/A")
        mode = params.get("mode", "append")
        self.logger.info(f"💾 Guardando en tabla '{table}' (modo: {mode})")
    
    def after(self, result: Any) -> None:
        """Hook: Log después"""
        rows = result.get("rows_inserted", 0)
        table = result.get("table", "N/A")
        self.logger.info(f"✅ {rows} filas guardadas en '{table}'")
    
    def on_error(self, error: Exception, context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Manejo de error"""
        self.logger.error(f"❌ Error guardando en BD: {error}")
        return {"success": False,
            "error": str(error),
            "error_type": type(error).__name__,
            "table": params.get("table", "N/A"),
            "rows_inserted": 0
        }

