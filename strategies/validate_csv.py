# app/tasks/validate_csv.py
import pandas as pd
import os 
from typing import Any, Dict, List
from Worker.strategies.base import ITask


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
        path = params["path"]

        # 1️⃣ Verifica existencia
        if not os.path.exists(path):
            raise FileNotFoundError(f"Archivo no encontrado: {path}")

        # 2️⃣ Lee CSV con pandas
        df = pd.read_csv(path)

        # 3️⃣ Verifica vacío
        if df.empty:
            raise ValueError("El archivo CSV está vacío.")

        # 4️⃣ Verifica columnas esperadas
        expected_cols = params["columns"]
        missing = [c for c in expected_cols if c not in df.columns]
        if missing:
            raise ValueError(f"Columnas faltantes: {missing}")

        # ✅ Si todo va bien
        return {
            "valid": True,
            "rows": len(df),
            "columns": list(df.columns)
        }

    def on_error(self, error):
        """Manejo personalizado de errores para CSV."""
        print(f"[{self.__class__.__name__}] ⚠️ Error manejado: {error}")
        # Devuelve un resultado estructurado en lugar de romper el flujo
        result = {
        "valid": False,
        "error": str(error),
        "rows": 0,
        "columns": []
        }
        # Guarda resultado de error en el contexto (opcional)
        self.last_result = result
        return result