from typing import Dict, Any, Optional, List, TypedDict
from sqlmodel import Session
import json
import random

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from app.core.config import settings
from app.models import SlackMessage
from app.crud.slack_message import get_slack_messages
from app.core.logging import LoggerMixin


class ConversationState(TypedDict):
    """Estado del flujo de conversación con LangGraph"""
    message: Dict[str, Any]
    channel_context: List[SlackMessage]
    user_responses: List[SlackMessage]
    urgency_analysis: Optional[Dict[str, Any]]
    analysis: Optional[Dict[str, Any]]
    sensitivity_check: Optional[Dict[str, Any]]
    should_respond: bool
    response: Optional[str]
    reasoning: str


class PromptBuilder:
    """Clase responsable de construir prompts para diferentes tareas de IA"""
    
    @staticmethod
    def build_urgency_evaluation_prompt(message: Dict[str, Any], context_text: str) -> tuple[str, str]:
        """Construye el prompt para evaluación de urgencia"""
        system_prompt = """
        Eres un experto en evaluación de urgencia de mensajes de Slack. Tu tarea es analizar la urgencia de un mensaje basándote en múltiples factores, NO solo en palabras clave como "urgente" o "importante".
        
        Factores a considerar:
        1. **Impacto del negocio**: ¿Afecta operaciones críticas, clientes, o ingresos?
        2. **Tiempo de respuesta requerido**: ¿Necesita respuesta inmediata, en horas, o puede esperar días?
        3. **Dependencias**: ¿Bloquea trabajo de otros o procesos críticos?
        4. **Contexto del canal**: ¿Es un canal de producción, desarrollo, o general?
        5. **Tipo de solicitud**: ¿Es un bug crítico, feature request, o consulta general?
        6. **Rol del remitente**: ¿Viene de alguien con responsabilidades críticas?
        
        Niveles de urgencia:
        - **high**: Requiere atención inmediata (< 1 hora), afecta operaciones críticas
        - **medium**: Requiere atención en las próximas horas, afecta trabajo pero no crítico
        - **low**: Puede esperar, consulta general o no crítica
        
        Responde con JSON válido:
        {
            "urgency_level": "low/medium/high",
            "urgency_score": 0.0-1.0,
            "urgency_factors": ["factor1", "factor2", ...],
            "reasoning": "explicación detallada"
        }
        """
        
        human_prompt = f"""
        Evalúa la urgencia de este mensaje:
        
        Canal: {message.get('channel', 'unknown')}
        Usuario: {message.get('user', 'unknown')}
        Mensaje: {message.get('text', '')}
        
        Contexto del canal:
        {context_text}
        
        Considera todos los factores mencionados, no solo palabras clave.
        """
        
        return system_prompt, human_prompt
    
    @staticmethod
    def build_message_analysis_prompt(message: Dict[str, Any], context_text: str, urgency_info: str) -> tuple[str, str]:
        """Construye el prompt para análisis de mensajes"""
        system_prompt = f"""
        Eres un asistente que analiza mensajes de Slack para determinar si {settings.AI_PRINCIPAL_USER_NAME} ({settings.AI_PRINCIPAL_ROLE} de {settings.AI_COMPANY_NAME}) debe responder.
        
        Reglas importantes:
        1. Responde SI el mensaje:
           - Te arroba directamente (@madim, @marian)
           - Te menciona por nombre (Mariano, Marian) aunque no te arroben
           - Te involucra de alguna forma en la conversación
           - Es URGENTE y requiere atención inmediata (problemas críticos, bugs, servidores caídos, etc.)
           - Es IMPORTANTE para el negocio y {settings.AI_PRINCIPAL_USER_NAME} debería estar al tanto
        2. Considera el contexto de la conversación
        3. Usa la evaluación de urgencia previa para tomar decisiones
        4. Si es urgente pero no ofensivo, DEBES responder
        
        Responde con JSON válido:
        {{
            "is_direct": true/false,
            "urgency": "low/medium/high", 
            "requires_response": true/false,
            "reasoning": "explicación"
        }}
        """
        
        human_prompt = f"""
        Analiza este mensaje:
        
        Canal: {message.get('channel', 'unknown')}
        Usuario: {message.get('user', 'unknown')}
        Mensaje: {message.get('text', '')}
        
        Contexto del canal:
        {context_text}
        
        {urgency_info}
        
        **IMPORTANTE**: Busca menciones de {settings.AI_PRINCIPAL_USER_NAME} en cualquier forma:
        - Arrobas: @madim, @marian
        - Nombres: Mariano, Marian
        - Referencias indirectas que te involucren
        
        ¿Requiere respuesta de {settings.AI_PRINCIPAL_USER_NAME}?
        """
        
        return system_prompt, human_prompt
    
    @staticmethod
    def build_sensitivity_check_prompt(message: Dict[str, Any], context_text: str) -> tuple[str, str]:
        """Construye el prompt para verificación de sensibilidad"""
        system_prompt = f"""
        Eres un experto en análisis de sensibilidad de conversaciones. Tu tarea es detectar situaciones donde {settings.AI_PRINCIPAL_USER_NAME} debería EVITAR responder para no meterse en conflictos o situaciones delicadas.
        
        Situaciones sensibles a detectar:
        1. **Conflictos entre personas**: Discusiones, desacuerdos, tensiones
        2. **Molestias o frustraciones**: Personas expresando enojo, frustración, molestia
        3. **Críticas o quejas**: Comentarios negativos sobre trabajo, personas o procesos
        4. **Situaciones personales**: Problemas personales, dramas, situaciones delicadas
        5. **Política o temas controversiales**: Discusiones políticas, religiosas, sociales
        6. **Tensiones laborales**: Conflictos de trabajo, jefes vs empleados, etc.
        7. **Sentimientos contradictorios**: Personas con emociones encontradas
        8. **Ofensas o insultos**: Lenguaje ofensivo o irrespetuoso
        
        Niveles de sensibilidad:
        - **high**: Situación muy delicada, definitivamente evitar respuesta
        - **medium**: Situación moderadamente sensible, considerar evitar
        - **low**: Situación normal, se puede responder con seguridad
        
        Responde con JSON válido:
        {{
            "is_sensitive": true/false,
            "sensitivity_level": "low/medium/high",
            "sensitivity_factors": ["factor1", "factor2", ...],
            "reasoning": "explicación detallada"
        }}
        """
        
        human_prompt = f"""
        Analiza la sensibilidad de esta conversación:
        
        Canal: {message.get('channel', 'unknown')}
        Usuario: {message.get('user', 'unknown')}
        Mensaje actual: {message.get('text', '')}
        
        Contexto del canal:
        {context_text}
        
        ¿Es seguro que {settings.AI_PRINCIPAL_USER_NAME} responda o hay situaciones sensibles que debería evitar?
        """
        
        return system_prompt, human_prompt
    
    @staticmethod
    def build_response_generation_prompt(message: Dict[str, Any], context_text: str, 
                                       responses_text: str, urgency_info: str) -> tuple[str, str]:
        """Construye el prompt para generación de respuestas"""
        system_prompt = f"""
        Eres {settings.AI_PRINCIPAL_USER_NAME}, el {settings.AI_PRINCIPAL_ROLE} de {settings.AI_COMPANY_NAME}. 
        
        **OBJETIVO CRÍTICO**: Debes responder EXACTAMENTE como lo haría {settings.AI_PRINCIPAL_USER_NAME} en persona. La gente NO debe detectar que es una IA. Debes parecer completamente humano.

        **ESTILO DE COMUNICACIÓN**:
        - Usa el mismo tono, vocabulario y estilo que {settings.AI_PRINCIPAL_USER_NAME} usa en sus respuestas previas
        - Sé directo, conciso y natural
        - Evita lenguaje formal o de asistente
        - Usa emojis y expresiones como lo haría {settings.AI_PRINCIPAL_USER_NAME}
        - Mantén la personalidad y forma de expresarse de {settings.AI_PRINCIPAL_USER_NAME}

        **CONTEXTO IMPORTANTE**:
        - Los mensajes del canal son la conversación actual
        - Las respuestas previas son EJEMPLOS de tu estilo de comunicación (no son parte de la conversación actual)
        - Usa esos ejemplos para imitar exactamente cómo respondes

        **AJUSTE POR URGENCIA**:
        - Alta urgencia: Respuesta inmediata, directa, prioritaria
        - Media urgencia: Respuesta balanceada, profesional pero cercana  
        - Baja urgencia: Respuesta casual, relajada

        **REGLAS ESTRICTAS**:
        - NO uses frases como "como asistente", "puedo ayudarte", "estoy aquí para"
        - NO parezcas un bot o IA
        - Responde como si fueras {settings.AI_PRINCIPAL_USER_NAME} escribiendo en persona
        - Mantén consistencia con tu estilo de comunicación previo
        """
        
        human_prompt = f"""
        **MENSAJE ACTUAL A RESPONDER:**
        {message.get('text', '')}
        
        **CONTEXTO DE LA CONVERSACIÓN ACTUAL (últimos mensajes del canal):**
        {context_text}
        
        {urgency_info}
        
        **EJEMPLOS DE TU ESTILO DE COMUNICACIÓN (respuestas previas tuyas):**
        {responses_text}
        
        **INSTRUCCIÓN**: Responde al mensaje actual usando tu estilo de comunicación natural, basándote en los ejemplos anteriores. La respuesta debe parecer que la escribiste tú en persona, no un asistente.
        """
        
        return system_prompt, human_prompt


