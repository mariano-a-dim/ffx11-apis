# Configuración de Tiempos de Respuesta

Este documento describe las variables de configuración para los tiempos de delay de respuesta en el sistema de IA.

## Variables de Configuración

Agrega estas variables a tu archivo `.env`:

```env
# Response Delay Configuration (in seconds)
RESPONSE_DELAY_HIGH=30      # 30 segundos para alta urgencia
RESPONSE_DELAY_MEDIUM=120   # 2 minutos para urgencia media
RESPONSE_DELAY_LOW=300      # 5 minutos para baja urgencia
RESPONSE_DELAY_LOCO=5       # 5 segundos para palabra "loco"
RESPONSE_DELAY_TEST=30      # 30 segundos para pruebas
```

## Descripción de los Delays

### `RESPONSE_DELAY_HIGH`
- **Valor por defecto**: 30 segundos
- **Uso**: Mensajes con urgencia alta
- **Descripción**: Respuesta inmediata para situaciones críticas

### `RESPONSE_DELAY_MEDIUM`
- **Valor por defecto**: 120 segundos (2 minutos)
- **Uso**: Mensajes con urgencia media
- **Descripción**: Respuesta rápida para situaciones importantes pero no críticas

### `RESPONSE_DELAY_LOW`
- **Valor por defecto**: 300 segundos (5 minutos)
- **Uso**: Mensajes con urgencia baja
- **Descripción**: Respuesta normal para consultas generales

### `RESPONSE_DELAY_LOCO`
- **Valor por defecto**: 5 segundos
- **Uso**: Mensajes que contienen la palabra "loco"
- **Descripción**: Respuesta de prueba muy rápida para testing

### `RESPONSE_DELAY_TEST`
- **Valor por defecto**: 30 segundos
- **Uso**: Endpoint de prueba `/test-scheduler`
- **Descripción**: Delay para respuestas de prueba del sistema

## Cómo Funciona

1. **Análisis de Urgencia**: El sistema analiza cada mensaje y determina su nivel de urgencia (high/medium/low)
2. **Selección de Delay**: Según la urgencia, se selecciona el delay correspondiente de la configuración
3. **Programación**: Se programa una tarea asíncrona para enviar la respuesta después del delay
4. **Envío**: La respuesta se envía automáticamente a Slack después del tiempo configurado

## Ejemplos de Uso

### Para Desarrollo/Testing
```env
RESPONSE_DELAY_HIGH=10      # 10 segundos
RESPONSE_DELAY_MEDIUM=30    # 30 segundos
RESPONSE_DELAY_LOW=60       # 1 minuto
RESPONSE_DELAY_LOCO=3       # 3 segundos
RESPONSE_DELAY_TEST=10      # 10 segundos
```

### Para Producción
```env
RESPONSE_DELAY_HIGH=30      # 30 segundos
RESPONSE_DELAY_MEDIUM=120   # 2 minutos
RESPONSE_DELAY_LOW=300      # 5 minutos
RESPONSE_DELAY_LOCO=5       # 5 segundos
RESPONSE_DELAY_TEST=30      # 30 segundos
```

## Notas Importantes

- Todos los tiempos están en **segundos**
- Los cambios en el `.env` requieren reiniciar el servidor
- El sistema usa `asyncio.sleep()` para los delays
- Las tareas se ejecutan de forma asíncrona sin bloquear el servidor 