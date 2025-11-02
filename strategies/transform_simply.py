# Worker/strategies/transform_simply.py

import pandas as pd
import json
import os
from typing import Any, Dict, List, Optional
from strategies.base import ITask


class TransformSimpleTask(ITask):
    """Tarea para transformar JSON/CSV a SQL INSERT statements"""

    type = "transform_simple"
    display_name = "Transformar a SQL"
    description = "Convierte JSON o CSV a SQL INSERT statements"
    category = "Transformación"
    icon = "wand-2"
    params_schema = {
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "title": "Nombre de la tabla SQL",
                "description": "Nombre de la tabla para los INSERT statements",
                "default": "data_table"
            },
            "select_columns": {
                "type": "array",
                "title": "Columnas a incluir (opcional)",
                "items": {"type": "string"},
                "description": "Lista de columnas a incluir en el SQL. Si no se especifica, se incluyen todas"
            }
        },
        "required": ["table_name"]
    }
    
    def validate_params(self, params: Dict[str, Any]) -> None:
        """Valida parámetros"""
        if "table_name" not in params:
            raise ValueError("Parámetro 'table_name' es obligatorio")

        # Validar que el nombre de tabla sea válido
        table_name = params["table_name"]
        if not table_name or not isinstance(table_name, str):
            raise ValueError("'table_name' debe ser un string no vacío")

        # Validar select_columns si existe
        if "select_columns" in params:
            if not isinstance(params["select_columns"], list):
                raise TypeError("'select_columns' debe ser lista")
            if len(params["select_columns"]) == 0:
                raise ValueError("'select_columns' no puede estar vacía")
    
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Transforma datos del contexto a SQL INSERT statements"""
        table_name = params.get("table_name", "data_table")
        select_columns = params.get("select_columns")

        # 1. Obtener datos del contexto (de nodos anteriores)
        data = None
        source_node = None

        self.logger.info(f"🔍 Buscando datos en el contexto. Nodos disponibles: {list(context.keys())}")

        # Buscar datos en el contexto - puede venir de http_get o validate_csv
        for node_id, node_result in context.items():
            if isinstance(node_result, dict):
                self.logger.debug(f"  Nodo '{node_id}' tiene keys: {list(node_result.keys())}")
                # De http_get: buscar 'data' o 'body'
                if 'data' in node_result:
                    raw_data = node_result.get('data')
                    self.logger.info(f"🔍 raw_data es tipo: {type(raw_data).__name__}")
                    # Si 'data' es un dict con un campo 'data' interno (APIs públicas), extraerlo
                    if isinstance(raw_data, dict) and 'data' in raw_data:
                        data = raw_data['data']
                        self.logger.info(f"✓ Datos extraídos desde campo 'data' anidado. Tipo: {type(data).__name__}")
                    else:
                        data = raw_data
                        self.logger.info(f"✓ Usando 'data' directamente. Tipo: {type(data).__name__}")
                    source_node = node_id
                    break
                elif 'body' in node_result:
                    raw_body = node_result.get('body')
                    # Si 'body' es un dict con un campo 'data' interno, extraerlo
                    if isinstance(raw_body, dict) and 'data' in raw_body:
                        data = raw_body['data']
                        self.logger.info(f"✓ Datos extraídos desde campo 'data' anidado en 'body'")
                    else:
                        data = raw_body
                    source_node = node_id
                    break
                # De validate_csv: buscar 'path' para leer el CSV
                elif 'path' in node_result:
                    csv_path = node_result['path']
                    # Verificar que el archivo existe
                    if not os.path.exists(csv_path):
                        self.logger.warning(f"Archivo CSV no encontrado en: {csv_path}")
                        continue
                    try:
                        df = pd.read_csv(csv_path)
                        data = df.to_dict('records')
                        source_node = node_id
                        self.logger.info(f"✓ Datos cargados desde CSV: {len(data)} filas")
                        break
                    except Exception as e:
                        self.logger.error(f"Error leyendo CSV {csv_path}: {e}")
                        raise RuntimeError(f"Error leyendo CSV del contexto: {e}")

        if data is None:
            # Crear mensaje de error detallado
            available_nodes = list(context.keys())
            error_msg = (
                f"No se encontraron datos en el contexto. "
                f"Este nodo debe estar conectado a un nodo http_get o validate_csv.\n"
                f"Nodos disponibles en el contexto: {available_nodes}\n"
            )
            if available_nodes:
                error_msg += "Estructura de cada nodo:\n"
                for nid, nres in context.items():
                    if isinstance(nres, dict):
                        error_msg += f"  - {nid}: {list(nres.keys())}\n"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        # 2. Convertir datos a DataFrame
        self.logger.info(f"🔍 Tipo de datos recibidos: {type(data).__name__}")
        self.logger.info(f"🔍 Muestra de datos: {str(data)[:200]}...")

        try:
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                # Si es un dict, intentar convertirlo a lista
                df = pd.DataFrame([data])
            else:
                error_msg = f"Los datos deben ser una lista de objetos o un objeto. Tipo recibido: {type(data).__name__}, Valor: {str(data)[:200]}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise RuntimeError(f"Error procesando datos: {e}")

        if df.empty:
            raise ValueError("Los datos recibidos están vacíos")

        original_columns = list(df.columns)
        original_rows = len(df)

        # 3. Seleccionar columnas si se especifica
        if select_columns:
            missing = [c for c in select_columns if c not in df.columns]
            if missing:
                raise ValueError(
                    f"Columnas faltantes: {missing}. "
                    f"Disponibles: {original_columns}"
                )
            df = df[select_columns]

        # 4. Generar CREATE TABLE statement basado en tipos de datos
        columns = list(df.columns)
        columns_str = ", ".join(columns)

        # Inferir tipos de datos para CREATE TABLE
        column_definitions = []
        for col in columns:
            # Obtener el tipo de dato predominante en la columna
            sample_val = df[col].dropna().iloc[0] if len(df[col].dropna()) > 0 else None

            if sample_val is None:
                col_type = "TEXT"
            elif isinstance(sample_val, (int, pd.Int64Dtype)):
                col_type = "INTEGER"
            elif isinstance(sample_val, (float, pd.Float64Dtype)):
                col_type = "REAL"
            else:
                col_type = "TEXT"

            column_definitions.append(f"{col} {col_type}")

        create_table_statement = (
            f"CREATE TABLE IF NOT EXISTS {table_name} (\n  "
            + ",\n  ".join(column_definitions)
            + "\n);"
        )

        # 5. Generar SQL INSERT statements
        sql_statements = []

        for _, row in df.iterrows():
            # Escapar valores y manejar NULL
            values = []
            for col in columns:
                val = row[col]
                if pd.isna(val):
                    values.append("NULL")
                elif isinstance(val, str):
                    # Escapar comillas simples
                    escaped_val = val.replace("'", "''")
                    values.append(f"'{escaped_val}'")
                elif isinstance(val, (int, float)):
                    values.append(str(val))
                else:
                    # Para otros tipos, convertir a string y escapar
                    escaped_val = str(val).replace("'", "''")
                    values.append(f"'{escaped_val}'")

            values_str = ", ".join(values)
            sql_statements.append(f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str});")

        # 6. Guardar archivo SQL en directorio data/
        try:
            # Crear directorio data si no existe
            output_dir = os.path.join(os.getcwd(), "data")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # Generar nombre de archivo basado en tabla con timestamp único
            from datetime import datetime
            import uuid
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = uuid.uuid4().hex[:6]  # ID único de 6 caracteres
            output_filename = f"{table_name}_{timestamp}_{unique_id}.sql"
            output_path = os.path.join(output_dir, output_filename)

            self.logger.info(f"📝 Guardando archivo SQL: {output_filename}")

            with open(output_path, 'w', encoding='utf-8') as f:
                # Escribir cabecera
                f.write(f"-- SQL INSERT statements generados desde nodo: {source_node}\n")
                f.write(f"-- Tabla: {table_name}\n")
                f.write(f"-- Filas: {len(sql_statements)}\n")
                f.write(f"-- Columnas: {columns_str}\n")
                f.write(f"-- Generado: {timestamp}\n\n")

                # Escribir CREATE TABLE
                f.write(create_table_statement + "\n\n")

                # Escribir statements
                for statement in sql_statements:
                    f.write(statement + "\n")

        except Exception as e:
            raise RuntimeError(f"Error guardando archivo SQL: {e}")

        return {
            "success": True,
            "source_node": source_node,
            "output_path": output_path,
            "output_filename": output_filename,
            "table_name": table_name,
            "rows": len(sql_statements),
            "columns": columns,
            "original_columns": original_columns,
            "statements_generated": len(sql_statements)
        }
    
    def before(self, context: Dict[str, Any], params: Dict[str, Any]) -> None:
        """Hook: Log antes"""
        table_name = params.get("table_name", "data_table")
        self.logger.info(f"🔄 Transformando datos del contexto a SQL para tabla '{table_name}'")

    def after(self, result: Any) -> None:
        """Hook: Log después"""
        rows = result.get("rows", 0)
        statements = result.get("statements_generated", 0)
        source_node = result.get("source_node", "desconocido")
        output_filename = result.get("output_filename", "output.sql")
        self.logger.info(
            f"✅ Transformación completada: {statements} INSERT statements generados desde nodo '{source_node}'"
        )
        self.logger.info(f"📄 Archivo guardado: {output_filename}")

    def on_error(self, error: Exception, context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Manejo de error"""
        self.logger.error(f"❌ Error en transformación a SQL: {error}")

        return {
            "success": False,
            "error": str(error),
            "error_type": type(error).__name__,
            "table_name": params.get("table_name", "data_table"),
            "rows": 0,
            "columns": [],
            "statements_generated": 0
        }
