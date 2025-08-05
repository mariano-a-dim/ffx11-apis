# Documentación Alembic

## Inicialización desde cero

### 1. Inicializar Alembic en el proyecto
```bash
alembic init migrations
```

### 2. Configurar la conexión a la base de datos
Editar `alembic.ini`:
```ini
sqlalchemy.url = postgresql://usuario:password@localhost:5432/nombre_db
```

O usar variables de entorno en `migrations/env.py` (recomendado):
```python
from app.core.config import settings

def get_url():
    return str(settings.SQLALCHEMY_DATABASE_URI)
```

### 3. Configurar los modelos
En `migrations/env.py`:
```python
from app.models import SQLModel
target_metadata = SQLModel.metadata
```

## Comandos principales

### Generar migración automática
```bash
alembic revision --autogenerate -m "Descripción de la migración"
```

### Aplicar migraciones
```bash
# Aplicar todas las migraciones pendientes
alembic upgrade head

# Aplicar hasta una migración específica
alembic upgrade <revision_id>

# Aplicar una migración hacia adelante
alembic upgrade +1
```

### Revertir migraciones
```bash
# Revertir una migración
alembic downgrade -1

# Revertir hasta una migración específica
alembic downgrade <revision_id>

# Revertir todas las migraciones
alembic downgrade base
```

### Ver estado de migraciones
```bash
# Ver historial de migraciones
alembic history

# Ver estado actual
alembic current

# Ver migraciones pendientes
alembic show <revision_id>
```

## Comandos de desarrollo

### Crear migración vacía
```bash
alembic revision -m "Migración manual"
```

### Editar migración existente
```bash
# Editar la última migración generada
nano migrations/versions/<revision_id>_description.py
```

### Marcar migración como aplicada (sin ejecutar)
```bash
alembic stamp head
```

## Solución de problemas comunes

### Error: "sqlmodel is not defined"
Agregar en el archivo de migración:
```python
import sqlmodel
```

### Error: "target_metadata is None"
Verificar que en `env.py` esté configurado:
```python
from app.models import SQLModel
target_metadata = SQLModel.metadata
```

### Error de conexión a base de datos
Verificar variables de entorno:
```bash
echo $POSTGRES_SERVER
echo $POSTGRES_PORT
echo $POSTGRES_USER
echo $POSTGRES_PASSWORD
echo $POSTGRES_DB
```

## Mejores prácticas

### 1. Nombres descriptivos
```bash
alembic revision --autogenerate -m "Add user table with email and password"
alembic revision --autogenerate -m "Add foreign key constraint to items table"
```

### 2. Revisar migraciones antes de aplicar
```bash
# Ver el SQL que se ejecutará
alembic upgrade head --sql
```

### 3. Backup antes de migraciones importantes
```bash
pg_dump -h localhost -U usuario -d nombre_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 4. Migraciones en producción
```bash
# Siempre hacer backup primero
# Usar --sql para revisar cambios
# Aplicar en horario de bajo tráfico
alembic upgrade head
```

## Estructura de archivos

```
migrations/
├── env.py                 # Configuración de Alembic
├── README                 # Documentación de migraciones
├── script.py.mako        # Template para nuevas migraciones
└── versions/             # Archivos de migración
    ├── c821ca541876_initial_migration.py
    └── ...
```

## Variables de entorno necesarias

```bash
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=usuario
POSTGRES_PASSWORD=password
POSTGRES_DB=nombre_db
```

## Comandos rápidos de referencia

| Comando | Descripción |
|---------|-------------|
| `alembic current` | Estado actual |
| `alembic history` | Historial completo |
| `alembic upgrade head` | Aplicar todas las migraciones |
| `alembic downgrade -1` | Revertir última migración |
| `alembic revision --autogenerate -m "msg"` | Generar migración automática |
| `alembic show head` | Ver última migración |
| `alembic stamp head` | Marcar como aplicada sin ejecutar | 