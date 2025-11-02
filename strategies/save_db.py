# Worker/strategies/save_db.py

import sqlite3
import os
from typing import Any, Dict, List
from strategies.base import ITask


class SaveDBTask(ITask):
    """Tarea para ejecutar archivo SQL generado por transform_simple en SQLite"""

    type = "save_db"
    display_name = "Guardar en Base de Datos"
    description = "Ejecuta archivo SQL generado por transform_simple en base de datos SQLite"
    category = "Salida"
    icon = "database"
    params_schema = {
        "type": "object",
        "properties": {
            "db_path": {
                "type": "string",
                "title": "Ruta de la Base de Datos",
                "description": "Ruta donde se guardará la base de datos SQLite",
                "default": "data/output.db"
            }
        },
        "required": []
    }

    def validate_params(self, params: Dict[str, Any]) -> None:
        """Valida parámetros"""
        # db_path es opcional, usa default si no existe
        db_path = params.get("db_path", "data/output.db")

        # Validar que el path tenga extensión .db
        if not db_path.endswith('.db'):
            raise ValueError("La ruta de la base de datos debe terminar en '.db'")

    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta SQL file del contexto en SQLite"""
        db_path = params.get("db_path", "data/output.db")

        # 1. Obtener archivo SQL del contexto (del nodo transform_simple)
        sql_file_path = None
        source_node = None
        table_name = None

        self.logger.info(f"🔍 Buscando archivo SQL en el contexto. Nodos disponibles: {list(context.keys())}")

        # Buscar resultado de transform_simple en el contexto
        for node_id, node_result in context.items():
            if isinstance(node_result, dict):
                self.logger.debug(f"  Nodo '{node_id}' tiene keys: {list(node_result.keys())}")

                # Buscar nodo transform_simple que tiene 'output_path'
                if 'output_path' in node_result and 'table_name' in node_result:
                    sql_file_path = node_result.get('output_path')
                    table_name = node_result.get('table_name')
                    source_node = node_id
                    self.logger.info(f"✓ Archivo SQL encontrado desde nodo '{source_node}': {sql_file_path}")
                    break

        if sql_file_path is None:
            # Crear mensaje de error detallado
            available_nodes = list(context.keys())
            error_msg = (
                f"No se encontró archivo SQL en el contexto. "
                f"Este nodo debe estar conectado a un nodo 'transform_simple'.\n"
                f"Nodos disponibles en el contexto: {available_nodes}\n"
            )
            if available_nodes:
                error_msg += "Estructura de cada nodo:\n"
                for nid, nres in context.items():
                    if isinstance(nres, dict):
                        error_msg += f"  - {nid}: {list(nres.keys())}\n"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        # 2. Validar que el archivo SQL existe
        if not os.path.exists(sql_file_path):
            raise FileNotFoundError(f"El archivo SQL no existe: {sql_file_path}")

        # 3. Leer contenido del archivo SQL
        self.logger.info(f"📖 Leyendo archivo SQL: {os.path.basename(sql_file_path)}")
        try:
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
        except Exception as e:
            raise RuntimeError(f"Error leyendo archivo SQL: {e}")

        # 4. Extraer statements SQL (separados por ';')
        # Primero eliminar todos los comentarios
        lines = sql_content.split('\n')
        cleaned_lines = [line for line in lines if not line.strip().startswith('--')]
        cleaned_content = '\n'.join(cleaned_lines)

        # Luego dividir por ';' y limpiar
        sql_statements = [
            stmt.strip()
            for stmt in cleaned_content.split(';')
            if stmt.strip()  # Solo verificar que no esté vacío
        ]

        total_statements = len(sql_statements)
        self.logger.info(f"📝 Total de statements SQL a ejecutar: {total_statements}")

        if total_statements == 0:
            raise ValueError("No se encontraron statements SQL válidos en el archivo")

        # 5. Crear directorio de la BD si no existe
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            self.logger.info(f"📁 Directorio creado: {db_dir}")

        # 6. Conectar a BD SQLite
        self.logger.info(f"🔗 Conectando a base de datos: {db_path}")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
        except sqlite3.Error as e:
            raise ConnectionError(f"No se pudo conectar a la base de datos: {e}")

        # 7. Ejecutar statements SQL uno por uno con logging
        executed_count = 0
        failed_count = 0
        errors = []

        try:
            for i, statement in enumerate(sql_statements, 1):
                try:
                    cursor.execute(statement)
                    executed_count += 1

                    # Log cada 10 statements o en el último
                    if i % 10 == 0 or i == total_statements:
                        self.logger.info(f"⚡ Progreso: {i}/{total_statements} statements ejecutados ({int(i/total_statements*100)}%)")

                except sqlite3.Error as e:
                    failed_count += 1
                    error_detail = f"Statement {i}: {str(e)[:100]}"
                    errors.append(error_detail)
                    self.logger.warning(f"⚠️ {error_detail}")

            # Commit de todas las transacciones
            conn.commit()
            self.logger.info(f"💾 Cambios guardados en la base de datos")

            # Verificar filas insertadas
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_rows = cursor.fetchone()[0]
            self.logger.info(f"✅ Total de filas en tabla '{table_name}': {total_rows}")

            return {
                "success": True,
                "source_node": source_node,
                "sql_file": os.path.basename(sql_file_path),
                "db_path": db_path,
                "table_name": table_name,
                "total_statements": total_statements,
                "executed_statements": executed_count,
                "failed_statements": failed_count,
                "total_rows_in_table": total_rows,
                "errors": errors if errors else None
            }

        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Error ejecutando SQL: {e}")
        finally:
            cursor.close()
            conn.close()

    #----------------------------------------Hooks-----------------------------------------
    def before(self, context: Dict[str, Any], params: Dict[str, Any]) -> None:
        """Hook: Log antes"""
        db_path = params.get("db_path", "data/output.db")
        self.logger.info(f"💾 Preparando ejecución de SQL en base de datos: {db_path}")

    def after(self, result: Any) -> None:
        """Hook: Log después"""
        executed = result.get("executed_statements", 0)
        failed = result.get("failed_statements", 0)
        table = result.get("table_name", "N/A")
        total_rows = result.get("total_rows_in_table", 0)

        self.logger.info(
            f"✅ Ejecución completada: {executed} statements ejecutados correctamente, "
            f"{failed} fallidos. Tabla '{table}' tiene {total_rows} filas."
        )

    def on_error(self, error: Exception, context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Manejo de error"""
        self.logger.error(f"❌ Error guardando en BD: {error}")
        return {
            "success": False,
            "error": str(error),
            "error_type": type(error).__name__,
            "db_path": params.get("db_path", "data/output.db"),
            "total_statements": 0,
            "executed_statements": 0,
            "failed_statements": 0,
            "total_rows_in_table": 0
        }

