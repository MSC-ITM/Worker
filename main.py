# Worker/main.py
"""
Punto de entrada principal para el Worker Service.
Lee workflows directamente de la BD compartida con la API (database.db).
"""
import sys
import os
import argparse
import logging

# Agregar el directorio raíz al path para imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Worker.service.worker_service import WorkerService

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parsea argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        description='Worker Service - Ejecuta workflows desde BD compartida'
    )
    
    parser.add_argument(
        '--shared-db',
        default=os.getenv('SHARED_DB_PATH', 'database.db'),
        help='Ruta a la BD compartida con la API (default: database.db)'
    )
    
    parser.add_argument(
        '--worker-db',
        default=os.getenv('WORKER_DB_PATH', 'data/worker_workflows.db'),
        help='Ruta a la BD propia del worker (default: data/worker_workflows.db)'
    )
    
    parser.add_argument(
        '--poll-interval',
        type=float,
        default=float(os.getenv('POLL_INTERVAL', '10.0')),
        help='Intervalo de polling en segundos (default: 10.0)'
    )
    
    return parser.parse_args()


def main():
    """Función principal"""
    args = parse_args()
    
    # Banner
    print("=" * 70)
    print("  🤖 WORKER SERVICE - Workflow Execution Engine")
    print("=" * 70)
    print(f"  BD Compartida:  {args.shared_db}")
    print(f"  BD Worker:      {args.worker_db}")
    print(f"  Poll Interval:  {args.poll_interval}s")
    print("=" * 70)
    print()
    
    # Verificar que la BD compartida existe
    if not os.path.exists(args.shared_db):
        logger.error(f"❌ No se encontró la BD compartida: {args.shared_db}")
        logger.error("   Asegúrate de que la API esté corriendo y haya creado la BD")
        sys.exit(1)
    
    # Crear servicio
    try:
        service = WorkerService(
            shared_db_path=args.shared_db,
            poll_interval=args.poll_interval,
            worker_db_path=args.worker_db
        )
    except Exception as e:
        logger.error(f"❌ Error inicializando WorkerService: {e}")
        sys.exit(1)
    
    # Iniciar servicio
    logger.info("🚀 Iniciando Worker Service...")
    logger.info("   Presiona Ctrl+C para detener")
    print()
    
    try:
        service.start_blocking()
    except KeyboardInterrupt:
        logger.info("\n⏹️ Interrupción recibida")
    finally:
        service.stop()
        logger.info("👋 Worker Service terminado")
        
        # Mostrar estadísticas finales
        stats = service.get_stats()
        print()
        print("=" * 70)
        print("  📊 ESTADÍSTICAS FINALES")
        print("=" * 70)
        print(f"  Total procesados:  {stats['total_processed']}")
        print(f"  Exitosos:          {stats['successful']}")
        print(f"  Fallidos:          {stats['failed']}")
        print(f"  Iniciado:          {stats['started_at']}")
        print("=" * 70)


if __name__ == "__main__":
    main()