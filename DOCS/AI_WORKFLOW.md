# Flujo de IA con LangGraph

## Descripción

Este sistema implementa un flujo de IA sofisticado usando LangGraph y LangChain para procesar mensajes de Slack y generar respuestas automáticas cuando el usuario principal (Madim) es mencionado.

## Arquitectura

### Flujo de Trabajo (LangGraph)

El flujo se compone de 5 nodos principales:

1. **`get_channel_context`**: Obtiene los últimos 10 mensajes del canal para contexto
2. **`get_user_responses`**: Obtiene las últimas 20 respuestas del usuario principal
3. **`evaluate_urgency`**: Evalúa la urgencia del mensaje basándose en múltiples factores
4. **`analyze_message`**: Analiza si el mensaje requiere respuesta usando la evaluación de urgencia
5. **`generate_response`**: Genera una respuesta apropiada considerando la urgencia

### Estado del Flujo

```python
class ConversationState(TypedDict):
    message: Dict[str, Any]           # Mensaje original de Slack
    channel_context: List[SlackMessage]  # Contexto del canal
    user_responses: List[SlackMessage]    # Respuestas previas del usuario
    urgency_analysis: Optional[Dict[str, Any]]  # Análisis de urgencia
    analysis: Optional[Dict[str, Any]]    # Resultado del análisis
    should_respond: bool                   # Si debe responder
    response: Optional[str]               # Respuesta generada
    reasoning: str                        # Razón de la decisión
```

## Configuración

### Variables de Entorno

```bash
# OpenAI
OPENAI_API_KEY=tu_api_key_aqui
OPENAI_MODEL=gpt-4o-mini

# Configuración del Asistente
AI_PRINCIPAL_USER_ID=U123456789  # ID de Slack del usuario principal
AI_PRINCIPAL_USER_NAME=Madim      # Nombre del usuario principal
AI_COMPANY_NAME=Gojiraf           # Nombre de la empresa
AI_PRINCIPAL_ROLE=CTO             # Rol del usuario principal
```

## Uso

### Análisis de Mensaje

```python
from app.services.ai_service import AIService

# Crear servicio
ai_service = AIService(session)

# Analizar mensaje
analysis = ai_service.analyze_message(message, conversation_context)

# Verificar si debe responder
if ai_service.should_respond(analysis):
    response = ai_service.get_response(message, conversation_context)
```

### Integración con Slack

El servicio de Slack (`SlackService`) ya está integrado con el nuevo flujo:

```python
# En process_message_event
analysis = self.ai_service.analyze_message(event, conversation_context)

if self.ai_service.should_respond(analysis):
    response = self.ai_service.get_response(event, conversation_context)
    # TODO: Enviar respuesta a Slack
```

## Características

### Análisis Inteligente

- Detecta menciones directas (`@madim`)
- Identifica preguntas directas al usuario principal
- **Evalúa urgencia basándose en múltiples factores**:
  - Impacto del negocio
  - Tiempo de respuesta requerido
  - Dependencias y bloqueos
  - Contexto del canal
  - Tipo de solicitud
  - Rol del remitente
- Considera contexto de la conversación

### Generación de Respuestas

- Basada en respuestas previas del usuario
- Mantiene estilo y tono personal
- **Ajusta respuesta según urgencia**:
  - Alta urgencia: Respuesta inmediata, directa, prioritaria
  - Media urgencia: Respuesta en las próximas horas, balanceada
  - Baja urgencia: Respuesta casual, puede esperar
- Considera contexto de la conversación
- Respuestas profesionales pero cercanas

### Persistencia

- Usa `MemorySaver` de LangGraph para checkpointing
- Mantiene estado entre ejecuciones
- Permite debugging y monitoreo

## Pruebas

### Script de Prueba

```bash
cd backend
python test_ai_workflow.py
```

Este script prueba diferentes tipos de mensajes:
- Menciones directas
- Preguntas generales
- Mensajes que requieren aprobación
- Conversaciones casuales

### Logs

El sistema genera logs detallados para:
- Análisis de mensajes
- Generación de respuestas
- Errores y excepciones
- Métricas de rendimiento

## Mejoras Futuras

1. **Identificación de Usuario**: Mejorar la detección de mensajes del usuario principal
2. **Respuestas Contextuales**: Usar más contexto histórico
3. **Aprendizaje**: Implementar feedback loop para mejorar respuestas
4. **Integración Slack**: Completar el envío automático de respuestas
5. **Métricas**: Agregar dashboard de métricas de uso

## Dependencias

- `langchain>=0.3.27`
- `langchain-openai>=0.3.28`
- `langgraph>=0.5.4`
- `openai` (via langchain-openai)

## Notas de Implementación

- El flujo es asíncrono y escalable
- Usa checkpoints para persistencia
- Maneja errores gracefully
- Es configurable via variables de entorno
- Sigue principios de clean architecture 