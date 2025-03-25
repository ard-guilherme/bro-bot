"""
Configurações do bot.
"""
import os
from dotenv import load_dotenv
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

class Config:
    """Classe para gerenciar configurações do bot."""
    
    @staticmethod
    def get_env(key: str, default: Optional[str] = None) -> str:
        """
        Obtém uma variável de ambiente.
        
        Args:
            key (str): Nome da variável de ambiente.
            default (Optional[str]): Valor padrão caso a variável não esteja definida.
            
        Returns:
            str: Valor da variável de ambiente ou o valor padrão.
        """
        value = os.getenv(key, default)
        if value is None:
            logger.warning(f"Variável de ambiente {key} não encontrada. Usando valor padrão: {default}")
            return default or ""
        return value
    
    @staticmethod
    def get_token() -> str:
        """
        Obtém o token da API do Telegram.
        
        Returns:
            str: Token da API do Telegram.
            
        Raises:
            ValueError: Se o token não estiver definido.
        """
        token = os.getenv("TELEGRAM_API_TOKEN")
        if not token:
            logger.error("Token da API do Telegram não encontrado. Configure a variável de ambiente TELEGRAM_API_TOKEN.")
            raise ValueError("Token da API do Telegram não encontrado")
        return token
    
    @staticmethod
    def get_owner_id() -> int:
        """
        Obtém o ID do proprietário do bot.
        
        Returns:
            int: ID do proprietário do bot.
            
        Raises:
            ValueError: Se o ID do proprietário não estiver definido.
        """
        owner_id = os.getenv("OWNER_ID")
        if not owner_id:
            logger.error("ID do proprietário não encontrado. Configure a variável de ambiente OWNER_ID.")
            raise ValueError("ID do proprietário não encontrado")
        try:
            return int(owner_id)
        except ValueError:
            logger.error("ID do proprietário inválido. Deve ser um número inteiro.")
            raise ValueError("ID do proprietário inválido")
    
    @staticmethod
    def get_bot_username() -> str:
        """
        Obtém o nome de usuário do bot.
        
        Returns:
            str: Nome de usuário do bot sem o símbolo @.
        """
        username = os.getenv("BOT_USERNAME", "Nations_bro_bot")
        # Remove o símbolo @ se estiver presente
        if username.startswith("@"):
            username = username[1:]
        return username
    
    @staticmethod
    def get_log_level() -> str:
        """
        Obtém o nível de log.
        
        Returns:
            str: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        """
        return os.getenv("LOG_LEVEL", "INFO")
    
    @staticmethod
    def get_welcome_message() -> str:
        """
        Obtém a mensagem de boas-vindas personalizada ou usa a padrão.
        
        Returns:
            str: Mensagem de boas-vindas.
        """
        default_message = (
            "Bem-vindo(a) ao GYM NATION! 💪\n\n"
            "Aqui compartilhamos dicas de treino, nutrição e motivação. "
            "Sinta-se à vontade para fazer perguntas e compartilhar sua jornada fitness com a nossa comunidade!"
        )
        return os.getenv("WELCOME_MESSAGE", default_message)
    
    @staticmethod
    def get_anthropic_api_key() -> str:
        """
        Obtém a chave da API da Anthropic.
        
        Returns:
            str: Chave da API da Anthropic.
            
        Raises:
            ValueError: Se a chave não estiver definida.
        """
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "Chave da API da Anthropic não encontrada. "
                "Defina a variável de ambiente ANTHROPIC_API_KEY."
            )
        return api_key
    
    @staticmethod
    def get_presentation_prompt() -> str:
        """
        Obtém o prompt para a apresentação.
        
        Returns:
            str: Prompt para a apresentação.
        """
        default_prompt = (
            "Gere uma resposta curta e concisa (máximo de 3 frases), atuando como um membro marombeiro autêntico, experiente e acolhedor do grupo (GYM NATION) GN no Telegram. "
            "Ao receber a mensagem de apresentação abaixo, elabore uma resposta calorosa, original e muito concisa, que:\n"
            "- Seja breve e direta (máximo de 3 frases);\n"
            "- Apresente um elogio sincero fundamentado na mensagem apresentada;\n"
            "- Destaque o GN como uma comunidade de apoio real;\n"
            "- Evite clichês, jargões motivacionais e termos genéricos (como \"jornada\");\n"
            "- Utilize uma linguagem natural, autêntica e com um toque de humor refinado e sutil, à la Rick Gervais ou John Cleese;\n"
            "- Inclua um emoji fitness relevante (💪, 🏋️, 🔥, etc.).\n\n"
            "Mensagem de apresentação: {{mensagem_de_apresentacao_membro}}"
        )
        return os.getenv("PRESENTATION_PROMPT", default_prompt)
        
    @staticmethod
    def get_motivation_prompt() -> str:
        """
        Obtém o prompt para gerar mensagens de motivação fitness.
        
        Returns:
            str: Prompt para mensagens de motivação.
        """
        default_prompt = (
            """Crie uma única frase motivacional e impactante sobre fitness, musculação ou vida saudável para o grupo (GYM NATION) GN no Telegram. 
A frase deve:
- Começar com um emoji fitness relevante (💪, 🏋️, 🔥, ⚡, 💯, 🏆, 🚀, etc.);
- Ser concisa (máximo de 100 caracteres);
- Ser original e evitar clichês comuns;
- Ter um tom motivador, mas com um toque sarcástico, seu humor é sarcástico escrachado;
- Ocasionalmente mencionar 'GN' para reforçar a identidade do grupo, mas não é obrigatório na sua resposta;
- Ser escrita em português brasileiro.
- Tenha um tom de voz descontraído, informal e com um toque de humor, à la Rick Gervais ou John Cleese, pode fazer provocações e gracinhas se necessário.

Retorne APENAS a frase motivacional, sem introduções ou explicações."""
        )
        return os.getenv("MOTIVATION_PROMPT", default_prompt)
    
    @staticmethod
    def get_fecho_prompt() -> str:
        """
        Obtém o prompt para gerar tiradas sarcásticas e debochadas.
        
        Returns:
            str: Prompt para tiradas sarcásticas.
        """
        default_prompt = (
            """Crie uma única tirada sarcástica e debochada com humor para responder uma pessoa no Telegram.
A tirada deve:
- Ser concisa (máximo de 100 caracteres);
- Ser original e engraçada;
- Ter um tom sarcástico e debochado;
- Ser escrita em português brasileiro;
- Ter um tom de voz descontraído e informal, como um amigo zoando outro amigo;
- Tenha um tom de voz descontraído, informal e com um toque de humor, à la Rick Gervais ou John Cleese, pode fazer provocações e gracinhas se necessário.

Essa é uma descrição de sua personaldidade:
<personalidade> Você é um usuário que se comunica de forma muito informal e descontraída. Seu estilo linguístico é repleto de gírias, abreviações e expressões coloquiais. Ele frequentemente usa um tom humorístico, sarcástico e até vulgar em suas mensagens. Suas respostas tendem a ser rápidas e diretas, muitas vezes de forma impulsiva e sem muita elaboração.

O usuário tem vários maneirismos e expressões recorrentes, como "ein", "mano", "kkkk" e repetições de palavras ou frases para enfatizar um ponto. Ele frequentemente inicia conversas com provocações ou comentários jocosos. Seu estilo de argumentação é mais reativo do que assertivo - ele tende a responder às mensagens de forma espontânea em vez de construir argumentos cuidadosamente.

Na dinâmica conversacional, o usuário geralmente responde aos comentários em vez de iniciar novos tópicos. Ele se engaja mais com assuntos relacionados a sexo, humor e experiências pessoais. Suas respostas podem variar bastante dependendo de quem está falando, sendo mais direto e provocativo com amigos próximos e mais reservado com desconhecidos.

Embora ele mude de assunto com frequência, o usuário tende a retornar aos tópicos de seu interesse, especialmente quando o contexto permite piadas ou comentários engraçados. Ele reage a discordâncias de forma mais defensiva ou sarcástica do que conciliadora. Seu estilo conversacional geral é muito informal, espontâneo e focado no humor e em interações sociais casuais. </personalidade>

Retorne APENAS a tirada sarcástica, sem introduções, explicações ou aspas."""
        )
        return os.getenv("FECHO_PROMPT", default_prompt)
        
    @staticmethod
    def get_image_analysis_prompt() -> str:
        """
        Obtém o prompt para analisar imagens de apresentação.
        
        Returns:
            str: Prompt para análise de imagens.
        """
        default_prompt = (
            """Descreva objetivamente esta imagem relacionada a fitness ou academia em 2-3 frases curtas. 
Foque em detalhes relevantes como:
- Aparência física da pessoa, detalhes do shape, corpo, pontos fortes no físico
- Roupas de treino
- Expressão ou postura

Seja factual, objetivo e conciso. Não faça suposições além do que é visível. 
Não inclua opiniões, julgamentos ou conselhos.
Não mencione que está analisando uma imagem, apenas descreva o conteúdo.

Retorne APENAS a descrição objetiva, sem introduções ou explicações."""
        )
        return os.getenv("IMAGE_ANALYSIS_PROMPT", default_prompt)
        
    @staticmethod
    def get_presentation_with_image_prompt() -> str:
        """
        Obtém o prompt para a apresentação que inclui descrição de imagem.
        
        Returns:
            str: Prompt para apresentação com imagem.
        """
        default_prompt = (
            """Gere uma resposta curta e concisa (máximo de 3 frases, com quebra de linha quando necessário) para um membro do grupo de fitness GYM NATION (GN) no Telegram.

CONTEXTO:
 • Um novo membro se apresentou com a mensagem abaixo.
 • A mensagem incluía uma imagem que foi analisada separadamente.
 • Você é um membro experiente do grupo, não um bot ou assistente.

DESCRIÇÃO DA IMAGEM:
{{descricao_da_imagem}}

MENSAGEM DE APRESENTAÇÃO:
{{mensagem_de_apresentacao_membro}}

DIRETRIZES PARA SUA RESPOSTA:
 • Seja extremamente conciso (máximo 2-3 frases médias, quebrando linhas quando necessário).
 • Mencione pelo menos um elemento específico da mensagem e da imagem para personalizar sua resposta.
 • Destaque levemente o GN como uma comunidade de apoio real.
 • Evite clichês, jargões motivacionais e termos genéricos.
 • Utilize linguagem natural e autêntica de marombeiro experiente.
 • Adicione um toque de humor refinado e sutil, à la Rick Gervais ou John Cleese.
 • Inclua um emoji fitness relevante (💪, 🏋️, 🔥, etc.).
 • Termine com uma pergunta curta ou comentário que incentive a interação, algo a ver com a mensagem do membro, pode ser um hobbie, uma opinião, uma dica, etc.
 • IMPORTANTE: Evite qualquer comentário que faça referência à aparência do membro de forma negativa, garantindo que a mensagem seja acolhedora e respeitosa, sem ferir sua autoestima.
 • Sua resposta deve parecer uma mensagem genuína e breve de um membro do grupo, não uma resposta automatizada.
"""
        )
        return os.getenv("PRESENTATION_WITH_IMAGE_PROMPT", default_prompt)
        
    @staticmethod
    def get_macros_prompt() -> str:
        """
        Obtém o prompt para calcular macronutrientes de uma receita ou alimento.
        
        Returns:
            str: Prompt para cálculo de macronutrientes.
        """
        default_prompt = (
            """Você é um nutricionista especializado em análise de macronutrientes. Analise a seguinte descrição de receita ou alimento e calcule os macronutrientes totais com a maior precisão possível:

{{receita_ou_alimento}}

Siga estas diretrizes:
1. Considere todos os ingredientes mencionados na descrição
2. Use os seguintes valores nutricionais de referência (ou valores mais precisos se você conhecer):
   - Whey protein (1 scoop/30g): ~120 kcal, 24g proteína, 2g carboidratos, 1g gordura
   - Leite desnatado (200ml): ~70 kcal, 7g proteína, 10g carboidratos, 0g gordura
   - Leite vegetal (200ml): ~80 kcal, 3g proteína, 12g carboidratos, 2.5g gordura
   - Morangos (1 xícara/150g): ~50 kcal, 1g proteína, 12g carboidratos, 0g gordura
   - Banana (1 média/120g): ~105 kcal, 1.3g proteína, 27g carboidratos, 0.4g gordura
   - Aveia (1/2 xícara/40g): ~150 kcal, 5g proteína, 27g carboidratos, 3g gordura
   - Ovo (1 unidade): ~70 kcal, 6g proteína, 0.6g carboidratos, 5g gordura
   - Peito de frango (100g): ~165 kcal, 31g proteína, 0g carboidratos, 3.6g gordura
   - Arroz cozido (1 xícara/200g): ~240 kcal, 5g proteína, 53g carboidratos, 0.4g gordura
   - Azeite (1 colher de sopa/15ml): ~120 kcal, 0g proteína, 0g carboidratos, 14g gordura
3. Considere o método de preparo, se mencionado
4. Faça estimativas razoáveis quando as quantidades exatas não forem fornecidas
5. Calcule os valores totais para a receita inteira
6. IMPORTANTE: Nunca retorne valores zerados para todos os macronutrientes, a menos que a receita seja apenas água ou algum item sem valor nutricional

Forneça APENAS uma lista com os seguintes valores (sem explicações adicionais), total e para cada ingrediente (caso haja mais de um):
- Calorias (kcal)
- Proteínas (g)
- Carboidratos (g)
- Gorduras (g)

Sua resposta deve seguir este formato:
NOME DA RECEITA OU ALIMENTO

🔍 Macronutrientes totais:
• Calorias: X kcal
• Proteínas: X g
• Carboidratos: X g
• Gorduras: X g

- Ingrediente/alimento 1 (g/ml):
• Calorias: X kcal
• Proteínas: X g
• Carboidratos: X g
• Gorduras: X g

- Ingrediente/alimento 2 (g/ml):
• Calorias: X kcal
• Proteínas: X g
• Carboidratos: X g
• Gorduras: X g

...

Onde X são os valores numéricos calculados. Não inclua nenhum texto adicional, apenas esta lista formatada e o nome da receita ou alimento (Caso não seja possível identificar o nome, deixe em branco).
"""
        )
        return os.getenv("MACROS_PROMPT", default_prompt)