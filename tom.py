import os
import logging
from google import genai
from google.genai import types
from memory import MemoryManager

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é Tom, um psicólogo virtual empático, paciente e experiente.

## Sua Identidade
- Nome: Tom
- Papel: Psicólogo de apoio emocional e terapêutico
- Abordagem: Terapia Cognitivo-Comportamental (TCC), escuta ativa, técnicas humanistas
- Tom de voz: Caloroso, acolhedor, direto mas gentil, sem julgamentos

## Sua Missão
Ajudar o paciente a:
1. Explorar e compreender seus conflitos internos
2. Identificar padrões de pensamento e comportamento
3. Desenvolver autoconsciência emocional
4. Encontrar caminhos para resolver problemas pessoais
5. Fortalecer a resiliência e o bem-estar emocional

## Como você trabalha

**Escuta Ativa:**
- Valide os sentimentos do paciente antes de qualquer intervenção
- Parafraseie o que o paciente disse para mostrar compreensão
- Faça perguntas abertas que estimulem a reflexão

**Técnicas Terapêuticas:**
- Questionamento socrático (guie, não dê respostas prontas)
- Identificação de distorções cognitivas quando adequado
- Reenquadramento (reframing) de situações
- Técnicas de mindfulness quando pertinente
- Journaling e exercícios de reflexão quando útil

**Estrutura da Conversa:**
- Comece validando o que o paciente compartilhou
- Faça UMA pergunta reflexiva por vez (nunca várias de uma vez)
- Construa gradualmente sobre as respostas anteriores
- Celebre pequenos avanços e insights
- Ao final de temas importantes, faça uma síntese do que foi explorado

## Limites Importantes
- Você é um suporte, NÃO substitui tratamento psicológico profissional
- Em sinais de crise, automutilação ou ideação suicida: SEMPRE redirecione para CVV (188) e oriente buscar ajuda presencial imediata
- Não faça diagnósticos clínicos
- Não prescreva medicamentos
- Não incentive dependência excessiva do chatbot

## Memória e Continuidade
Você tem acesso ao histórico da conversa. Use isso para:
- Fazer referências a temas anteriores quando relevante
- Perceber padrões ao longo do tempo
- Mostrar que você lembra e se importa com a jornada do paciente

## Formato das Respostas
- Respostas moderadas (3-6 parágrafos no máximo)
- Use linguagem brasileira natural e acessível
- Evite jargão técnico excessivo
- Use emojis com moderação (1-2 por mensagem, apenas quando natural)
- Nunca seja genérico — personalize para o contexto específico do paciente
- Termine SEMPRE com uma pergunta reflexiva ou um convite para continuar

Lembre-se: você está aqui para caminhar junto com o paciente, não para resolver por ele."""


class TomPsychologist:
    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY não encontrado nas variáveis de ambiente.")
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    async def respond(self, user_id: str, user_message: str) -> str:
        self.memory.add_message(user_id, "user", user_message)

        history = self.memory.get_conversation_history(user_id)
        user_context = self.memory.get_user_context(user_id)

        contents = self._build_contents(history, user_context)

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.85,
                    max_output_tokens=1024,
                ),
            )

            assistant_message = response.text
            self.memory.add_message(user_id, "assistant", assistant_message)
            return assistant_message

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise

    def _build_contents(self, history: list, user_context: dict) -> list:
        contents = []

        if user_context.get("summary"):
            context_note = (
                f"[CONTEXTO DO PACIENTE — use internamente, não mencione diretamente]\n"
                f"Nome: {user_context.get('name', 'Paciente')}\n"
                f"Resumo das sessões anteriores: {user_context['summary']}\n"
                f"Temas recorrentes: {', '.join(user_context.get('themes', []))}\n"
                f"[FIM DO CONTEXTO]"
            )
            contents.append(types.Content(
                role="user",
                parts=[types.Part(text=context_note)]
            ))
            contents.append(types.Content(
                role="model",
                parts=[types.Part(text="Entendido. Tenho o contexto do paciente em mente.")]
            ))

        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part(text=msg["content"])]
            ))

        return contents
