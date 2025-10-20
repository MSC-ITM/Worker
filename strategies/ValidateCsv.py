# app/tasks/validate_csv.py
import pandas as pd
from typing import Any, Dict, List
from strategies.base import ITask


class ValidateCSVTask(ITask):
    type = "validate_csv"
    display_name = "Validar CSV"
    description = "Verifica que un archivo CSV tenga las columnas esperadas."
    category = "Validación"
    icon = "file-text"
    params_schema = {
            "type": "object",
            "properties": {
                "path": {"type": "string", "title": "Ruta del archivo CSV"},
                "columns": {
                    "type": "array",
                    "title": "Columnas esperadas",
                    "items": {"type": "string"}
                }
            },
            "required": ["path", "columns"]
        }

    def validate_params(self, params):
        if "path" not in params or "columns" not in params:
            raise ValueError("Faltan parámetros: 'path' y 'columns'.")

    def execute(self, context, params):
        df = pd.read_csv(params["path"])
        missing = [c for c in params["columns"] if c not in df.columns]
        if missing:
            raise ValueError(f"Columnas faltantes: {missing}")
        return {"rows": len(df), "columns": list(df.columns)}

    def get_param_schema(self):
        return self.params_schema