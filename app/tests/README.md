# 🧪 Tests de la Aplicación

## 📋 Descripción

Este directorio contiene todos los tests de la aplicación, organizados por funcionalidad y tipo. Los tests están diseñados para asegurar la calidad del código y facilitar el desarrollo individual.

## 🏗️ Estructura

```
tests/
├── api/
│   └── routes/           # Tests de endpoints de la API
│       ├── test_login.py
│       ├── test_users.py
│       ├── test_items.py
│       ├── test_slack_routes.py
│       └── test_private.py
├── crud/                 # Tests de operaciones CRUD
│   ├── test_user.py
│   └── test_slack_message.py
├── services/             # Tests de servicios
│   └── test_slack_service.py
├── utils/                # Utilidades para tests
│   ├── user.py
│   ├── item.py
│   └── utils.py
├── conftest.py           # Configuración de pytest
└── README.md             # Este archivo
```

## 🚀 Ejecución de Tests

### Instalar Dependencias
```bash
cd backend
uv sync
```

### Ejecutar Todos los Tests
```bash
pytest
```

### Ejecutar Tests con Coverage
```bash
pytest --cov=app --cov-report=html
```

### Ejecutar Tests Específicos
```bash
# Tests de Slack
pytest tests/api/routes/test_slack_routes.py

# Tests de servicios
pytest tests/services/test_slack_service.py

# Tests de CRUD
pytest tests/crud/test_slack_message.py

# Tests con marcadores específicos
pytest -m "not slow"
pytest -m integration
```

### Ejecutar Tests en Paralelo
```bash
pytest -n auto
```

## 📊 Cobertura de Tests

### Cobertura Mínima
- **Cobertura mínima requerida**: 80%
- **Cobertura actual**: Verificar con `pytest --cov=app --cov-report=term-missing`

### Generar Reporte HTML
```bash
pytest --cov=app --cov-report=html
# Abrir htmlcov/index.html en el navegador
```

## 🏷️ Marcadores de Tests

### Marcadores Disponibles
- `@pytest.mark.slow`: Tests que tardan más tiempo
- `@pytest.mark.integration`: Tests de integración
- `@pytest.mark.unit`: Tests unitarios
- `@pytest.mark.asyncio`: Tests asíncronos

### Ejecutar por Marcador
```bash
# Solo tests rápidos
pytest -m "not slow"

# Solo tests de integración
pytest -m integration

# Solo tests unitarios
pytest -m unit
```

## 🔧 Configuración

### Variables de Entorno para Tests
```bash
# Configuración de base de datos de test
POSTGRES_DB=ffx11_test_db

# Configuración de logging
LOG_LEVEL=WARNING

# Configuración de Slack (mocks)
SLACK_CLIENT_ID=test_client_id
SLACK_CLIENT_SECRET=test_client_secret

# Configuración de OpenAI (mocks)
OPENAI_API_KEY=test_api_key
```

### Configuración de pytest
- **Archivo**: `pytest.ini`
- **Cobertura mínima**: 80%
- **Modo asyncio**: Auto
- **Reportes**: HTML y terminal

## 📝 Tipos de Tests

### 1. Tests de Endpoints (`api/routes/`)
- **Propósito**: Probar endpoints de la API
- **Cobertura**: Todos los endpoints de Slack
- **Casos**: Éxito, error, validación, autenticación

### 2. Tests de Servicios (`services/`)
- **Propósito**: Probar lógica de negocio
- **Cobertura**: SlackService, SlackOAuthService, AIService
- **Casos**: Funcionalidad, errores, edge cases

### 3. Tests de CRUD (`crud/`)
- **Propósito**: Probar operaciones de base de datos
- **Cobertura**: Todas las operaciones CRUD
- **Casos**: Crear, leer, actualizar, eliminar, filtros

## 🎯 Tests de Slack

### Endpoints Cubiertos
- `GET /slack/test` - Prueba de conectividad
- `GET /slack/messages` - Obtener mensajes
- `POST /slack/events` - Webhook de eventos
- `GET /slack/oauth/callback` - Callback de OAuth

### Casos de Prueba
- **Autenticación**: Tokens válidos e inválidos
- **Validación**: Parámetros correctos e incorrectos
- **Eventos**: URL verification, message events
- **OAuth**: Flujo completo de autenticación
- **Errores**: Manejo de excepciones

### Mocks Utilizados
- **Slack API**: Simulación de respuestas de Slack
- **OpenAI API**: Simulación de análisis de IA
- **Base de datos**: Base de datos de test aislada

## 🔍 Debugging de Tests

### Verbosidad
```bash
# Tests muy verbosos
pytest -v -s

# Solo tests que fallan
pytest -x

# Continuar después de fallos
pytest --tb=short
```

### Logs de Tests
```bash
# Ver logs durante tests
pytest --log-cli-level=INFO

# Capturar logs en archivo
pytest --log-file=test.log
```

### Tests Específicos
```bash
# Test específico
pytest tests/api/routes/test_slack_routes.py::TestSlackRoutes::test_test_endpoint

# Tests que contienen palabra
pytest -k "slack"
```

## 📈 Métricas de Calidad

### Cobertura por Módulo
- **API Routes**: >90%
- **Services**: >85%
- **CRUD**: >95%
- **Models**: >80%

### Tiempo de Ejecución
- **Tests unitarios**: <30 segundos
- **Tests de integración**: <2 minutos
- **Tests completos**: <5 minutos

## 🚨 Troubleshooting

### Problemas Comunes

#### 1. Tests de Base de Datos
```bash
# Error: Base de datos no existe
createdb ffx11_test_db

# Error: Migraciones pendientes
alembic upgrade head
```

#### 2. Tests Asíncronos
```bash
# Error: Tests async no ejecutan
pip install pytest-asyncio

# Error: Event loop
pytest --asyncio-mode=auto
```

#### 3. Mocks No Funcionan
```bash
# Verificar que los mocks están correctos
pytest -v -s tests/api/routes/test_slack_routes.py::TestSlackRoutes::test_slack_events_url_verification
```

### Logs de Debug
```bash
# Ver logs detallados
pytest --log-cli-level=DEBUG

# Ver configuración de pytest
pytest --setup-show
```

## 🔄 CI/CD

### GitHub Actions
Los tests se ejecutan automáticamente en:
- **Push a main**: Tests completos
- **Pull Request**: Tests + coverage
- **Scheduled**: Tests de integración

### Pre-commit Hooks
```bash
# Instalar pre-commit
pre-commit install

# Ejecutar manualmente
pre-commit run --all-files
```

## 📚 Recursos Adicionales

### Documentación
- [pytest](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)

### Mejores Prácticas
- Usar fixtures para datos de prueba
- Mockear servicios externos
- Tests independientes y aislados
- Nombres descriptivos para tests
- Documentar casos complejos

---

*Última actualización: Enero 2024* 