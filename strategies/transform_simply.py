# app/tasks/transform_simple.py
import pandas as pd
import os
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
        path_in = params["input_path"]
        path_out = params["output_path"]

        if not os.path.exists(path_in):
            raise FileNotFoundError(f"Archivo de entrada no encontrado: {path_in}")

        df = pd.read_csv(path_in)

        if df.empty:
            raise ValueError("El archivo CSV de entrada está vacío.")

        if "select_columns" in params:
            missing = [c for c in params["select_columns"] if c not in df.columns]
            if missing:
                raise ValueError(f"Columnas faltantes en input: {missing}")
            df = df[params["select_columns"]]

        if "rename_map" in params:
            df = df.rename(columns=params["rename_map"])

        df.to_csv(path_out, index=False)
        return {"output_path": path_out, "rows": len(df), "columns": list(df.columns)}

    def on_error(self, error):
        print(f"[{self.__class__.__name__}] ⚠️ Error manejado: {error}")
        return {
            "output_path": None,
            "rows": 0,
            "columns": [],
            "error": str(error),
            "success": False
        }



