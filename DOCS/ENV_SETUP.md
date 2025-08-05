# Configuración de Variables de Entorno

Este documento describe todas las variables de entorno necesarias para ejecutar la aplicación.

## Archivo `.env`

Crea un archivo `.env` en el directorio raíz del proyecto con las siguientes variables:

```env
# =============================================================================
# CONFIGURACIÓN DE BASE DE DATOS
# =============================================================================
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=ffx11_api

# =============================================================================
# CONFIGURACIÓN DEL PROYECTO
# =============================================================================
PROJECT_NAME=FFX11 API
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=admin123

# =============================================================================
# CONFIGURACIÓN DE SLACK
# =============================================================================
SLACK_CLIENT_ID=your_slack_client_id
SLACK_CLIENT_SECRET=your_slack_client_secret
SLACK_PERSONAL_TOKEN=xoxp-your-personal-token

# =============================================================================
# CONFIGURACIÓN DE OPENAI
# =============================================================================
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-4o

# =============================================================================
# CONFIGURACIÓN DEL ASISTENTE DE IA
# =============================================================================
AI_PRINCIPAL_USER_ID=U036PD91RR6
AI_PRINCIPAL_USER_NAME=Madim
AI_COMPANY_NAME=Gojiraf
AI_PRINCIPAL_ROLE=CTO

# =============================================================================
# CONFIGURACIÓN DE TIEMPOS DE RESPUESTA (en segundos)
# =============================================================================
RESPONSE_DELAY_HIGH=30      # 30 segundos para alta urgencia
RESPONSE_DELAY_MEDIUM=120   # 2 minutos para urgencia media
RESPONSE_DELAY_LOW=300      # 5 minutos para baja urgencia
RESPONSE_DELAY_LOCO=5       # 5 segundos para palabra "loco"
RESPONSE_DELAY_TEST=30      # 30 segundos para pruebas
```

## Descripción de Variables

### Base de Datos
- **POSTGRES_SERVER**: Servidor de PostgreSQL
- **POSTGRES_PORT**: Puerto de PostgreSQL (por defecto 5432)
- **POSTGRES_USER**: Usuario de la base de datos
- **POSTGRES_PASSWORD**: Contraseña de la base de datos
- **POSTGRES_DB**: Nombre de la base de datos

### Proyecto
- **PROJECT_NAME**: Nombre del proyecto
- **FIRST_SUPERUSER**: Email del primer superusuario
- **FIRST_SUPERUSER_PASSWORD**: Contraseña del primer superusuario

### Slack
- **SLACK_CLIENT_ID**: ID de la aplicación de Slack
- **SLACK_CLIENT_SECRET**: Secret de la aplicación de Slack
- **SLACK_PERSONAL_TOKEN**: Token personal de Slack (xoxp-...)

### OpenAI
- **OPENAI_API_KEY**: Clave de API de OpenAI
- **OPENAI_MODEL**: Modelo de OpenAI a usar (gpt-4o, gpt-4o-mini, etc.)

### Asistente de IA
- **AI_PRINCIPAL_USER_ID**: ID de Slack del usuario principal (Madim)
- **AI_PRINCIPAL_USER_NAME**: Nombre del usuario principal
- **AI_COMPANY_NAME**: Nombre de la empresa
- **AI_PRINCIPAL_ROLE**: Rol del usuario principal

### Tiempos de Respuesta
- **RESPONSE_DELAY_HIGH**: Delay para mensajes de alta urgencia
- **RESPONSE_DELAY_MEDIUM**: Delay para mensajes de urgencia media
- **RESPONSE_DELAY_LOW**: Delay para mensajes de baja urgencia
- **RESPONSE_DELAY_LOCO**: Delay para mensajes con palabra "loco"
- **RESPONSE_DELAY_TEST**: Delay para respuestas de prueba

## Configuración para Diferentes Entornos

### Desarrollo
```env
RESPONSE_DELAY_HIGH=10      # 10 segundos
RESPONSE_DELAY_MEDIUM=30    # 30 segundos
RESPONSE_DELAY_LOW=60       # 1 minuto
RESPONSE_DELAY_LOCO=3       # 3 segundos
RESPONSE_DELAY_TEST=10      # 10 segundos
```

### Producción
```env
RESPONSE_DELAY_HIGH=30      # 30 segundos
RESPONSE_DELAY_MEDIUM=120   # 2 minutos
RESPONSE_DELAY_LOW=300      # 5 minutos
RESPONSE_DELAY_LOCO=5       # 5 segundos
RESPONSE_DELAY_TEST=30      # 30 segundos
```

## Obtención de Tokens

### Slack Personal Token
1. Ve a https://api.slack.com/apps
2. Crea una nueva app o selecciona una existente
3. Ve a "OAuth & Permissions"
4. Agrega los scopes necesarios:
   - `users:read`
   - `chat:write`
   - `channels:read`
   - `groups:read`
   - `im:read`
   - `mpim:read`
5. Instala la app en tu workspace
6. Copia el "Bot User OAuth Token" (xoxb-) o "User OAuth Token" (xoxp-)

### OpenAI API Key
1. Ve a https://platform.openai.com/api-keys
2. Crea una nueva API key
3. Copia la clave (comienza con `sk-`)

## Notas Importantes

- **Nunca commits el archivo `.env`** al repositorio
- **Mantén los tokens seguros** y no los compartas
- **Los cambios en `.env` requieren reiniciar el servidor**
- **Para desarrollo**, puedes usar valores más bajos en los delays
- **Para producción**, usa valores más altos para evitar spam

## Verificación

Para verificar que las variables están configuradas correctamente:

```bash
# Verificar configuración de Slack
curl http://localhost:8000/api/slack/test-token

# Verificar configuración de delays
curl http://localhost:8000/api/slack/response-times

# Verificar procesamiento de menciones
curl http://localhost:8000/api/slack/test-mentions
``` 