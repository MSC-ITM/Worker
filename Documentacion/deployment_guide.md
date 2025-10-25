# 🚀 Guía de Despliegue - Worker Engine

Guía completa para desplegar Worker Engine en diferentes entornos.

---

## 📋 Tabla de Contenidos

- [Requisitos Previos](#requisitos-previos)
- [Despliegue Local](#despliegue-local)
- [Despliegue con Docker](#despliegue-con-docker)
- [Despliegue en Producción](#despliegue-en-producción)
- [Variables de Entorno](#variables-de-entorno)
- [Monitoreo](#monitoreo)
- [Backup y Recuperación](#backup-y-recuperación)
- [Troubleshooting](#troubleshooting)

---

## ⚙️ Requisitos Previos

### Software Necesario

- Python 3.9 o superior
- pip 21.0 o superior
- SQLite 3.35 o superior (incluido en Python)
- Git

### Recursos Recomendados

| Entorno | CPU | RAM | Disco |
|---------|-----|-----|-------|
| Desarrollo | 2 cores | 2 GB | 10 GB |
| Staging | 2 cores | 4 GB | 20 GB |
| Producción | 4+ cores | 8+ GB | 50+ GB |

---

## 💻 Despliegue Local

### 1. Preparación del Entorno

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/worker-engine.git
cd worker-engine

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Actualizar pip
pip install --upgrade pip
```

### 2. Instalación de Dependencias

```bash
# Instalar dependencias
pip install -r requirements.txt

# Verificar instalación
python -c "import Worker; print('OK')"
```

### 3. Configuración

```bash
# Crear directorios necesarios
mkdir -p data logs workflows/examples

# Copiar configuración de ejemplo
cp config.example.py config.py

# Editar configuración (opcional)
nano config.py
```

### 4. Inicializar Base de Datos

```bash
# Ejecutar script de inicialización
python scripts/init_db.py

# Verificar creación
ls -lh data/workflows.db
```

### 5. Ejecutar Tests

```bash
# Ejecutar suite de tests
pytest Worker/Tests/ -v

# Con cobertura
pytest Worker/Tests/ --cov=Worker --cov-report=html

# Ver reporte
open htmlcov/index.html
```

### 6. Ejecución Local

```bash
# Ejecutar workflow de ejemplo
python examples/run_example_workflow.py

# O usar API (si está disponible)
uvicorn main:app --reload
```

---

## 🐳 Despliegue con Docker

### 1. Crear Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Metadata
LABEL maintainer="tu.email@ejemplo.com"
LABEL version="1.0.0"
LABEL description="Worker Engine - Sistema de Orquestación de Workflows"

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY Worker/ ./Worker/
COPY workflows/ ./workflows/
COPY config.py .

# Crear directorios de datos
RUN mkdir -p data logs

# Usuario no-root
RUN useradd -m -u 1000 worker && \
    chown -R worker:worker /app
USER worker

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from Worker.workflow.workflow_persistence import WorkflowRepository; WorkflowRepository()" || exit 1

# Volúmenes
VOLUME ["/app/data", "/app/logs"]

# Exponer puerto (si usas API)
EXPOSE 8000

# Comando por defecto
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Crear docker-compose.yml

```yaml
# docker-compose.yml
version: '3.8'

services:
  worker-engine:
    build: .
    container_name: worker-engine
    restart: unless-stopped
    
    ports:
      - "8000:8000"
    
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./workflows:/app/workflows
    
    environment:
      - DB_PATH=/app/data/workflows.db
      - LOG_LEVEL=INFO
      - MAX_WORKERS=5
      - TASK_TIMEOUT=3600
    
    networks:
      - worker-net
    
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  worker-net:
    driver: bridge

volumes:
  worker-data:
  worker-logs:
```

### 3. Construir y Ejecutar

```bash
# Construir imagen
docker build -t worker-engine:1.0.0 .

# Ejecutar con docker-compose
docker-compose up -d

# Ver logs
docker-compose logs -f

# Verificar estado
docker-compose ps

# Ejecutar tests dentro del container
docker-compose exec worker-engine pytest Worker/Tests/ -v
```

### 4. Comandos Útiles

```bash
# Detener servicios
docker-compose down

# Reiniciar servicios
docker-compose restart

# Ver logs en tiempo real
docker-compose logs -f worker-engine

# Acceder al container
docker-compose exec worker-engine bash

# Limpiar todo (incluyendo volúmenes)
docker-compose down -v
```

---

## 🏭 Despliegue en Producción

### 1. Preparación del Servidor

```bash
# Actualizar sistema (Ubuntu/Debian)
sudo apt-get update && sudo apt-get upgrade -y

# Instalar dependencias
sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    sqlite3 \
    nginx \
    supervisor

# Crear usuario para la aplicación
sudo useradd -m -s /bin/bash worker
sudo su - worker
```

### 2. Instalación de la Aplicación

```bash
# Como usuario worker
cd /home/worker

# Clonar repositorio
git clone https://github.com/tu-usuario/worker-engine.git
cd worker-engine

# Crear entorno virtual
python3.11 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
pip install gunicorn  # Para producción
```

### 3. Configuración de Nginx

```nginx
# /etc/nginx/sites-available/worker-engine
upstream worker_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name worker-engine.ejemplo.com;

    # Redirigir a HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name worker-engine.ejemplo.com;

    # Certificados SSL (Let's Encrypt recomendado)
    ssl_certificate /etc/letsencrypt/live/worker-engine.ejemplo.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/worker-engine.ejemplo.com/privkey.pem;

    # Configuración SSL
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Logs
    access_log /var/log/nginx/worker-engine.access.log;
    error_log /var/log/nginx/worker-engine.error.log;

    # Headers de seguridad
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy a la aplicación
    location / {
        proxy_pass http://worker_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Archivos estáticos (si aplica)
    location /static/ {
        alias /home/worker/worker-engine/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Límite de tamaño de archivos
    client_max_body_size 100M;
}
```

```bash
# Habilitar sitio
sudo ln -s /etc/nginx/sites-available/worker-engine /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 4. Configuración de Supervisor

```ini
# /etc/supervisor/conf.d/worker-engine.conf
[program:worker-engine]
command=/home/worker/worker-engine/venv/bin/gunicorn main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --timeout 60 \
    --access-logfile /home/worker/worker-engine/logs/access.log \
    --error-logfile /home/worker/worker-engine/logs/error.log \
    --log-level info

directory=/home/worker/worker-engine
user=worker
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true

# Variables de entorno
environment=
    PATH="/home/worker/worker-engine/venv/bin",
    DB_PATH="/home/worker/worker-engine/data/workflows.db",
    LOG_LEVEL="INFO"

# Logs
stdout_logfile=/home/worker/worker-engine/logs/supervisor.log
stderr_logfile=/home/worker/worker-engine/logs/supervisor.error.log

# Número de intentos de restart
startretries=3
```

```bash
# Aplicar configuración
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start worker-engine

# Ver estado
sudo supervisorctl status

# Ver logs
sudo supervisorctl tail -f worker-engine stdout
```

### 5. Configuración de Systemd (Alternativa)

```ini
# /etc/systemd/system/worker-engine.service
[Unit]
Description=Worker Engine - Sistema de Orquestación
After=network.target

[Service]
Type=notify
User=worker
Group=worker
WorkingDirectory=/home/worker/worker-engine

# Variables de entorno
Environment="PATH=/home/worker/worker-engine/venv/bin"
Environment="DB_PATH=/home/worker/worker-engine/data/workflows.db"
Environment="LOG_LEVEL=INFO"

# Comando
ExecStart=/home/worker/worker-engine/venv/bin/gunicorn main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --timeout 60

# Restart
Restart=always
RestartSec=10

# Logs
StandardOutput=append:/home/worker/worker-engine/logs/worker.log
StandardError=append:/home/worker/worker-engine/logs/worker.error.log

# Seguridad
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

```bash
# Habilitar y iniciar servicio
sudo systemctl daemon-reload
sudo systemctl enable worker-engine
sudo systemctl start worker-engine

# Ver estado
sudo systemctl status worker-engine

# Ver logs
sudo journalctl -u worker-engine -f
```

---

## 🔐 Variables de Entorno

### Archivo .env

```bash
# .env
# Configuración General
APP_NAME=WorkerEngine
APP_VERSION=1.0.0
ENVIRONMENT=production

# Base de Datos
DB_PATH=data/workflows.db
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/worker.log
LOG_MAX_SIZE=10485760  # 10MB
LOG_BACKUP_COUNT=5

# Ejecución
MAX_WORKERS=5
TASK_TIMEOUT=3600
MAX_RETRIES=3
RETRY_DELAY=60

# Seguridad
SECRET_KEY=tu-clave-secreta-super-segura
API_KEY=tu-api-key
ALLOWED_HOSTS=localhost,127.0.0.1,worker-engine.ejemplo.com

# Monitoreo
ENABLE_METRICS=true
METRICS_PORT=9090
SENTRY_DSN=https://...@sentry.io/...

# Notificaciones
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_FROM=noreply@ejemplo.com
```

### Cargar Variables en Python

```python
# config.py
import os
from dotenv import load_dotenv

# Cargar .env
load_dotenv()

class Config:
    # General
    APP_NAME = os.getenv("APP_NAME", "WorkerEngine")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    
    # Database
    DB_PATH = os.getenv("DB_PATH", "data/workflows.db")
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/worker.log")
    
    # Execution
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", "5"))
    TASK_TIMEOUT = int(os.getenv("TASK_TIMEOUT", "3600"))
    
    @classmethod
    def validate(cls):
        """Valida que todas las variables requeridas estén presentes"""
        required = ["DB_PATH", "SECRET_KEY"]
        missing = [var for var in required if not getattr(cls, var)]
        if missing:
            raise ValueError(f"Variables faltantes: {missing}")
```

---

## 📊 Monitoreo

### 1. Health Check Endpoint

```python
# main.py
from fastapi import FastAPI
from datetime import datetime

app = FastAPI()

@app.get("/health")
async def health_check():
    """Endpoint de health check"""
    try:
        # Verificar base de datos
        from Worker.workflow.workflow_persistence import WorkflowRepository
        repo = WorkflowRepository()
        
        # Test de conectividad
        from sqlmodel import Session, select
        from Worker.workflow.workflow_persistence import WorkflowRun
        with Session(repo.engine) as session:
            session.exec(select(WorkflowRun).limit(1))
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "checks": {
                "database": "ok",
                "tasks": "ok"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }, 503
```

### 2. Prometheus Metrics

```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Métricas
workflow_executions = Counter(
    'workflow_executions_total',
    'Total workflows executed',
    ['workflow_name', 'status']
)

task_duration = Histogram(
    'task_duration_seconds',
    'Task execution duration',
    ['task_type']
)

active_workflows = Gauge(
    'active_workflows',
    'Currently running workflows'
)

@app.get("/metrics")
async def metrics():
    """Endpoint de métricas para Prometheus"""
    return Response(
        generate_latest(),
        media_type="text/plain"
    )
```

### 3. Logging Estructurado

```python
# logging_config.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_obj)

# Configurar
handler = logging.FileHandler("logs/worker.json")
handler.setFormatter(JSONFormatter())
logging.getLogger().addHandler(handler)
```

---

## 💾 Backup y Recuperación

### Script de Backup

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/worker-engine"
DB_PATH="/home/worker/worker-engine/data/workflows.db"

# Crear directorio de backup
mkdir -p "$BACKUP_DIR"

# Backup de base de datos
sqlite3 "$DB_PATH" ".backup '$BACKUP_DIR/workflows_$DATE.db'"

# Comprimir
gzip "$BACKUP_DIR/workflows_$DATE.db"

# Limpiar backups antiguos (mantener 30 días)
find "$BACKUP_DIR" -name "workflows_*.db.gz" -mtime +30 -delete

echo "Backup completado: workflows_$DATE.db.gz"
```

### Automatizar con Cron

```bash
# Editar crontab
crontab -e

# Ejecutar backup diario a las 2AM
0 2 * * * /home/worker/worker-engine/scripts/backup.sh >> /home/worker/worker-engine/logs/backup.log 2>&1
```

### Restauración

```bash
#!/bin/bash
# restore.sh

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Uso: ./restore.sh /path/to/backup.db.gz"
    exit 1
fi

# Detener servicio
sudo systemctl stop worker-engine

# Descomprimir
gunzip -c "$BACKUP_FILE" > /tmp/workflows_restore.db

# Restaurar
mv /home/worker/worker-engine/data/workflows.db /home/worker/worker-engine/data/workflows.db.old
mv /tmp/workflows_restore.db /home/worker/worker-engine/data/workflows.db

# Reiniciar servicio
sudo systemctl start worker-engine

echo "Restauración completada"
```

---

## 🔧 Troubleshooting

### Problemas Comunes

#### 1. Error de Conexión a BD

```bash
# Verificar permisos
ls -l data/workflows.db
chmod 664 data/workflows.db

# Verificar integridad
sqlite3 data/workflows.db "PRAGMA integrity_check;"
```

#### 2. Worker no Inicia

```bash
# Ver logs
sudo journalctl -u worker-engine -n 100

# Verificar configuración
python -c "from config import Config; Config.validate()"

# Test manual
source venv/bin/activate
python main.py
```

#### 3. Alto Uso de Memoria

```bash
# Monitorear
htop

# Reducir workers
# En gunicorn: --workers 2
# En config: MAX_WORKERS=2
```

#### 4. Timeouts

```bash
# Aumentar timeout en nginx
# proxy_read_timeout 120s;

# Aumentar en gunicorn
# --timeout 120

# Aumentar en config
# TASK_TIMEOUT=7200
```

---

## 📞 Soporte

- **Documentación**: https://worker-engine.readthedocs.io
- **Issues**: https://github.com/tu-usuario/worker-engine/issues
- **Email**: soporte@ejemplo.com