class ContextManager:
    """Clase responsable de gestionar el contexto de conversación"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_channel_context(self, channel_id: str, current_msg_id: str, limit: int = 10) -> List[SlackMessage]:
        """Obtiene el contexto del canal (últimos mensajes)"""
        try:
            context_messages = get_slack_messages(
                session=self.session,
                channel_id=channel_id,
                limit=limit
            )
            
            # Filtrar para excluir el mensaje actual
            context_messages = [
                msg for msg in context_messages 
                if msg.slack_message_id != current_msg_id
            ]
            
            return context_messages
            
        except Exception as e:
            return []
    
    def get_user_responses_for_style(self, principal_user_id: str = None, limit: int = 30) -> List[SlackMessage]:
        """Obtiene respuestas previas del usuario para usar como ejemplos de estilo"""
        try:
            if principal_user_id:
                user_responses = get_slack_messages(
                    session=self.session,
                    user_id=principal_user_id,
                    limit=limit
                )
            else:
                # Fallback: obtener todos los mensajes
                user_responses = get_slack_messages(
                    session=self.session,
                    limit=50
                )
            
            # Filtrar mensajes que son buenos ejemplos de estilo
            filtered_responses = []
            for msg in user_responses:
                text = msg.text.lower()
                if (len(text) > 5 and 
                    not text.startswith(('?', '¿')) and
                    not text.startswith(('!', '/', 'http'))):
                    filtered_responses.append(msg)
            
            # Tomar los últimos ejemplos más representativos
            return filtered_responses[-10:] if filtered_responses else []
            
        except Exception as e:
            return []
    
    def format_messages_for_prompt(self, messages: List[SlackMessage], is_user_responses: bool = False) -> str:
        """Formatea mensajes para usar en prompts"""
        if not messages:
            return "No hay mensajes previos."
        
        formatted = []
        for msg in messages[-5:]:  # Últimos 5 mensajes
            user = msg.user_name or msg.user_id
            timestamp = msg.timestamp[:10] if msg.timestamp else "unknown"
            
            if is_user_responses:
                # Para respuestas previas del usuario, enfatizar que son ejemplos de estilo
                formatted.append(f"📝 Ejemplo de tu estilo ({timestamp}): {msg.text}")
            else:
                # Para contexto del canal, mostrar conversación normal
                formatted.append(f"[{user}]: {msg.text}")
        
        return "\n".join(formatted)


class ResponseGenerator:
    """Clase responsable de generar respuestas específicas"""
    
    @staticmethod
    def generate_test_response() -> str:
        """Genera respuesta de prueba para palabra 'loco'"""
        return "¡Hola! 🎯 Detecté la palabra 'loco' en tu mensaje. Esta es una respuesta de prueba del sistema automático. El sistema está funcionando correctamente y puede detectar palabras clave y responder automáticamente."
    
    @staticmethod
    def generate_evasion_response() -> str:
        """Genera respuesta de evasión para situaciones sensibles"""
        evasion_responses = [
            "Después lo hablamos 👍",
            "Lo reviso más tarde",
            "Ahora no puedo, después hablamos",
            "Lo veo después",
            "Más tarde lo charlamos",
            "Después lo vemos",
            "Ahora estoy ocupado, después hablamos",
            "Lo reviso cuando pueda",
            "Después lo conversamos",
            "Más tarde lo tratamos"
        ]
        return random.choice(evasion_responses)


class AIService(LoggerMixin):
    """Servicio principal de IA con flujo de LangGraph refactorizado"""
    
    def __init__(self, session: Session):
        self.session = session
        self.context_manager = ContextManager(session)
        self.prompt_builder = PromptBuilder()
        self.response_generator = ResponseGenerator()
        
        # Inicializar LLM
        if not settings.OPENAI_API_KEY:
            self.logger.warning("OPENAI_API_KEY not configured, AI features will be disabled")
            self.llm = None
        else:
            self.llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                temperature=0.7,
                openai_api_key=settings.OPENAI_API_KEY
            )
            self.logger.info("AI service initialized", model=settings.OPENAI_MODEL)
        
        # Crear el grafo de LangGraph
        self.workflow = self._create_workflow()
    
    def _create_workflow(self) -> StateGraph:
        """Crea el flujo de trabajo con LangGraph"""
        workflow = StateGraph(ConversationState)
        
        # Agregar nodos
        workflow.add_node("get_channel_context", self._get_channel_context)
        workflow.add_node("get_user_responses", self._get_user_responses)
        workflow.add_node("evaluate_urgency", self._evaluate_urgency)
        workflow.add_node("analyze_message", self._analyze_message)
        workflow.add_node("check_sensitivity", self._check_sensitivity)
        workflow.add_node("generate_response", self._generate_response)
        
        # Definir el flujo
        workflow.set_entry_point("get_channel_context")
        workflow.add_edge("get_channel_context", "get_user_responses")
        workflow.add_edge("get_user_responses", "evaluate_urgency")
        workflow.add_edge("evaluate_urgency", "analyze_message")
        workflow.add_conditional_edges(
            "analyze_message",
            self._should_respond_condition,
            {
                "respond": "check_sensitivity",
                "respond_direct": "generate_response",
                "skip": END
            }
        )
        workflow.add_conditional_edges(
            "check_sensitivity",
            self._sensitivity_condition,
            {
                "safe": "generate_response",
                "sensitive": END
            }
        )
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    # Nodos del workflow
    def _get_channel_context(self, state: ConversationState) -> ConversationState:
        """Obtiene el contexto del canal"""
        try:
            message = state["message"]
            channel_id = message.get("channel", "unknown")
            current_msg_id = message.get("client_msg_id") or message.get("ts")
            
            context_messages = self.context_manager.get_channel_context(channel_id, current_msg_id)
            
            self.logger.info("Channel context retrieved", 
                           channel_id=channel_id,
                           context_count=len(context_messages))
            
            return {**state, "channel_context": context_messages}
            
        except Exception as e:
            self.logger.error("Error getting channel context", error=str(e))
            return {**state, "channel_context": []}
    
    def _get_user_responses(self, state: ConversationState) -> ConversationState:
        """Obtiene las respuestas previas del usuario principal"""
        try:
            principal_user_id = settings.AI_PRINCIPAL_USER_ID
            user_responses = self.context_manager.get_user_responses_for_style(principal_user_id)
            
            self.logger.info("User responses retrieved for style examples", 
                           response_count=len(user_responses),
                           principal_user_id=principal_user_id)
            
            return {**state, "user_responses": user_responses}
            
        except Exception as e:
            self.logger.error("Error getting user responses", error=str(e))
            return {**state, "user_responses": []}
    
    def _evaluate_urgency(self, state: ConversationState) -> ConversationState:
        """Evalúa la urgencia del mensaje"""
        self.logger.info("🚨 Starting urgency evaluation")
        
        if not self.llm:
            return self._get_default_urgency_analysis(state)
        
        try:
            message = state["message"]
            channel_context = state["channel_context"]
            
            context_text = self.context_manager.format_messages_for_prompt(channel_context, is_user_responses=False)
            system_prompt, human_prompt = self.prompt_builder.build_urgency_evaluation_prompt(message, context_text)
            
            urgency_analysis = self._call_llm_with_json_parsing(system_prompt, human_prompt, "urgency analysis")
            return {**state, "urgency_analysis": urgency_analysis}
            
        except Exception as e:
            self.logger.error("Error evaluating urgency", error=str(e))
            return self._get_default_urgency_analysis(state)
    
    def _analyze_message(self, state: ConversationState) -> ConversationState:
        """Analiza el mensaje para determinar si requiere respuesta"""
        self.logger.info("🔍 Starting message analysis")
        
        # Detectar palabra "loco" para prueba - DEBE RESPONDER SIEMPRE
        message = state["message"]
        message_text = message.get('text', '').lower()
        if "loco" in message_text:
            self.logger.info("🎯 Detected 'loco' keyword - bypassing all analysis")
            return {
                **state,
                "analysis": {
                    "is_direct": True,
                    "urgency": "high",
                    "requires_response": True,
                    "reasoning": "Mensaje contiene la palabra 'loco' - respuesta de prueba activada"
                },
                "should_respond": True,
                "reasoning": "Palabra de prueba 'loco' detectada - respuesta obligatoria"
            }
        
        if not self.llm:
            return self._get_default_message_analysis(state)
        
        try:
            channel_context = state["channel_context"]
            urgency_analysis = state.get("urgency_analysis", {})
            
            context_text = self.context_manager.format_messages_for_prompt(channel_context, is_user_responses=False)
            urgency_info = self._format_urgency_info(urgency_analysis)
            
            system_prompt, human_prompt = self.prompt_builder.build_message_analysis_prompt(message, context_text, urgency_info)
            
            analysis = self._call_llm_with_json_parsing(system_prompt, human_prompt, "message analysis")
            return {**state, "analysis": analysis}
            
        except Exception as e:
            self.logger.error("Error analyzing message", error=str(e))
            return self._get_default_message_analysis(state)
    
    def _check_sensitivity(self, state: ConversationState) -> ConversationState:
        """Verifica si el contexto contiene situaciones sensibles"""
        self.logger.info("🔍 Checking conversation sensitivity")
        
        if not self.llm:
            return self._get_default_sensitivity_check(state)
        
        try:
            message = state["message"]
            channel_context = state["channel_context"]
            
            context_text = self.context_manager.format_messages_for_prompt(channel_context, is_user_responses=False)
            system_prompt, human_prompt = self.prompt_builder.build_sensitivity_check_prompt(message, context_text)
            
            sensitivity_check = self._call_llm_with_json_parsing(system_prompt, human_prompt, "sensitivity check")
            return {**state, "sensitivity_check": sensitivity_check}
            
        except Exception as e:
            self.logger.error("Error checking sensitivity", error=str(e))
            return self._get_default_sensitivity_check(state)
    
    def _generate_response(self, state: ConversationState) -> ConversationState:
        """Genera una respuesta basada en el contexto"""
        self.logger.info("💬 Starting response generation")
        
        # Verificar respuestas específicas primero
        message = state["message"]
        sensitivity_check = state.get("sensitivity_check", {})
        
        # Respuesta específica para palabra "loco"
        message_text = message.get('text', '').lower()
        if "loco" in message_text:
            return self._handle_loco_response(state)
        
        # Respuesta de evasión para situaciones sensibles
        if sensitivity_check.get("is_sensitive", False) and sensitivity_check.get("sensitivity_level") in ["medium", "high"]:
            return self._handle_sensitive_situation(state, sensitivity_check)
        
        # Generar respuesta normal con IA
        if not self.llm:
            return {**state, "response": None, "reasoning": "AI not configured"}
        
        try:
            channel_context = state["channel_context"]
            user_responses = state["user_responses"]
            urgency_analysis = state.get("urgency_analysis", {})
            
            context_text = self.context_manager.format_messages_for_prompt(channel_context, is_user_responses=False)
            responses_text = self.context_manager.format_messages_for_prompt(user_responses, is_user_responses=True)
            urgency_info = self._format_urgency_info(urgency_analysis)
            
            system_prompt, human_prompt = self.prompt_builder.build_response_generation_prompt(
                message, context_text, responses_text, urgency_info
            )
            
            response = self.llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)])
            
            return {
                **state, 
                "response": response.content,
                "reasoning": "Response generated based on context and user style"
            }
            
        except Exception as e:
            self.logger.error("Error generating response", error=str(e))
            return {**state, "response": None, "reasoning": f"Error: {str(e)}"}
    
    # Condiciones del workflow
    def _should_respond_condition(self, state: ConversationState) -> str:
        """Determina si debe generar respuesta"""
        analysis = state.get("analysis", {})
        message = state.get("message", {})
        message_text = message.get('text', '').lower()
        
        # Si contiene "loco", ir directamente a generar respuesta (saltar sensibilidad)
        if "loco" in message_text:
            self.logger.info("🎯 'loco' detected - going directly to response generation")
            return "respond_direct"
        
        # Si es directo y requiere respuesta, responder
        # Si es urgente (medium o high) y requiere respuesta, responder
        urgency = analysis.get("urgency", "low")
        is_direct = analysis.get("is_direct", False)
        requires_response = analysis.get("requires_response", False)
        
        should_respond = (
            (is_direct and requires_response) or
            (urgency in ["medium", "high"] and requires_response)
        )
        
        self.logger.info("🤔 Should respond decision", 
                       is_direct=is_direct,
                       requires_response=requires_response,
                       urgency=urgency,
                       decision="respond" if should_respond else "skip",
                       reasoning=f"Direct: {is_direct}, Urgent: {urgency}, Requires: {requires_response}")
        
        return "respond" if should_respond else "skip"
    
    def _sensitivity_condition(self, state: ConversationState) -> str:
        """Determina si es seguro responder basado en el análisis de sensibilidad"""
        sensitivity_check = state.get("sensitivity_check", {})
        is_sensitive = sensitivity_check.get("is_sensitive", False)
        sensitivity_level = sensitivity_check.get("sensitivity_level", "low")
        
        if is_sensitive and sensitivity_level in ["medium", "high"]:
            self.logger.info("🚫 Conversation marked as sensitive, avoiding response", 
                           sensitivity_level=sensitivity_level,
                           factors=sensitivity_check.get("sensitivity_factors", []))
            return "sensitive"
        
        self.logger.info("✅ Conversation safe to respond", 
                        sensitivity_level=sensitivity_level)
        return "safe"
    
    # Métodos auxiliares
    def _call_llm_with_json_parsing(self, system_prompt: str, human_prompt: str, task_name: str) -> Dict[str, Any]:
        """Llama al LLM y parsea la respuesta JSON"""
        try:
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]
            response = self.llm.invoke(messages)
            
            content = response.content
            start = content.find('{')
            end = content.rfind('}') + 1
            
            if start != -1 and end != 0:
                json_str = content[start:end]
                result = json.loads(json_str)
                return result
            else:
                raise ValueError("No JSON found")
                
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.warning(f"Failed to parse {task_name}", error=str(e))
            return self._get_default_json_response(task_name)
    
    def _format_urgency_info(self, urgency_analysis: Dict[str, Any]) -> str:
        """Formatea información de urgencia para incluir en prompts"""
        if not urgency_analysis:
            return ""
        
        return f"""
        Análisis de urgencia:
        - Nivel: {urgency_analysis.get('urgency_level', 'unknown')}
        - Score: {urgency_analysis.get('urgency_score', 0)}
        - Factores: {', '.join(urgency_analysis.get('urgency_factors', []))}
        - Razón: {urgency_analysis.get('reasoning', 'N/A')}
        """
    

    
    def _handle_loco_response(self, state: ConversationState) -> ConversationState:
        """Genera respuesta específica para palabra 'loco'"""
        test_response = self.response_generator.generate_test_response()
        self.logger.info("🎯 Generating test response for 'loco' keyword", 
                       response=test_response)
        return {
            **state, 
            "response": test_response,
            "reasoning": "Test response generated for 'loco' keyword"
        }
    
    def _handle_sensitive_situation(self, state: ConversationState, sensitivity_check: Dict[str, Any]) -> ConversationState:
        """Genera respuesta de evasión para situaciones sensibles"""
        evasion_response = self.response_generator.generate_evasion_response()
        self.logger.info("🚫 Generating evasion response for sensitive situation", 
                       sensitivity_level=sensitivity_check.get("sensitivity_level"),
                       factors=sensitivity_check.get("sensitivity_factors", []),
                       response=evasion_response)
        return {
            **state, 
            "response": evasion_response,
            "reasoning": f"Evasion response for sensitive situation: {sensitivity_check.get('reasoning', 'N/A')}"
        }
    
    # Métodos de fallback
    def _get_default_urgency_analysis(self, state: ConversationState) -> ConversationState:
        """Retorna análisis de urgencia por defecto"""
        return {**state, "urgency_analysis": {
            "urgency_level": "low",
            "urgency_score": 0.1,
            "urgency_factors": ["AI not configured"],
            "reasoning": "AI not configured"
        }}
    
    def _get_default_message_analysis(self, state: ConversationState) -> ConversationState:
        """Retorna análisis de mensaje por defecto"""
        return {**state, "analysis": {
            "is_direct": False,
            "urgency": "low",
            "requires_response": False,
            "reasoning": "AI not configured"
        }}
    
    def _get_default_sensitivity_check(self, state: ConversationState) -> ConversationState:
        """Retorna verificación de sensibilidad por defecto"""
        return {**state, "sensitivity_check": {
            "is_sensitive": False,
            "sensitivity_level": "low",
            "sensitivity_factors": ["AI not configured"],
            "reasoning": "AI not configured"
        }}
    
    def _get_default_json_response(self, task_name: str) -> Dict[str, Any]:
        """Retorna respuesta JSON por defecto según la tarea"""
        defaults = {
            "urgency analysis": {
                "urgency_level": "low",
                "urgency_score": 0.1,
                "urgency_factors": ["Parse error"],
                "reasoning": "Parse error"
            },
            "message analysis": {
                "is_direct": False,
                "urgency": "low",
                "requires_response": False,
                "reasoning": "Parse error"
            },
            "sensitivity check": {
                "is_sensitive": False,
                "sensitivity_level": "low",
                "sensitivity_factors": ["Parse error"],
                "reasoning": "Parse error"
            }
        }
        return defaults.get(task_name, {"error": "Unknown task"})
    
    # Métodos públicos
    def analyze_message(self, message: Dict[str, Any], conversation_context: list[SlackMessage] = None) -> Dict[str, Any]:
        """Analiza un mensaje usando el flujo de LangGraph"""
        self.logger.info("🚀 Starting AI workflow analysis")
        
        try:
            initial_state = self._create_initial_state(message, conversation_context)
            config = self._create_workflow_config(message)
            
            self.logger.info("🔄 Invoking LangGraph workflow")
            result = self.workflow.invoke(initial_state, config=config)
            self.logger.info("✅ LangGraph workflow completed")
            
            analysis = result.get("analysis", {})
            self.logger.info("Message analysis completed", 
                           analysis=analysis,
                           should_respond=result.get("should_respond"),
                           has_response=bool(result.get("response")))
            
            return analysis
            
        except Exception as e:
            self.logger.error("Error in message analysis workflow", error=str(e))
            return {
                "is_direct": False,
                "urgency": "low",
                "requires_response": False,
                "reasoning": f"Workflow error: {str(e)}"
            }
    
    def should_respond(self, analysis: Dict[str, Any]) -> bool:
        """Determina si debe responder basado en el análisis de IA"""
        return (
            analysis.get("is_direct", False) and 
            analysis.get("requires_response", False)
        )
    
    def get_response(self, message: Dict[str, Any], conversation_context: list[SlackMessage] = None) -> Optional[str]:
        """Obtiene una respuesta generada para un mensaje"""
        try:
            initial_state = self._create_initial_state(message, conversation_context)
            config = self._create_workflow_config(message)
            
            result = self.workflow.invoke(initial_state, config=config)
            return result.get("response")
            
        except Exception as e:
            self.logger.error("Error getting response", error=str(e))
            return None
    
    def _create_initial_state(self, message: Dict[str, Any], conversation_context: list[SlackMessage] = None) -> ConversationState:
        """Crea el estado inicial para el workflow"""
        return {
            "message": message,
            "channel_context": conversation_context or [],
            "user_responses": [],
            "urgency_analysis": None,
            "analysis": None,
            "sensitivity_check": None,
            "should_respond": False,
            "response": None,
            "reasoning": ""
        }
    
    def _create_workflow_config(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Crea la configuración para el workflow"""
        return {
            "configurable": {
                "thread_id": f"slack_{message.get('channel', 'unknown')}_{message.get('ts', 'unknown')}",
                "checkpoint_id": f"msg_{message.get('client_msg_id', message.get('ts', 'unknown'))}"
            }
        } 