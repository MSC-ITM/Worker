# app/tasks/transform_simple.py
import pandas as pd
from typing import Any, Dict, List
from strategies.base import ITask


class TransformSimpleTask(ITask):
    type = "transform_simple"
    display_name = "Transformar Datos (Simple)"
    description = "Realiza transformaciones básicas sobre un DataFrame (selección y renombre)."
    category = "Transformación"
    icon = "wand-2"
    params_schema = {
            "type": "object",
            "properties": {
                "input_path": {"type": "string", "title": "Ruta del CSV de entrada"},
                "output_path": {"type": "string", "title": "Ruta de salida"},
                "select_columns": {
                    "type": "array",
                    "title": "Columnas a conservar",
                    "items": {"type": "string"}
                },
                "rename_map": {
                    "type": "object",
                    "title": "Mapa de renombres (columna: nuevo_nombre)",
                    "additionalProperties": {"type": "string"}
                }
            },
            "required": ["input_path", "output_path"]
        }

    def validate_params(self, params):
        if "input_path" not in params or "output_path" not in params:
            raise ValueError("Se requieren 'input_path' y 'output_path'.")

    def execute(self, context, params):
        df = pd.read_csv(params["input_path"])
        if "select_columns" in params:
            df = df[params["select_columns"]]
        if "rename_map" in params:
            df = df.rename(columns=params["rename_map"])
        df.to_csv(params["output_path"], index=False)
        return {"output_path": params["output_path"], "rows": len(df)}

