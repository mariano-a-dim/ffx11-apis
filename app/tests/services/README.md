# Tests de Servicios

Este directorio contiene los tests para los servicios principales de la aplicación.

## Estructura

```
services/
├── __init__.py
├── README.md
├── test_slack_user_service.py      # Tests para el servicio de usuarios de Slack
├── test_slack_response_scheduler.py # Tests para el scheduler de respuestas
└── test_ai_service.py              # Tests para el servicio de IA
```

## Ejecutar Tests

### Ejecutar todos los tests de servicios
```bash
# Desde el directorio raíz del proyecto
pytest app/tests/services/ -v
```

### Ejecutar tests específicos
```bash
# Tests de usuarios de Slack
pytest app/tests/services/test_slack_user_service.py -v

# Tests del scheduler
pytest app/tests/services/test_slack_response_scheduler.py -v

# Tests de IA
pytest app/tests/services/test_ai_service.py -v
```

### Ejecutar tests manualmente (para debugging)
```bash
# Tests de usuarios de Slack
python app/tests/services/test_slack_user_service.py

# Tests del scheduler
python app/tests/services/test_slack_response_scheduler.py

# Tests de IA
python app/tests/services/test_ai_service.py
```

## Tests Disponibles

### `test_slack_user_service.py`
- **`test_user_mentions_processing`**: Prueba el procesamiento de menciones de usuario
- **`test_regex_patterns`**: Prueba los patrones regex para extraer menciones

### `test_slack_response_scheduler.py`
- **`test_scheduled_responses`**: Prueba el sistema de respuestas programadas
- **`test_urgency_response_times`**: Prueba la obtención de tiempos por urgencia
- **`test_test_response_scheduling`**: Prueba el scheduling de respuestas de prueba
- **`test_loco_response_scheduling`**: Prueba el scheduling de respuestas para "loco"

### `test_ai_service.py`
- **`test_ai_workflow`**: Prueba el flujo completo de IA
- **`test_loco_keyword_detection`**: Prueba la detección de la palabra "loco"
- **`test_sensitivity_detection`**: Prueba la detección de situaciones sensibles

## Configuración Requerida

Para ejecutar los tests, asegúrate de tener configurado:

1. **Variables de entorno** en `.env`:
   ```env
   SLACK_PERSONAL_TOKEN=xoxp-your-token
   OPENAI_API_KEY=sk-your-key
   RESPONSE_DELAY_HIGH=30
   RESPONSE_DELAY_MEDIUM=120
   RESPONSE_DELAY_LOW=300
   RESPONSE_DELAY_LOCO=5
   RESPONSE_DELAY_TEST=30
   ```

2. **Base de datos** configurada y accesible

3. **Dependencias** instaladas:
   ```bash
   pip install pytest pytest-asyncio
   ```

## Notas Importantes

- Los tests usan **fixtures de pytest** para manejar sesiones de base de datos
- Algunos tests hacen llamadas a **APIs externas** (Slack, OpenAI) - asegúrate de tener tokens válidos
- Los tests pueden ejecutarse en **modo manual** para debugging usando `python archivo.py`
- Los tests están diseñados para ser **independientes** y no afectar el estado de la aplicación 