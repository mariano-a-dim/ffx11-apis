# AI Service - Arquitectura Refactorizada

## 🏗️ **Estructura General**

El servicio de IA ha sido completamente refactorizado para mejorar la claridad, mantenibilidad y separación de responsabilidades.

### 📁 **Clases Principales**

#### 1. **`ConversationState` (TypedDict)**
- Define el estado del flujo de conversación con LangGraph
- Contiene todos los datos necesarios para el procesamiento
- Tipado fuerte para mejor IDE support

#### 2. **`PromptBuilder`**
- **Responsabilidad**: Construir prompts para diferentes tareas de IA
- **Métodos**:
  - `build_urgency_evaluation_prompt()` - Evaluación de urgencia
  - `build_message_analysis_prompt()` - Análisis de mensajes
  - `build_sensitivity_check_prompt()` - Verificación de sensibilidad
  - `build_response_generation_prompt()` - Generación de respuestas

#### 3. **`ContextManager`**
- **Responsabilidad**: Gestionar el contexto de conversación
- **Métodos**:
  - `get_channel_context()` - Obtener contexto del canal
  - `get_user_responses_for_style()` - Obtener ejemplos de estilo
  - `format_messages_for_prompt()` - Formatear mensajes para prompts

#### 4. **`ResponseGenerator`**
- **Responsabilidad**: Generar respuestas específicas
- **Métodos**:
  - `generate_test_response()` - Respuesta para palabra "loco"
  - `generate_evasion_response()` - Respuestas de evasión

#### 5. **`AIService` (Clase Principal)**
- **Responsabilidad**: Orquestar todo el flujo de IA
- **Componentes**:
  - Inicialización del LLM
  - Creación del workflow de LangGraph
  - Nodos del workflow
  - Condiciones de flujo
  - Métodos auxiliares

## 🔄 **Flujo de LangGraph**

### **Nodos del Workflow**

1. **`get_channel_context`** → Obtiene contexto del canal
2. **`get_user_responses`** → Obtiene ejemplos de estilo del usuario
3. **`evaluate_urgency`** → Evalúa urgencia del mensaje
4. **`analyze_message`** → Determina si debe responder
5. **`check_sensitivity`** → Verifica situaciones sensibles
6. **`generate_response`** → Genera la respuesta final

### **Condiciones de Flujo**

- **`_should_respond_condition`**: Decide si continuar a sensibilidad o terminar
- **`_sensitivity_condition`**: Decide si generar respuesta o terminar

### **Flujo Visual**

```
get_channel_context → get_user_responses → evaluate_urgency → analyze_message
                                                                    ↓
                                                              should_respond?
                                                                    ↓
                                                              check_sensitivity
                                                                    ↓
                                                              is_safe?
                                                                    ↓
                                                              generate_response
```

## 🎯 **Características de la Refactorización**

### ✅ **Separación de Responsabilidades**
- Cada clase tiene una responsabilidad específica
- Prompts separados en `PromptBuilder`
- Contexto gestionado por `ContextManager`
- Respuestas específicas en `ResponseGenerator`

### ✅ **Mantenibilidad**
- Código más legible y organizado
- Métodos pequeños y enfocados
- Fácil de extender y modificar
- Documentación clara

### ✅ **Robustez**
- Manejo de errores mejorado
- Fallbacks para cada componente
- Logging detallado
- Validación de respuestas JSON

### ✅ **Flexibilidad**
- Fácil agregar nuevos tipos de prompts
- Configuración centralizada
- Parámetros configurables
- Extensible para nuevas funcionalidades

## 🔧 **Uso del Servicio**

### **Análisis de Mensaje**
```python
ai_service = AIService(session)
analysis = ai_service.analyze_message(message, context)
should_respond = ai_service.should_respond(analysis)
```

### **Generación de Respuesta**
```python
response = ai_service.get_response(message, context)
```

## 📝 **Logs y Debugging**

### **Logs Principales**
- `🚀 Starting AI workflow analysis`
- `🚨 Starting urgency evaluation`
- `🔍 Starting message analysis`
- `🔍 Checking conversation sensitivity`
- `💬 Starting response generation`

### **Logs de Decisión**
- `🤔 Should respond decision`
- `🚫 Conversation marked as sensitive`
- `✅ Conversation safe to respond`

### **Logs de Respuesta**
- `🎯 Generating test response for 'loco' keyword`
- `🚫 Generating evasion response for sensitive situation`
- `✅ Response generated based on context and user style`

## 🚀 **Beneficios de la Refactorización**

1. **Código más limpio**: Separación clara de responsabilidades
2. **Fácil mantenimiento**: Cada componente es independiente
3. **Mejor testing**: Cada clase puede ser testeada por separado
4. **Extensibilidad**: Fácil agregar nuevas funcionalidades
5. **Debugging mejorado**: Logs específicos para cada paso
6. **Reutilización**: Componentes pueden ser reutilizados
7. **Documentación**: Código autodocumentado

## 🔮 **Futuras Mejoras**

- Agregar tests unitarios para cada clase
- Implementar cache de prompts
- Agregar métricas de performance
- Configuración dinámica de prompts
- Soporte para múltiples modelos de IA 