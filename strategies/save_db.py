# app/tasks/save_db.py
import sqlite3
import pandas as pd
import os
from typing import Any, Dict, List
from Worker.strategies.base import ITask


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
        path = params["path"]
        table = params["table"]
        mode = params.get("mode", "append")

        # 🧱 1️⃣ Validación de archivo
        if not os.path.exists(path):
            raise FileNotFoundError(f"El archivo '{path}' no existe.")

        # 🧱 2️⃣ Conexión a base de datos
        try:
            conn = sqlite3.connect("data.db")
        except sqlite3.Error as e:
            raise ConnectionError(f"No se pudo conectar a la base de datos: {e}")

        try:
            # 🧠 3️⃣ Lectura del CSV
            df = pd.read_csv(path)

            if df.empty:
                raise ValueError("El archivo CSV está vacío y no se insertó nada.")

            # 🧩 4️⃣ Inserción a tabla
            df.to_sql(table, conn, if_exists=mode, index=False)

            inserted = len(df)
            print(f"[SaveDBTask] {inserted} filas insertadas en la tabla '{table}'.")

            return {
                "table": table,
                "rows_inserted": inserted,
                "mode": mode,
                "success": True,
            }

        except pd.errors.EmptyDataError:
            raise ValueError("El archivo CSV está vacío o corrupto.")
        except sqlite3.Error as e:
            raise RuntimeError(f"Error al guardar en la base de datos: {e}")
        finally:
            conn.close()

    def on_error(self, error):
        print(f"[{self.__class__.__name__}] ⚠️ Error manejado: {error}")
        return {
            "table": None,
            "rows_inserted": 0,
            "success": False,
            "error": str(error),
        }
