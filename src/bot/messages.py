"""
Mensagens utilizadas pelo bot.
"""
import random
from typing import Optional
from src.utils.config import Config
from src.bot.motivation import get_random_motivation
from src.utils.anthropic_client import AnthropicClient
import asyncio
import logging

logger = logging.getLogger(__name__)

class Messages:
    """Classe para gerenciar mensagens do bot."""
    
    # Lista de emojis positivos para reações
    POSITIVE_REACTION_EMOJIS = [
        "❤", "🔥", "👏", "🎉", "🤩", "🥰"
    ]
    
    @staticmethod
    def get_welcome_message(user_name: str) -> str:
        """
        Obtém a mensagem de boas-vindas personalizada com o nome do usuário.
        
        Args:
            user_name (str): Nome do usuário que entrou no grupo.
            
        Returns:
            str: Mensagem de boas-vindas personalizada.
        """
        base_message = Config.get_welcome_message()
        
        # Adiciona o nome do usuário à mensagem
        personalized_message = f"Olá, {user_name}! {base_message}"
        
        return personalized_message
    
    @staticmethod
    def get_random_motivation_message() -> str:
        """
        Obtém uma mensagem de motivação fitness aleatória da lista fixa.
        
        Returns:
            str: Mensagem de motivação.
        """
        return get_random_motivation()
    
    @staticmethod
    def get_start_message() -> str:
        """
        Obtém a mensagem de início do bot.
        
        Returns:
            str: Mensagem de início.
        """
        return (
            "🏋️‍♂️ *Bem-vindo ao GYM NATION Bot!* 🏋️‍♀️\n\n"
            "Sou seu assistente virtual para ajudar com sua jornada fitness.\n\n"
            "Use /help para ver todos os comandos disponíveis."
        )
    
    @staticmethod
    def get_help_message() -> str:
        """
        Obtém a mensagem de ajuda com os comandos disponíveis.
        
        Returns:
            str: Mensagem de ajuda.
        """
        return (
            "🤖 *Comandos do GYM NATION Bot* 🤖\n\n"
            "• /start - Inicia o bot\n"
            "• /help - Mostra esta mensagem de ajuda\n"
            "• /motivacao - Receba uma mensagem motivacional\n"
            "• /apresentacao - Gera uma apresentação personalizada\n"
            "• /checkin - Inicia um check-in (apenas admins)\n"
            "• /endcheckin - Encerra um check-in ativo (apenas admins)\n"
            "• /checkinscore - Mostra o placar de check-ins\n"
            "• /confirmcheckin - Confirma check-in de um usuário (apenas admins)\n"
            "• /macros - Calcula macronutrientes de um alimento\n"
            "• /monitor - Inicia monitoramento de mensagens (apenas dono do bot)\n"
            "• /unmonitor - Encerra monitoramento de mensagens (apenas dono do bot)\n"
        )
    
    @staticmethod
    async def get_motivation_message_async(user_name: Optional[str] = None, message_content: Optional[str] = None) -> str:
        """
        Obtém uma mensagem de motivação fitness gerada pela API da Anthropic,
        opcionalmente personalizada para um usuário específico e considerando o
        conteúdo da mensagem à qual está respondendo.
        
        Args:
            user_name (Optional[str]): Nome do usuário para personalizar a mensagem.
            message_content (Optional[str]): Conteúdo da mensagem a ser considerada para personalização.
            
        Returns:
            str: Mensagem de motivação.
        """
        try:
            # Cria um cliente da Anthropic com a chave da API
            client = AnthropicClient(Config.get_anthropic_api_key())
            
            # Obtém o prompt para a motivação
            prompt = Config.get_motivation_prompt()
            
            # Se um nome de usuário foi fornecido, personaliza o prompt
            if user_name:
                if message_content:
                    # Inclui o conteúdo da mensagem para personalizar ainda mais a resposta
                    prompt = f"Crie uma única frase motivacional curta e impactante sobre fitness, musculação ou vida saudável direcionada para {user_name}, considerando a mensagem: '{message_content}'. A frase deve ser personalizada para este usuário específico e relacionada ao conteúdo da mensagem.\n\nSIGA AS INSTRUÇÕES:\n{prompt}"
                else:
                    prompt = f"Crie uma única frase motivacional curta e impactante sobre fitness, musculação ou vida saudável direcionada para {user_name}. A frase deve ser personalizada para este usuário específico.\n\nSIGA AS INSTRUÇÕES:\n{prompt}"
            
            # Gera a resposta (com limite de 150 tokens para garantir uma resposta curta)
            response = await client.generate_response(prompt, "", max_tokens=150)
            
            return response.strip()
        except Exception as e:
            # Em caso de erro, retorna uma mensagem de motivação da lista fixa
            base_message = Messages.get_random_motivation_message()
            if user_name:
                return f"{user_name}, {base_message.lower()}"
            return base_message
    
    @staticmethod
    async def get_fecho_message_async(user_name: Optional[str] = None, message_content: Optional[str] = None) -> str:
        """
        Obtém uma tirada sarcástica e debochada gerada pela API da Anthropic,
        opcionalmente personalizada para um usuário específico e considerando o
        conteúdo da mensagem à qual está respondendo.
        
        Args:
            user_name (Optional[str]): Nome do usuário para personalizar a tirada.
            message_content (Optional[str]): Conteúdo da mensagem a ser considerada para personalização.
            
        Returns:
            str: Tirada sarcástica.
        """
        try:
            # Cria um cliente da Anthropic com a chave da API
            client = AnthropicClient(Config.get_anthropic_api_key())
            
            # Obtém o prompt para a tirada sarcástica
            prompt = Config.get_fecho_prompt()
            
            # Se um nome de usuário foi fornecido, personaliza o prompt
            if user_name:
                if message_content:
                    # Inclui o conteúdo da mensagem para personalizar ainda mais a resposta
                    prompt = f"Crie uma única tirada sarcástica e debochada com humor direcionada para {user_name}, considerando a mensagem: '{message_content}'. A tirada deve ser personalizada para este usuário específico e fazer uma piada relacionada ao conteúdo da mensagem.\n\nSIGA AS INSTRUÇÕES:\n{prompt}"
                else:
                    prompt = f"Crie uma única tirada sarcástica e debochada com humor direcionada para {user_name}. A tirada deve ser personalizada para este usuário específico.\n\nSIGA AS INSTRUÇÕES:\n{prompt}"
            
            # Gera a resposta (com limite de 150 tokens para garantir uma resposta curta)
            response = await client.generate_response(prompt, "", max_tokens=150)
            
            return response.strip()
        except Exception as e:
            # Em caso de erro, retorna uma tirada sarcástica genérica
            fallback_messages = [
                "😂 Essa foi tão boa que até a IA travou de tanto rir!",
                "🤣 Não consegui processar tamanha genialidade, tente de novo!",
                "😅 Meu detector de piadas quebrou com essa mensagem!",
                "😆 Tão engraçado que até meus circuitos deram tilt!",
                "🙄 Acho que vou precisar de um upgrade para entender essa...",
                "🤦‍♂️ Até eu, uma IA, fiquei sem palavras com essa!"
            ]
            base_message = random.choice(fallback_messages)
            if user_name:
                return f"{user_name}, {base_message}"
            return base_message
    
    @staticmethod
    async def get_motivation_message() -> str:
        """
        Obtém uma mensagem de motivação fitness gerada pela API da Anthropic.
        
        Returns:
            str: Mensagem de motivação.
        """
        return await Messages.get_motivation_message_async()
    
    @staticmethod
    def get_random_positive_emoji() -> str:
        """
        Obtém um emoji positivo aleatório para reações.
        
        Returns:
            str: Emoji positivo aleatório.
        """
        return random.choice(Messages.POSITIVE_REACTION_EMOJIS)
    
    @staticmethod
    async def get_presentation_response(message_content: str, image_data: Optional[bytes] = None, image_mime_type: Optional[str] = None) -> str:
        """
        Obtém uma resposta personalizada para uma mensagem de apresentação.
        
        Args:
            message_content (str): Conteúdo da mensagem de apresentação.
            image_data (Optional[bytes]): Dados binários da imagem, se houver.
            image_mime_type (Optional[str]): Tipo MIME da imagem (ex: "image/jpeg").
            
        Returns:
            str: Resposta personalizada.
        """
        try:
            # Cria um cliente da Anthropic com a chave da API
            client = AnthropicClient(Config.get_anthropic_api_key())
            
            # Se não houver imagem, usa o fluxo normal
            if not image_data or not image_mime_type:
                # Obtém o prompt para a apresentação
                prompt = Config.get_presentation_prompt()
                
                # Gera a resposta
                response = await client.generate_response(
                    prompt_template=prompt, 
                    message_content=message_content,
                    max_tokens=200  # Limita o tamanho da resposta
                )
                
                return response
            
            # Se houver imagem, primeiro analisa a imagem separadamente
            try:
                # Obtém o prompt para análise de imagem
                image_analysis_prompt = Config.get_image_analysis_prompt()
                
                # Gera a análise da imagem
                image_description = await client.generate_response(
                    prompt_template=image_analysis_prompt,
                    message_content="",
                    image_data=image_data,
                    image_mime_type=image_mime_type,
                    max_tokens=150  # Limita o tamanho da descrição
                )
                
                # Obtém o prompt para apresentação com imagem
                presentation_with_image_prompt = Config.get_presentation_with_image_prompt()
                
                # Substitui os placeholders no prompt
                prompt_with_description = presentation_with_image_prompt.replace(
                    "{{descricao_da_imagem}}", image_description
                )
                
                # Substitui também o placeholder da mensagem de apresentação
                prompt_with_description = prompt_with_description.replace(
                    "{{mensagem_de_apresentacao_membro}}", message_content
                )
                
                # Gera a resposta final usando o prompt completo
                response = await client.generate_response(
                    prompt_template=prompt_with_description,
                    message_content="",  # Já substituímos o placeholder manualmente
                    max_tokens=200  # Limita o tamanho da resposta
                )
                
                return response
                
            except Exception as e:
                # Se falhar na análise da imagem, tenta apenas com o texto
                prompt = Config.get_presentation_prompt()
                response = await client.generate_response(
                    prompt_template=prompt, 
                    message_content=message_content,
                    max_tokens=200  # Limita o tamanho da resposta
                )
                return response
                
        except Exception as e:
            # Em caso de erro, retorna uma mensagem genérica
            return f"Bem-vindo ao GYM NATION! Obrigado por se apresentar. 💪"
    
    @staticmethod
    async def get_macros_calculation(food_description: str) -> str:
        """
        Calcula os macronutrientes de uma receita ou alimento usando a API da Anthropic.
        
        Args:
            food_description (str): Descrição da receita ou alimento.
            
        Returns:
            str: Cálculo de macronutrientes formatado.
            
        Raises:
            Exception: Se ocorrer um erro ao gerar a resposta.
        """
        try:
            # Cria um cliente da Anthropic com a chave da API
            client = AnthropicClient(Config.get_anthropic_api_key())
            
            # Obtém o prompt para o cálculo de macronutrientes
            prompt = Config.get_macros_prompt()
            
            # Cria uma tarefa para gerar a resposta
            generate_task = asyncio.create_task(client.generate_response(
                prompt_template=prompt,
                message_content=food_description,
                max_tokens=5000  # Aumenta ainda mais o limite para garantir cálculos precisos
            ))
            
            # Aguarda a resposta com timeout de 30 segundos
            try:
                response = await asyncio.wait_for(generate_task, timeout=30.0)
                
                # Adiciona o disclaimer no final da resposta
                disclaimer = "\n\n⚠️ Nota: Estes valores são estimativas calculadas por IA e podem não refletir os valores nutricionais reais."
                
                return response.strip() + disclaimer
            except asyncio.TimeoutError:
                # Em caso de timeout, cancela a tarefa e informa o usuário
                generate_task.cancel()
                logger.error("Timeout ao calcular macronutrientes via API Anthropic")
                raise Exception("Tempo limite excedido ao calcular macronutrientes. Por favor, tente novamente.")
        except Exception as e:
            # Em caso de erro, retorna uma mensagem de erro
            logger.error(f"Erro ao calcular macronutrientes: {e}")
            raise Exception(f"Erro ao calcular macronutrientes: {e}") 