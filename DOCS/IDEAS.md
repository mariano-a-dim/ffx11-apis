# Notas acerca de ideas

# Idea Grupo asistente

## Grupo funcionalidad

- En vez de un asistente para una persona, puedo crear un asistente imparcial para un grupo. Aunque lo de imparcial puede sonar un poco desafiante ya que la AI esta influenciada.
- Blockchain === sin intermediario -- Con un intermediario no humano... para algunas tareas..
- Este grupo podria ser una wallet compartida; es decir un fondo comun distribuido viviendo en la blockchain, el cual requiere aprobacion de los diferentes participantes. Si a esto le agregamos un asistente especifico para las operaciones de esa wallet; que tenga acceso a una base con todos los datos de operaciones previas y demas podria servir como una fuente de consulta.
- Dentro del contexto de slack podria ser el asistente de un canal; la mascota inteligente de un canal. Este caso de uso serviria para simular una persona adicional en un canal. Y ademas como un asistente inteligente para todos; que opine de lo que estamos hablando.
- Este ultimo caso se uso se relaciona mejor que el de blockchain, asi que lo voy a implementar antes.
- Quiero poder agegar diferentes bots al canal; uno que sea Arquitecto de Software; otro especialista en desarrollo nodejs otro en testing y solo opinan cuando se esta hablando de algun tema relacionado con su scope. Se puede configurar desde la APP de slack. Me suena que podria ser interesante la propuesta.
- Me gustaria que a nivel monetizacion el usuario pueda configurar el modelo que desee, ya sea uno free o pago.



## Casos de uso


4. Agrega los scopes necesarios:
   - `users:read`
   - `chat:write`


## Arquitectura drivers y restricciones

- El Sistema escala a millones de mensajes/ usuarios/ canales.
- El sistema responde rapido a las consultas directas
- El sistemas es serverless, aca hay una cuestion de costos clave, ya que no voy a pagar por el no uso
- El sistema esta orientado a eventos y es multi stack
- Inicialmente voy a usar tecnologia cloud no aws, no azure, no gcp; no auto-hosting



## Stack inicial

Arquitectura mínima en Railway (2 servicios + 2 add‑ons)
API (FastAPI)

Recibe /slack/events (webhook).

Valida firma, normaliza y persiste en Postgres (ACID).

Outbox pattern en la misma TX y publica a Redis Streams (events) para no bloquear.

Worker (Dramatiq/Arq/RQ, Python)

Consume events y ejecuta steps: embedding, topic, fragment, bot_decision, post_to_slack.

Es stateless; escala horizontal por concurrencia.

Add‑ons Railway

Postgres con pgvector (embeddings + HNSW), partición por workspace_id.

Redis (Upstash) para Streams, dedupe, rate‑limit y cache.

Opcional: Railway Cron pegando a un endpoint del Worker (snapshots/resúmenes).
Todo queda en Railway (una sola nube).