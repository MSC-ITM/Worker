# app/tasks/save_db.py
import sqlite3
import pandas as pd
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
            "path": {"type": "string", "title": "Ruta del CSV"},
            "table": {"type": "string", "title": "Nombre de la tabla"},
            "mode": {
                "type": "string",
                "title": "Modo de inserción",
                "enum": ["append", "replace"],
                "default": "append"
            }
        },
        "required": ["path", "table"]
    }

    def validate_params(self, params):
        if "path" not in params or "table" not in params:
            raise ValueError("Se requieren 'path' y 'table'.")

    def execute(self, context, params):
        conn = sqlite3.connect("data.db")
        df = pd.read_csv(params["path"])
        df.to_sql(params["table"], conn, if_exists=params.get("mode", "append"), index=False)
        conn.close()
        return {"table": params["table"], "rows_inserted": len(df)}

    def get_param_schema(self):
        return self.params_schema