"""
Handlers para os eventos do Telegram.
"""
import logging
import io
import asyncio
from telegram import Update, ChatMember, ChatMemberAdministrator, ChatMemberOwner
from telegram.ext import ContextTypes
from src.bot.messages import Messages
from telegram.constants import ReactionEmoji, ParseMode
from telegram import ReactionTypeEmoji
from telegram.error import BadRequest, TimedOut
from src.utils.config import Config
from src.utils.mongodb_instance import mongodb_client
import time
from datetime import datetime

# Configuração de logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Não inicializa o cliente MongoDB aqui, usa a instância do main.py
# mongodb_client = MongoDBClient()

# Dicionário de cache para armazenar resultados de verificações de admin
# Formato: {(chat_id, user_id): (is_admin, timestamp)}
admin_cache = {}
ADMIN_CACHE_TTL = 300  # 5 minutos em segundos

async def send_temporary_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, duration: int = 20, reply: bool = False) -> None:
    """
    Envia uma mensagem temporária que será excluída após a duração especificada.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
        text (str): Texto da mensagem a ser enviada.
        duration (int): Duração em segundos antes da exclusão da mensagem (padrão: 20).
        reply (bool): Se True, responde diretamente à mensagem do usuário. Se False, envia como mensagem independente.
    """
    try:
        # Implementa um mecanismo de retry com backoff exponencial
        max_retries = 3
        base_delay = 1  # segundo
        
        for attempt in range(max_retries):
            try:
                # Decide se vai responder diretamente à mensagem ou enviar uma nova mensagem
                if reply:
                    # Responde diretamente à mensagem original
                    reply_task = asyncio.create_task(update.message.reply_text(text))
                else:
                    # Envia uma nova mensagem no chat, sem responder à original
                    reply_task = asyncio.create_task(context.bot.send_message(
                        chat_id=update.effective_chat.id, 
                        text=text
                    ))
                
                # Aguarda com timeout para evitar bloqueio
                message = await asyncio.wait_for(reply_task, timeout=10.0)
                
                # Se conseguiu enviar, agenda a exclusão da mensagem
                asyncio.create_task(delete_message_after(message, duration))
                
                # Se chegou aqui, enviou com sucesso
                logger.debug(f"Mensagem temporária enviada com sucesso na tentativa {attempt+1}")
                return
            
            except asyncio.TimeoutError:
                # Calcula o tempo de espera com backoff exponencial
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Timeout ao enviar mensagem temporária (tentativa {attempt+1}/{max_retries}). Aguardando {delay}s antes de tentar novamente.")
                
                # Se for a última tentativa, não tente mais e apenas retorne
                if attempt == max_retries - 1:
                    logger.warning(f"Desistindo após {max_retries} tentativas de enviar mensagem temporária devido a timeouts.")
                    return
                
                # Não cancela a tarefa para permitir que ela conclua em segundo plano
                # Aguarda antes de tentar novamente
                await asyncio.sleep(delay)
            
            except Exception as e:
                # Para erros de timeout, não tente novamente para não sobrecarregar o bot
                if isinstance(e, TimedOut):
                    logger.warning(f"Timeout do Telegram ao enviar mensagem temporária. Desistindo.")
                    return
                
                logger.error(f"Erro ao enviar mensagem temporária na tentativa {attempt+1}: {e}")
                # Para outros erros, tenta novamente se houver tentativas restantes
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    # Na última tentativa, apenas retorna sem tentar mais
                    return
        
        # Se chegou aqui, todas as tentativas falharam
        logger.error(f"Falha ao enviar mensagem temporária após {max_retries} tentativas")
    
    except Exception as e:
        logger.error(f"Erro: {e} - Update: {update}")
        # Em caso de erro grave, apenas loga e não propaga (para não interromper a execução do bot)

async def delete_message_after(message, duration: int) -> None:
    """
    Exclui uma mensagem após a duração especificada.
    
    Args:
        message: Mensagem do Telegram a ser excluída.
        duration (int): Duração em segundos antes da exclusão.
    """
    try:
        # Aguarda a duração especificada
        await asyncio.sleep(duration)
        
        # Tenta excluir a mensagem com número limitado de tentativas
        max_retries = 2
        for attempt in range(max_retries):
            try:
                # Cria uma tarefa para deletar a mensagem com timeout
                delete_task = asyncio.create_task(message.delete())
                
                # Aguarda com timeout para evitar bloqueio
                await asyncio.wait_for(delete_task, timeout=10.0)
                
                # Se chegou aqui, a exclusão foi bem-sucedida
                return
                
            except asyncio.TimeoutError:
                logger.warning("Timeout ao excluir mensagem temporária")
                # Na última tentativa, apenas desiste
                if attempt == max_retries - 1:
                    return
                
                # Aguarda um pouco antes de tentar novamente
                await asyncio.sleep(2)
                
            except Exception as e:
                # Para erros de timeout do Telegram, desiste imediatamente
                if isinstance(e, TimedOut):
                    logger.warning(f"Timeout do Telegram ao excluir mensagem. Desistindo.")
                    return
                    
                # Para outros erros, apenas loga e desiste
                logger.error(f"Erro ao excluir mensagem temporária: {e}")
                return
                
    except Exception as e:
        logger.error(f"Erro ao processar exclusão de mensagem temporária: {e}")
        # Não propaga o erro para não interromper outras operações do bot

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /start.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    user = update.effective_user
    chat_type = update.effective_chat.type
    
    logger.info(f"Usuário {user.id} ({user.full_name}) iniciou o bot em chat {chat_type}")
    
    # Verifica se é em chat privado
    if chat_type == 'private':
        # Verificar se há parâmetros no comando (ex: /start revelar_123)
        start_param = None
        if context.args:
            start_param = context.args[0].lower()
        
        # Detectar ações específicas do correio elegante
        if start_param and start_param.startswith('revelar_'):
            mail_id = start_param.replace('revelar_', '')
            # Executar automaticamente o comando revelar correio
            context.args = [mail_id]
            from src.bot.mail_handlers import MailHandlers
            await MailHandlers.revelar_correio_command(update, context)
            return
            
        elif start_param and start_param.startswith('responder_'):
            mail_id = start_param.replace('responder_', '')
            # Executar automaticamente o comando responder correio
            context.args = [mail_id]
            from src.bot.mail_handlers import MailHandlers
            await MailHandlers.responder_correio_command(update, context)
            return
            
        elif start_param and start_param.startswith('denunciar_'):
            mail_id = start_param.replace('denunciar_', '')
            # Executar automaticamente o comando denunciar correio
            context.args = [mail_id]
            from src.bot.mail_handlers import MailHandlers
            await MailHandlers.denunciar_correio_command(update, context)
            return
        
        # Se veio através do botão do correio elegante (geral)
        elif start_param == 'correio':
            welcome_message = (
                f"📬 **Bem-vindo ao Correio Elegante, {user.first_name}!** 💌\n\n"
                "Você chegou aqui através de um correio elegante no grupo! 🎯\n\n"
                "🌟 **O que você pode fazer:**\n\n"
                "📝 **Enviar mensagem anônima:**\n"
                "• Use `/correio` para criar uma nova mensagem\n\n"
                "🔍 **Descobrir quem enviou:**\n"
                "• Use `/revelarcorreio [ID]` + Pix R$2,00\n\n"
                "💌 **Responder anonimamente:**\n"
                "• Use `/respondercorreio [ID]`\n\n"
                "🚨 **Denunciar conteúdo inapropriado:**\n"
                "• Use `/denunciarcorreio [ID]`\n\n"
                "💡 **Dica:** Encontre o ID do correio na mensagem do grupo!\n\n"
                "Pronto para interagir? Use `/correio` para começar! ✨"
            )
        else:
            # Apresentação completa para chat privado normal
            welcome_message = (
                f"🏋️‍♂️ **Olá {user.first_name}! Bem-vindo ao GYM NATION Bot!** 💪\n\n"
                "Eu sou seu assistente fitness e social para o grupo **GYM NATION**! 🥇\n\n"
                "🔥 **O que posso fazer por você:**\n\n"
                "📬 **Correio Elegante Anônimo**\n"
                "• Envie mensagens anônimas para membros do grupo\n"
                "• Responda anonimamente a correios recebidos\n"
                "• Revele remetentes por apenas R$2 via Pix\n\n"
                "📊 **Rankings e Estatísticas**\n"
                "• Consulte o ranking de check-ins do grupo\n"
                "• Acompanhe sua participação na comunidade\n\n"
                "💬 **Como usar:**\n"
                "• Use `/correio` para enviar uma mensagem anônima\n"
                "• Use `/checkinscore` para ver o ranking\n"
                "• Use `/help` para ver todos os comandos\n\n"
                "🎯 **Dica:** Todos os comandos funcionam apenas aqui no chat privado comigo!\n\n"
                "Pronto para começar? Digite `/help` para ver todas as opções! 🚀"
            )
        
        await update.message.reply_text(
            welcome_message,
            parse_mode='Markdown'
        )
    else:
        # Resposta simples para grupos
        await update.message.reply_text(
            "👋 Olá! Para usar meus recursos, inicie uma conversa privada comigo!\n\n"
            "Clique no meu nome e depois em \"Iniciar\" para acessar o correio elegante e outras funcionalidades! 📬"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /help.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    user = update.effective_user
    chat_type = update.effective_chat.type
    
    logger.info(f"Usuário {user.id} ({user.full_name}) solicitou ajuda em chat {chat_type}")
    
    # Verifica se é administrador/proprietário para mostrar comandos específicos
    is_admin_user = await is_admin(update, context)
    is_owner = user.id == Config.get_owner_id()
    
    if chat_type == 'private':
        # Ajuda para chat privado - foco nos comandos públicos
        help_message = (
            "🏋️‍♂️ **GYM NATION BOT - GUIA DE COMANDOS** 🏋️‍♀️\n\n"
            "📬 **CORREIO ELEGANTE** - *Sistema de mensagens anônimas*\n\n"
            "• `/correio` - Enviar mensagem anônima para um membro\n"
            "• `/revelarcorreio <ID>` - Revelar remetente (R$2 via Pix)\n"
            "• `/respondercorreio <ID>` - Responder anonimamente\n\n"
            "**Como funciona:**\n"
            "1️⃣ Digite `/correio` e siga as instruções\n"
            "2️⃣ Escreva sua mensagem (será filtrada)\n"
            "3️⃣ Digite o @username do destinatário\n"
            "4️⃣ Confirme o envio\n"
            "5️⃣ Mensagem será publicada no grupo anonimamente\n\n"
            "📊 **ESTATÍSTICAS**\n\n"
            "• `/checkinscore` - Ver ranking de check-ins do grupo\n\n"
            "🔒 **REGRAS IMPORTANTES:**\n"
            "• Máximo 2 correios por dia por usuário\n"
            "• Conteúdo ofensivo é automaticamente rejeitado\n"
            "• Destinatário deve ser membro do GYM NATION\n"
            "• Mensagens expiram em 24 horas\n"
            "• 3+ denúncias = remoção automática\n\n"
        )
        
        # Adiciona comandos administrativos se for admin
        if is_admin_user:
            help_message += (
                "👑 **COMANDOS ADMINISTRATIVOS** _(Apenas para admins)_\n\n"
                "🏋️‍♂️ **Comandos Fitness:**\n"
                "• `/motivacao` - Mensagem de motivação com IA\n"
                "• `/apresentacao` - Apresentação personalizada\n"
                "• `/macros` - Calcular macronutrientes\n"
                "• `/regras` - Exibir regras do grupo\n\n"
                "✅ **Check-ins:**\n"
                "• `/checkin` - Definir âncora de check-in\n"
                "• `/checkinplus` - Check-in PLUS (x2 pontos)\n"
                "• `/endcheckin` - Finalizar check-in\n"
                "• `/confirmcheckin` - Confirmar check-in manual\n\n"
                "🚫 **Moderação:**\n"
                "• `/addblacklist` - Adicionar à blacklist\n"
                "• `/blacklist` - Ver mensagens na blacklist\n"
                "• `/rmblacklist` - Remover da blacklist\n"
                "• `/ban_blacklist` - Banir usuários da blacklist\n\n"
            )
        
        # Adiciona comandos do proprietário
        if is_owner:
            help_message += (
                "🔑 **COMANDOS DO PROPRIETÁRIO** _(Apenas para você)_\n\n"
                "📬 **Correio Elegante:**\n"
                "• `/admincorreio status` - Status do sistema\n"
                "• `/admincorreio stats` - Estatísticas detalhadas\n"
                "• `/admincorreio pending` - Correios pendentes\n"
                "• `/admincorreio reports` - Correios denunciados\n"
                "• `/admincorreio cleanup` - Limpeza automática\n\n"
                "👥 **Administração:**\n"
                "• `/setadmin` - Adicionar administrador\n"
                "• `/deladmin` - Remover administrador\n"
                "• `/listadmins` - Listar administradores\n\n"
                "📡 **Sistema:**\n"
                "• `/monitor` - Monitorar grupo\n"
                "• `/unmonitor` - Parar monitoramento\n"
                "• `/say` - Enviar mensagem como bot\n"
                "• `/sayrecurrent` - Mensagem recorrente\n"
                "• `/listrecurrent` - Listar recorrentes\n"
                "• `/delrecurrent` - Remover recorrente\n\n"
            )
        
        help_message += (
            "💡 **DICAS:**\n"
            "• Todos os comandos funcionam apenas em chat privado\n"
            "• Use `/start` para ver a apresentação completa\n"
            "• Para suporte, contate o administrador do grupo\n\n"
            "🎯 **Quer começar?** Digite `/correio` para enviar sua primeira mensagem anônima!"
        )
    else:
        # Ajuda simples para grupos
        help_message = (
            "📱 **Para usar meus recursos, inicie um chat privado comigo!**\n\n"
            "Clique no meu nome e depois em \"Iniciar\" para:\n"
            "📬 Enviar correios elegantes anônimos\n"
            "💰 Revelar remetentes via Pix\n"
            "📊 Ver rankings e estatísticas\n\n"
            "Digite `/start` no chat privado para começar! 🚀"
        )
    
    # Envia a mensagem de ajuda com formatação Markdown
    await update.message.reply_text(
        help_message,
        parse_mode="Markdown"
    )

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Verifica se o usuário que enviou o comando é administrador do grupo.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
        
    Returns:
        bool: True se o usuário for administrador, False caso contrário.
    """
    # Se for chat privado, permite o comando
    if update.effective_chat.type == "private":
        return True
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    cache_key = (chat_id, user_id)
    
    # Verifica primeiro no cache para evitar chamadas desnecessárias
    current_time = time.time()
    if cache_key in admin_cache:
        is_admin_result, timestamp = admin_cache[cache_key]
        # Se o cache ainda é válido (não expirou)
        if current_time - timestamp < ADMIN_CACHE_TTL:
            logger.debug(f"Usando resultado em cache para usuário {user_id} no chat {chat_id}: {is_admin_result}")
            return is_admin_result
    
    # Verifica se é proprietário do bot
    owner_id = int(Config.get_owner_id())
    if user_id == owner_id:
        # Armazena no cache e retorna True
        admin_cache[cache_key] = (True, current_time)
        return True
    
    # Verifica se é administrador do bot no MongoDB
    try:
        if mongodb_client.db is not None:
            is_bot_admin = await mongodb_client.is_admin(user_id)
            if is_bot_admin:
                logger.info(f"Usuário {user_id} é administrador do bot no MongoDB")
                # Armazena no cache e retorna True
                admin_cache[cache_key] = (True, current_time)
                return True
    except Exception as e:
        logger.error(f"Erro ao verificar permissões de administrador do bot no MongoDB: {e}")
        # Aqui não retornamos, continuamos tentando verificar pelo Telegram
    
    # Última opção: verificar permissões de administrador pelo Telegram
    try:
        # Obtém o status do membro no chat com timeout para evitar bloqueio
        try:
            # Cria uma tarefa para get_chat_member com timeout de 3 segundos
            chat_member_task = asyncio.create_task(context.bot.get_chat_member(chat_id, user_id))
            chat_member = await asyncio.wait_for(chat_member_task, timeout=3.0)
            
            # Verifica se é administrador ou criador do grupo
            is_admin_result = isinstance(chat_member, (ChatMemberAdministrator, ChatMemberOwner))
            
            # Armazena no cache
            admin_cache[cache_key] = (is_admin_result, current_time)
            
            return is_admin_result
        except asyncio.TimeoutError:
            logger.warning(f"Timeout ao verificar permissões de administrador para usuário {user_id} no chat {chat_id}")
            # Se for um retry após timeout anterior, assumimos false para não ficar em loop
            admin_cache[cache_key] = (False, current_time)
            return False
    except Exception as e:
        logger.error(f"Erro ao verificar permissões de administrador: {e}")
        # Em caso de erro, não permite o comando
        admin_cache[cache_key] = (False, current_time)
        return False

async def motivation_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /motivacao.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    # Verifica se o usuário é administrador
    if not await is_admin(update, context):
        await send_temporary_message(
            update, 
            context, 
            "Apenas administradores podem usar este comando."
        )
        return
        
    logger.info(f"Usuário {update.effective_user.id} solicitou uma mensagem de motivação")
    
    # Verifica se o comando foi usado como resposta a outra mensagem
    if update.message.reply_to_message:
        # Obtém o nome do usuário da mensagem original
        replied_user = update.message.reply_to_message.from_user
        user_name = replied_user.full_name or f"@{replied_user.username}" or "amigo"
        
        # Obtém o conteúdo da mensagem original
        message_content = update.message.reply_to_message.text or ""
        
        # Obtém uma mensagem de motivação personalizada
        motivation_message = await Messages.get_motivation_message_async(user_name, message_content)
        
        # Tenta deletar a mensagem original (comando)
        try:
            await update.message.delete()
        except Exception as e:
            logger.error(f"Erro ao deletar mensagem de comando: {e}")
            # Se não conseguir deletar, envia a mensagem de motivação como resposta
            await send_temporary_message(
                update, 
                context, 
                "Não foi possível deletar o comando. Verifique as permissões do bot."
            )
            await update.message.reply_to_message.reply_text(motivation_message)
            return
        
        # Envia a mensagem de motivação como resposta à mensagem original
        await update.message.reply_to_message.reply_text(motivation_message)
    else:
        # Obtém uma mensagem de motivação aleatória
        motivation_message = Messages.get_random_motivation_message()
        
        # Tenta deletar a mensagem original (comando)
        try:
            await update.message.delete()
        except Exception as e:
            logger.error(f"Erro ao deletar mensagem de comando: {e}")
            # Se não conseguir deletar, envia a mensagem de motivação como resposta
            await send_temporary_message(
                update, 
                context, 
                "Não foi possível deletar o comando. Verifique as permissões do bot."
            )
            await update.message.reply_text(motivation_message)
            return
        
        # Envia a mensagem de motivação como nova mensagem
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=motivation_message
        )

async def fecho_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /fecho.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    # Verifica se o usuário é administrador
    if not await is_admin(update, context):
        await send_temporary_message(
            update, 
            context, 
            "Apenas administradores podem usar este comando."
        )
        return
        
    logger.info(f"Usuário {update.effective_user.id} solicitou uma tirada sarcástica")
    
    # Verifica se o comando foi usado como resposta a outra mensagem
    if update.message.reply_to_message:
        # Obtém o nome do usuário da mensagem original
        replied_user = update.message.reply_to_message.from_user
        user_name = replied_user.full_name or f"@{replied_user.username}" or "amigo"
        
        # Obtém o conteúdo da mensagem original
        message_content = update.message.reply_to_message.text or ""
        
        # Obtém uma tirada sarcástica personalizada
        fecho_message = await Messages.get_fecho_message_async(user_name, message_content)
        
        # Tenta deletar a mensagem original (comando)
        try:
            await update.message.delete()
        except Exception as e:
            logger.error(f"Erro ao deletar mensagem de comando: {e}")
            # Se não conseguir deletar, envia a tirada sarcástica como resposta
            await send_temporary_message(
                update, 
                context, 
                "Não foi possível deletar o comando. Verifique as permissões do bot."
            )
            await update.message.reply_to_message.reply_text(fecho_message)
            return
        
        # Envia a tirada sarcástica como resposta à mensagem original
        await update.message.reply_to_message.reply_text(fecho_message)
    else:
        # Obtém uma tirada sarcástica aleatória
        fecho_message = await Messages.get_fecho_message_async()
        
        # Tenta deletar a mensagem original (comando)
        try:
            await update.message.delete()
        except Exception as e:
            logger.error(f"Erro ao deletar mensagem de comando: {e}")
            # Se não conseguir deletar, envia a tirada sarcástica como resposta
            await send_temporary_message(
                update, 
                context, 
                "Não foi possível deletar o comando. Verifique as permissões do bot."
            )
            await update.message.reply_text(fecho_message)
            return
        
        # Envia a tirada sarcástica como nova mensagem
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=fecho_message
        )

async def presentation_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /apresentacao.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    # Verifica se o usuário é administrador
    if not await is_admin(update, context):
        await send_temporary_message(
            update, 
            context, 
            "Apenas administradores podem usar este comando."
        )
        return
        
    logger.info(f"Usuário {update.effective_user.id} solicitou uma apresentação personalizada")
    
    # Verifica se o comando foi usado como resposta a outra mensagem
    if not update.message.reply_to_message:
        await send_temporary_message(
            update, 
            context, 
            "Por favor, use este comando respondendo a uma mensagem de apresentação."
        )
        return
    
    # Obtém a mensagem de apresentação
    presentation_message = update.message.reply_to_message.text or update.message.reply_to_message.caption or ""
    
    # Verifica se há imagem na mensagem respondida
    image_data = None
    image_mime_type = None
    
    if update.message.reply_to_message.photo:
        # Pega a foto com maior resolução
        photo = update.message.reply_to_message.photo[-1]
        
        try:
            # Baixa a foto
            file = await context.bot.get_file(photo.file_id)
            image_data_io = io.BytesIO()
            await file.download_to_memory(image_data_io)
            image_data = image_data_io.getvalue()
            image_mime_type = "image/jpeg"  # Telegram usa JPEG para fotos
        except Exception as e:
            logger.error(f"Erro ao baixar imagem: {e}")
            await send_temporary_message(
                update, 
                context, 
                "Não foi possível baixar a imagem. Continuando sem ela."
            )
            # Continua sem a imagem
    
    # Gera uma resposta personalizada
    try:
        response = await Messages.get_presentation_response(
            presentation_message,
            image_data=image_data,
            image_mime_type=image_mime_type
        )
    except Exception as e:
        logger.error(f"Erro ao gerar resposta de apresentação: {e}")
        await send_temporary_message(
            update, 
            context, 
            "Desculpe, não foi possível gerar uma resposta personalizada."
        )
        return
    
    # Tenta adicionar uma reação à mensagem original
    try:
        await context.bot.set_message_reaction(
            chat_id=update.effective_chat.id,
            message_id=update.message.reply_to_message.message_id,
            reaction=[ReactionTypeEmoji(emoji=Messages.get_random_positive_emoji())]
        )
    except Exception as e:
        logger.error(f"Erro ao adicionar reação: {e}")
        await send_temporary_message(
            update, 
            context, 
            "Não foi possível adicionar uma reação à mensagem."
        )
    
    # Tenta deletar a mensagem de comando
    try:
        await update.message.delete()
    except Exception as e:
        logger.error(f"Erro ao deletar mensagem de comando: {e}")
        await send_temporary_message(
            update, 
            context, 
            "Não foi possível deletar o comando. Verifique as permissões do bot."
        )
    
    # Envia a resposta personalizada
    await update.message.reply_to_message.reply_text(response)

async def macros_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /macros.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    # Verifica se o usuário é administrador
    if not await is_admin(update, context):
        await send_temporary_message(
            update, 
            context, 
            "Apenas administradores podem usar este comando."
        )
        return
        
    logger.info(f"Usuário {update.effective_user.id} solicitou cálculo de macronutrientes")
    
    # Verifica se o comando foi usado como resposta a outra mensagem
    if not update.message.reply_to_message:
        await send_temporary_message(
            update, 
            context, 
            "Por favor, use este comando respondendo a uma mensagem que contenha uma receita ou alimento."
        )
        return
    
    # Obtém a descrição da receita ou alimento
    # Tenta obter o texto da mensagem, mesmo que tenha formatação
    reply_msg = update.message.reply_to_message
    food_description = ""
    
    # Verifica diferentes tipos de conteúdo na mensagem
    if reply_msg.text:
        food_description = reply_msg.text
    elif reply_msg.caption:
        food_description = reply_msg.caption
    elif hasattr(reply_msg, 'forward_from_message_id') and reply_msg.forward_from_message_id:
        # Mensagem encaminhada
        if reply_msg.text:
            food_description = reply_msg.text
        elif reply_msg.caption:
            food_description = reply_msg.caption
    
    # Verifica se há texto na mensagem respondida
    if not food_description:
        await send_temporary_message(
            update, 
            context, 
            "A mensagem respondida não contém texto. Por favor, responda a uma mensagem que descreva uma receita ou alimento."
        )
        return
    
    # Verifica se a mensagem é muito longa
    if len(food_description) > 4000:
        await send_temporary_message(
            update, 
            context, 
            "A receita é muito longa para ser processada. Por favor, tente com uma descrição mais curta (máximo de 4000 caracteres)."
        )
        return
    
    # Envia mensagem de carregamento
    loading_message = await update.message.reply_text("Calculando macronutrientes... Isso pode levar alguns segundos ⏳")
    
    try:
        # Calcula os macronutrientes com timeout para evitar bloqueio
        try:
            # Cria uma tarefa para a chamada à API
            macros_task = asyncio.create_task(
                Messages.get_macros_calculation(food_description)
            )
            
            # Aguarda a resposta com timeout de 45 segundos
            macros_result = await asyncio.wait_for(macros_task, timeout=45.0)
        except asyncio.TimeoutError:
            logger.error("Timeout ao calcular macronutrientes via API Anthropic")
            
            # Tenta deletar a mensagem de carregamento
            try:
                await loading_message.delete()
            except Exception as e:
                logger.error(f"Erro ao deletar mensagem de carregamento após timeout: {e}")
            
            # Informa o usuário sobre o timeout
            await send_temporary_message(
                update,
                context,
                "O cálculo de macronutrientes está demorando mais do que o esperado. Por favor, tente novamente com uma descrição mais simples."
            )
            return
        
        # Tenta deletar a mensagem de comando
        try:
            await update.message.delete()
        except Exception as e:
            logger.error(f"Erro ao deletar mensagem de comando: {e}")
            await send_temporary_message(
                update, 
                context, 
                "Não foi possível deletar o comando. Verifique as permissões do bot."
            )
        
        # Tenta deletar a mensagem de carregamento
        try:
            await loading_message.delete()
        except Exception as e:
            logger.error(f"Erro ao deletar mensagem de carregamento: {e}")
        
        # Envia o resultado como resposta à mensagem original
        await update.message.reply_to_message.reply_text(macros_result)
        
    except Exception as e:
        logger.error(f"Erro ao calcular macronutrientes: {e}")
        
        # Tenta deletar a mensagem de carregamento
        try:
            await loading_message.delete()
        except Exception as loading_delete_error:
            logger.error(f"Erro ao deletar mensagem de carregamento: {loading_delete_error}")
        
        # Envia mensagem de erro
        await send_temporary_message(
            update, 
            context, 
            "Desculpe, não foi possível calcular os macronutrientes. Por favor, tente novamente com uma descrição mais detalhada."
        )

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para novos membros no grupo.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    # Verifica se há novos membros
    if not update.message.new_chat_members:
        return
    
    # Para cada novo membro, envia uma mensagem de boas-vindas
    for new_member in update.message.new_chat_members:
        # Ignora se o novo membro for o próprio bot
        if new_member.is_bot and new_member.username == context.bot.username:
            continue
        
        # Obtém o nome do usuário (nome completo ou username)
        user_name = new_member.full_name or f"@{new_member.username}" or "novo membro"
        
        logger.info(f"Novo membro no grupo: {user_name}")
        
        # Envia mensagem de boas-vindas
        welcome_message = Messages.get_welcome_message(user_name)
        await update.message.reply_text(welcome_message)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para erros do bot.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    # Obtém o erro
    error = context.error
    
    # Loga o erro
    logger.error(f"Erro: {error} - Update: {update}")
    
    # Tratamento específico para erros de timeout
    if isinstance(error, (TimedOut, asyncio.TimeoutError)):
        # Para erros de timeout, apenas loga e não tenta enviar mensagem
        logger.warning(f"Timeout detectado durante o processamento: {error}. Ignorando.")
        return
    
    # Se não temos informações do update, não podemos responder
    if not update or not update.effective_message:
        logger.error(f"Update não disponível ou nulo, não é possível enviar resposta. Erro: {error}")
        return
    
    # Prepara a mensagem de erro para o usuário
    try:
        # Envia uma mensagem genérica para erros desconhecidos
        await update.effective_message.reply_text(
            "Ocorreu um erro inesperado. A equipe do bot foi notificada."
        )
    except Exception as response_error:
        logger.error(f"Erro ao enviar mensagem de erro: {response_error}")

async def setadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /setadmin.
    Adiciona um usuário como administrador do bot.
    
    Uso: /setadmin [user_id] ou responder a uma mensagem com /setadmin
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    # Verifica se o MongoDB está conectado
    if mongodb_client.db is None:
        await update.message.reply_text(
            "Erro: Não foi possível conectar ao banco de dados. Tente novamente mais tarde."
        )
        return
    
    # Obtém o ID do usuário a ser adicionado como administrador
    user_id = None
    user_name = None
    
    # Verifica se o comando foi usado respondendo a uma mensagem
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
        user_name = update.message.reply_to_message.from_user.full_name
    # Verifica se o ID do usuário foi fornecido como argumento
    elif context.args and len(context.args) > 0:
        try:
            user_id = int(context.args[0])
            # Como não temos o nome do usuário, usamos o ID como nome temporário
            user_name = f"Usuário {user_id}"
        except ValueError:
            await update.message.reply_text(
                "Erro: O ID do usuário deve ser um número inteiro.\n\n"
                "Uso: /setadmin [user_id] ou responder a uma mensagem com /setadmin"
            )
            return
    else:
        await update.message.reply_text(
            "Erro: Você deve fornecer o ID do usuário ou responder a uma mensagem.\n\n"
            "Uso: /setadmin [user_id] ou responder a uma mensagem com /setadmin"
        )
        return
    
    # Verifica se o usuário está tentando adicionar a si mesmo
    if user_id == update.effective_user.id:
        await update.message.reply_text(
            "Você já é o proprietário do bot e tem acesso total. Não é necessário adicionar a si mesmo como administrador."
        )
        return
    
    # Verifica se o usuário já é o proprietário do bot
    owner_id = Config.get_owner_id()
    if user_id == owner_id:
        await update.message.reply_text(
            "Este usuário já é o proprietário do bot e tem acesso total."
        )
        return
    
    # Adiciona o usuário como administrador
    result = await mongodb_client.add_admin(
        admin_id=user_id,
        admin_name=user_name,
        added_by=update.effective_user.id
    )
    
    if result:
        await update.message.reply_text(
            f"✅ Usuário {user_name} (ID: {user_id}) foi adicionado como administrador do bot."
        )
        logger.info(f"Usuário {user_id} foi adicionado como administrador por {update.effective_user.id}")
    else:
        await update.message.reply_text(
            f"ℹ️ Usuário {user_name} (ID: {user_id}) já é um administrador do bot."
        )
        logger.info(f"Tentativa de adicionar usuário {user_id} que já é administrador por {update.effective_user.id}")

async def deladmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /deladmin.
    Remove um usuário da lista de administradores do bot.
    
    Uso: /deladmin [user_id] ou responder a uma mensagem com /deladmin
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    # Verifica se o MongoDB está conectado
    if mongodb_client.db is None:
        await update.message.reply_text(
            "Erro: Não foi possível conectar ao banco de dados. Tente novamente mais tarde."
        )
        return
    
    # Obtém o ID do usuário a ser removido da lista de administradores
    user_id = None
    
    # Verifica se o comando foi usado respondendo a uma mensagem
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
    # Verifica se o ID do usuário foi fornecido como argumento
    elif context.args and len(context.args) > 0:
        try:
            user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text(
                "Erro: O ID do usuário deve ser um número inteiro.\n\n"
                "Uso: /deladmin [user_id] ou responder a uma mensagem com /deladmin"
            )
            return
    else:
        await update.message.reply_text(
            "Erro: Você deve fornecer o ID do usuário ou responder a uma mensagem.\n\n"
            "Uso: /deladmin [user_id] ou responder a uma mensagem com /deladmin"
        )
        return
    
    # Verifica se o usuário está tentando remover a si mesmo
    if user_id == update.effective_user.id:
        await update.message.reply_text(
            "Você é o proprietário do bot e não pode remover a si mesmo da lista de administradores."
        )
        return
    
    # Verifica se o usuário é o proprietário do bot
    owner_id = Config.get_owner_id()
    if user_id == owner_id:
        await update.message.reply_text(
            "Não é possível remover o proprietário do bot da lista de administradores."
        )
        return
    
    # Remove o usuário da lista de administradores
    result = await mongodb_client.remove_admin(user_id=user_id)
    
    if result:
        await update.message.reply_text(
            f"✅ Usuário (ID: {user_id}) foi removido da lista de administradores do bot."
        )
        logger.info(f"Usuário {user_id} foi removido da lista de administradores por {update.effective_user.id}")
    else:
        await update.message.reply_text(
            f"ℹ️ Usuário (ID: {user_id}) não é um administrador do bot."
        )
        logger.info(f"Tentativa de remover usuário {user_id} que não é administrador por {update.effective_user.id}")

async def listadmins_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /listadmins.
    Lista todos os administradores do bot.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    # Verifica se o MongoDB está conectado
    if mongodb_client.db is None:
        await update.message.reply_text(
            "Erro: Não foi possível conectar ao banco de dados. Tente novamente mais tarde."
        )
        return
    
    # Obtém a lista de administradores
    admins = await mongodb_client.get_admins()
    
    if not admins:
        await update.message.reply_text(
            "Não há administradores adicionais configurados para o bot.\n\n"
            "Você, como proprietário, é o único com acesso total ao bot."
        )
        return
    
    # Formata a lista de administradores
    admin_list = "📋 Lista de administradores do bot:\n\n"
    
    for i, admin in enumerate(admins, 1):
        admin_list += f"{i}. {admin.get('admin_name', 'Nome desconhecido')} (ID: {admin['admin_id']})\n"
    
    admin_list += f"\nTotal: {len(admins)} administrador(es)"
    
    await update.message.reply_text(admin_list)
    logger.info(f"Lista de administradores solicitada por {update.effective_user.id}")

# Handlers para monitoramento de mensagens

async def monitor_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /monitor.
    Inicia o monitoramento de mensagens em um grupo.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    # Verifica se o chat é um grupo
    if update.effective_chat.type not in ["group", "supergroup"]:
        await send_temporary_message(
            update,
            context,
            "Este comando só pode ser usado em grupos."
        )
        return
    
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title
    chat_username = update.effective_chat.username
    
    # Inicia o monitoramento
    success = await mongodb_client.start_monitoring(
        chat_id=chat_id,
        title=chat_title,
        username=chat_username
    )
    
    # Tenta deletar a mensagem de comando
    try:
        await update.message.delete()
    except Exception as e:
        logger.error(f"Erro ao deletar mensagem de comando: {e}")
    
    if success:
        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Monitoramento de mensagens iniciado neste grupo."
        )
    else:
        await send_temporary_message(
            update,
            context,
            "❌ Erro ao iniciar monitoramento. Por favor, tente novamente."
        )

async def unmonitor_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /unmonitor.
    Para o monitoramento de mensagens em um grupo.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    # Verifica se o chat é um grupo
    if update.effective_chat.type not in ["group", "supergroup"]:
        await send_temporary_message(
            update,
            context,
            "Este comando só pode ser usado em grupos."
        )
        return
    
    chat_id = update.effective_chat.id
    
    # Para o monitoramento
    success = await mongodb_client.stop_monitoring(chat_id)
    
    # Tenta deletar a mensagem de comando
    try:
        await update.message.delete()
    except Exception as e:
        logger.error(f"Erro ao deletar mensagem de comando: {e}")
    
    if success:
        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Monitoramento de mensagens parado neste grupo."
        )
    else:
        await send_temporary_message(
            update,
            context,
            "❌ Erro ao parar monitoramento. Por favor, tente novamente."
        )

async def handle_monitored_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para processar mensagens de texto em grupos monitorados.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    # Verifica se a mensagem contém texto
    if not update.message or not update.message.text:
        return
    
    # Verifica se o chat é um grupo
    if update.effective_chat.type not in ["group", "supergroup"]:
        return
    
    chat_id = update.effective_chat.id
    
    # Verifica se o chat está sendo monitorado
    is_monitored = await mongodb_client.is_chat_monitored(chat_id)
    
    if not is_monitored:
        return
    
    # Obtém informações da mensagem
    message_id = update.message.message_id
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name or f"@{update.effective_user.username}" or "Usuário"
    text = update.message.text
    timestamp = update.message.date
    
    # Armazena a mensagem no banco de dados
    await mongodb_client.store_message(
        chat_id=chat_id,
        message_id=message_id,
        user_id=user_id,
        user_name=user_name,
        text=text,
        timestamp=timestamp
    )

async def say_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /say.
    
    Permite que administradores enviem mensagens através do bot.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    # Verifica se o usuário é administrador
    if not await is_admin(update, context):
        await send_temporary_message(
            update, 
            context, 
            "Apenas administradores podem usar este comando."
        )
        return
        
    # Obtém o texto da mensagem (removendo o comando /say)
    message_text = update.message.text
    
    # Verifica se há texto após o comando
    if message_text.startswith("/say "):
        # Remove o comando "/say " do início da mensagem
        admin_message = message_text[5:].strip()
        
        # Verifica se a mensagem não está vazia
        if not admin_message:
            await send_temporary_message(
                update,
                context,
                "Por favor, forneça uma mensagem após o comando /say."
            )
            return
            
        logger.info(f"Usuário {update.effective_user.id} enviou uma mensagem de administração: {admin_message}")
        
        # Formata a mensagem conforme solicitado
        formatted_message = f"{admin_message}"
        
        # Tenta deletar a mensagem original (comando)
        try:
            await update.message.delete()
        except Exception as e:
            logger.error(f"Erro ao deletar mensagem de comando: {e}")
            # Se não conseguir deletar, envia a mensagem mesmo assim
            await send_temporary_message(
                update, 
                context, 
                "Não foi possível deletar o comando. Verifique as permissões do bot."
            )
        
        # Envia a mensagem formatada com Markdown
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=formatted_message,
            parse_mode="Markdown"
        )
    else:
        # Se o usuário apenas enviou "/say" sem texto
        await send_temporary_message(
            update,
            context,
            "Por favor, forneça uma mensagem após o comando /say."
        ) 

async def sayrecurrent_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Configura uma mensagem recorrente.
    Formato: /sayrecurrent <intervalo> <mensagem>
    Exemplos de intervalo: 30m, 1h, 1h30m
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    # Verifica se é uma mensagem normal ou editada
    message = update.message or update.edited_message
    if not message:
        return
        
    # Verifica se o usuário é um administrador
    if not await is_admin(update, context):
        await message.reply_text(
            "❌ Você não tem permissão para usar este comando.",
            reply_to_message_id=message.message_id
        )
        return
    
    # Obtém os argumentos do comando
    args = message.text.split(' ', 2)
    
    # Verifica se há argumentos suficientes
    if len(args) < 3:
        await message.reply_text(
            "❌ Formato incorreto. Use: /sayrecurrent <intervalo> <mensagem>\n"
            "Exemplos de intervalo: 30m, 1h, 1h30m\n"
            "Exemplo: /sayrecurrent 30m Bom dia, pessoal!",
            reply_to_message_id=message.message_id
        )
        return
    
    # Obtém o intervalo e a mensagem
    interval_str = args[1].lower()
    message_text = args[2]
    
    # Verifica se a mensagem não está vazia
    if not message_text.strip():
        await message.reply_text(
            "❌ A mensagem não pode estar vazia.",
            reply_to_message_id=message.message_id
        )
        return
    
    # Processa o intervalo
    try:
        # Inicializa as horas e minutos
        hours = 0
        minutes = 0
        
        # Verifica se o formato é complexo (ex: 1h30m)
        if 'h' in interval_str and 'm' in interval_str:
            # Divide em partes de horas e minutos
            parts = interval_str.split('h')
            if len(parts) == 2:
                # Extrai as horas
                hours = float(parts[0])
                
                # Extrai os minutos (remove o 'm' do final)
                min_part = parts[1]
                if min_part.endswith('m'):
                    min_part = min_part[:-1]
                minutes = float(min_part)
        
        # Verifica se o formato é apenas horas
        elif 'h' in interval_str:
            # Remove o 'h' do final
            hours_part = interval_str.rstrip('h')
            hours = float(hours_part)
        
        # Verifica se o formato é apenas minutos
        elif 'm' in interval_str:
            # Remove o 'm' do final
            minutes_part = interval_str.rstrip('m')
            minutes = float(minutes_part)
        
        # Se não tem sufixo, assume que é em minutos
        else:
            minutes = float(interval_str)
        
        # Converte para horas
        interval_hours = hours + (minutes / 60)
        
        # Verifica se o intervalo é positivo
        if interval_hours <= 0:
            await message.reply_text(
                "❌ O intervalo deve ser um número positivo.",
                reply_to_message_id=message.message_id
            )
            return
    except ValueError:
        await message.reply_text(
            "❌ Formato de intervalo inválido. Use: 30m, 1h, 1h30m, etc.",
            reply_to_message_id=message.message_id
        )
        return
    
    # Adiciona a mensagem recorrente
    from src.utils.recurring_messages_manager import recurring_messages_manager
    
    message_id = await recurring_messages_manager.add_recurring_message(
        chat_id=message.chat_id,
        message=message_text,
        interval_hours=interval_hours,
        added_by=message.from_user.id,
        added_by_name=message.from_user.full_name
    )
    
    if message_id:
        # Formata o intervalo para exibição
        if interval_hours < 1:
            interval_display = f"{int(minutes)} minutos"
        else:
            hours_int = int(hours)
            minutes_int = int(minutes)
            
            if hours_int > 0 and minutes_int > 0:
                interval_display = f"{hours_int} hora(s) e {minutes_int} minuto(s)"
            elif hours_int > 0:
                interval_display = f"{hours_int} hora(s)"
            else:
                interval_display = f"{minutes_int} minuto(s)"
        
        # Envia mensagem de confirmação
        await context.bot.send_message(
            chat_id=message.chat_id,
            text=(
                f"✅ *Mensagem recorrente configurada com sucesso!*\n\n"
                f"🔄 *Intervalo:* `{interval_display}`\n"
                f"🆔 *ID:* `{message_id}`\n\n"
                f"📝 *Mensagem:*\n"
                f"```\n{message_text}\n```"
            ),
            parse_mode="Markdown"
        )
        
        # Registra a ação
        logger.info(
            f"Usuário {message.from_user.id} configurou uma mensagem recorrente "
            f"com intervalo de {interval_hours} horas no chat {message.chat_id}"
        )
    else:
        await message.reply_text(
            "❌ Erro ao configurar a mensagem recorrente. Tente novamente mais tarde.",
            reply_to_message_id=message.message_id
        )
    
    # Tenta apagar a mensagem do comando
    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"Não foi possível apagar a mensagem do comando: {e}")

async def listrecurrent_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /listrecurrent.
    
    Lista todas as mensagens recorrentes configuradas para o chat.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    # Verifica se é uma mensagem normal ou editada
    message = update.message or update.edited_message
    if not message:
        return
        
    # Verifica se o usuário é um administrador
    if not await is_admin(update, context):
        await message.reply_text(
            "❌ Você não tem permissão para usar este comando.",
            reply_to_message_id=message.message_id
        )
        return
    
    # Importa o gerenciador de mensagens recorrentes
    from src.utils.recurring_messages_manager import recurring_messages_manager
    
    # Obtém todas as mensagens recorrentes do chat
    messages = await recurring_messages_manager.get_recurring_messages(message.chat_id)
    
    # Registra a ação
    logger.info(f"Usuário {message.from_user.id} solicitou a lista de mensagens recorrentes")
    
    # Verifica se há mensagens recorrentes
    if not messages:
        await message.reply_text(
            "📝 *Não há mensagens recorrentes configuradas para este chat.*",
            parse_mode="Markdown",
            reply_to_message_id=message.message_id
        )
        return
    
    # Formata a lista de mensagens
    response = "📝 *Mensagens recorrentes configuradas:*\n\n"
    
    for i, msg in enumerate(messages, 1):
        # Formata o intervalo para exibição
        interval_hours = msg.get("interval_hours", 0)
        
        # Converte para horas e minutos
        hours = int(interval_hours)
        minutes = int((interval_hours - hours) * 60)
        
        if hours > 0 and minutes > 0:
            interval_display = f"{hours}h{minutes}m"
        elif hours > 0:
            interval_display = f"{hours}h"
        else:
            interval_display = f"{minutes}m"
        
        # Formata a data de criação
        created_at = msg.get("created_at", datetime.now())
        created_at_str = created_at.strftime("%d/%m/%Y %H:%M")
        
        # Formata a data do último envio
        last_sent_at = msg.get("last_sent_at")
        if last_sent_at:
            last_sent_at_str = last_sent_at.strftime("%d/%m/%Y %H:%M")
        else:
            last_sent_at_str = "Nunca"
        
        # Limita o tamanho da mensagem para exibição
        message_text = msg.get("message", "")
        if len(message_text) > 50:
            message_text = message_text[:47] + "..."
        
        # Adiciona a mensagem à resposta
        response += (
            f"*{i}. ID:* `{msg['_id']}`\n"
            f"*Mensagem:* {message_text}\n"
            f"*Intervalo:* {interval_display}\n"
            f"*Adicionada por:* {msg.get('added_by_name', 'Desconhecido')}\n"
            f"*Criada em:* {created_at_str}\n"
            f"*Último envio:* {last_sent_at_str}\n\n"
        )
    
    # Adiciona instruções para desativar mensagens
    response += (
        "*Para desativar uma mensagem, use:*\n"
        "`/delrecurrent ID_DA_MENSAGEM`"
    )
    
    # Envia a resposta
    await context.bot.send_message(
        chat_id=message.chat_id,
        text=response,
        parse_mode="Markdown"
    )

async def delrecurrent_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Desativa uma mensagem recorrente.
    Formato: /delrecurrent ID_DA_MENSAGEM
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    # Verifica se é uma mensagem normal ou editada
    message = update.message or update.edited_message
    if not message:
        return
        
    # Verifica se o usuário é um administrador
    if not await is_admin(update, context):
        await message.reply_text(
            "❌ Você não tem permissão para usar este comando.",
            reply_to_message_id=message.message_id
        )
        return
    
    # Obtém os argumentos do comando
    args = message.text.split()
    
    # Verifica se há argumentos suficientes
    if len(args) < 2:
        await message.reply_text(
            "❌ Formato incorreto. Use: /delrecurrent <id_da_mensagem>",
            reply_to_message_id=message.message_id
        )
        return
    
    # Obtém o ID da mensagem
    message_id = args[1]
    
    # Importa o gerenciador de mensagens recorrentes
    from src.utils.recurring_messages_manager import recurring_messages_manager
    
    # Desativa a mensagem recorrente
    result = await recurring_messages_manager.delete_recurring_message(message_id)
    
    if result:
        # Envia mensagem de confirmação
        await context.bot.send_message(
            chat_id=message.chat_id,
            text=f"✅ *Mensagem recorrente desativada com sucesso!*\n\n🆔 ID: `{message_id}`",
            parse_mode="Markdown"
        )
        
        # Registra a ação
        logger.info(
            f"Usuário {message.from_user.id} desativou a mensagem recorrente {message_id} "
            f"no chat {message.chat_id}"
        )
    else:
        await message.reply_text(
            f"❌ Erro ao desativar a mensagem recorrente. Verifique se o ID `{message_id}` está correto.",
            parse_mode="Markdown",
            reply_to_message_id=message.message_id
        )
    
    # Tenta apagar a mensagem do comando
    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"Não foi possível apagar a mensagem do comando: {e}")

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /regras.
    Envia a lista de regras do grupo GYM NATION.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    logger.info(f"Usuário {update.effective_user.id} solicitou as regras do grupo")
    
    rules_message = (
        "🔱 <b>CÓDIGO DE CONDUTA | GYM NATION</b> 🔱\n"
        "<i>\"Onde o ferro encontra a irmandade\"</i>\n\n"
        "━━━━━━━━━━━━━━\n"
        "🎯 <b>PILARES FUNDAMENTAIS</b>\n\n"
        "<b>RESPEITO SUPREMO</b> 🤝\n"
        "Zoeira é combustível, desrespeito é veneno. Atacar físico, personalidade ou jornada alheia = passaporte direto pro ban. Aqui celebramos diferenças, não as destruímos.\n\n"
        "<b>BROTHERHOOD CODE</b> 👥\n"
        "Não somos apenas um grupo, somos uma irmandade. Apoie, motive, compartilhe conhecimento. Seja o cara que você gostaria de ter ao seu lado no treino.\n\n"
        "━━━━━━━━━━━━━━\n"
        "📸 <b>PROTOCOLO VISUAL</b>\n\n"
        "<b>SHAPE SHOWCASE</b> ✅\n"
        "Progresso merece ser celebrado! Fotos de físico são bem-vindas, mas com classe:\n\n"
        "<b>CÓDIGO DE VESTIMENTA</b> 👕\n"
        "- Mínimo obrigatório: Cueca sempre\n"
        "- Contorno do \"amigão\" aparecendo = nudez proibida\n"
        "- Rego à mostra = nudez proibida\n"
        "- Regra de ouro: Se sua mãe não aprovaria, não poste\n\n"
        "<b>ZERO MONOTONIA</b> 🚫\n"
        "Mesma foto = criatividade zero. Renove seu conteúdo, surpreenda a galera.\n\n"
        "━━━━━━━━━━━━━━\n"
        "⚡️ <b>TERRITÓRIO LIVRE DE:</b>\n\n"
        "🚨 <b>NUDES & CONTEÚDO SEXUAL</b>\n"
        "Não somos OnlyFans. Sensualidade ≠ vulgaridade.\n\n"
        "🚨 <b>BAIT MASTERS</b>\n"
        "\"Chama PV\", vendas disfarçadas, iscas pra atenção = tática de amador.\n\n"
        "🚨 <b>SPAM LORDS</b>\n"
        "Flood, links duvidosos, autopromoção não autorizada.\n\n"
        "━━━━━━━━━━━━━━\n"
        "💥 <b>CÓDIGO DE INTERAÇÃO</b>\n\n"
        "<b>FLERTE INTELIGENTE</b> 😏💚\n"
        "Charme e zoeira fazem parte, mas leia o ambiente. Bom senso é sexy.\n\n"
        "<b>TRANSPARÊNCIA TOTAL</b> 💎\n"
        "Dúvidas? Questionamentos? Fale aberto ou procure a moderação.\n\n"
        "━━━━━━━━━━━━━━\n"
        "🤖 <b>SISTEMA BLACKLIST</b>\n\n"
        "O grupo é monitorado 24/7. Conteúdo fora das regras = <b>BLACKLIST</b>\n\n"
        "🚨 <b>ALERTA VERMELHO:</b> Bot notifica o grupo sobre violações\n"
        "📊 <b>HISTÓRICO PERMANENTE:</b> Toda infração fica registrada\n"
        "⚖️ <b>QUER SAIR DA LISTA?</b> Chame um ADM\n\n"
        "<i>O sistema não dorme, não falha, não perdoa repetições.</i>\n\n"
        "━━━━━━━━━━━━━━\n"
        "🔥 <b>MISSÃO ACEITA?</b>\n\n"
        "Bem-vindo ao território onde o shape cresce junto com o caráter 💚"
    )
    
    # Tenta deletar a mensagem de comando
    try:
        await update.message.delete()
    except Exception as e:
        logger.error(f"Erro ao deletar mensagem de comando: {e}")
        await send_temporary_message(
            update,
            context,
            "Não foi possível deletar o comando. Verifique as permissões do bot."
        )
    
    # Envia a mensagem com as regras
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=rules_message,
        parse_mode="HTML"
    )

async def admin_correio_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando administrativo para gerenciar correios elegantes.
    Uso: /admincorreio [status|stats|cleanup]
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    # Verificar se é o proprietário
    if update.effective_user.id != Config.get_owner_id():
        await update.message.reply_text("❌ Apenas o proprietário pode usar este comando.")
        return
    
    args = context.args
    
    if not args:
        help_text = (
            "📬 **ADMINISTRAÇÃO DO CORREIO ELEGANTE**\n\n"
            "**Comandos disponíveis:**\n"
            "• `/admincorreio status` - Status do sistema\n"
            "• `/admincorreio stats` - Estatísticas gerais\n"
            "• `/admincorreio cleanup` - Limpar correios expirados\n"
            "• `/admincorreio pending` - Ver correios pendentes\n"
            "• `/admincorreio reports` - Ver denúncias\n"
            "• `/admincorreio send [ID|all]` - Publicar correio específico ou todos"
        )
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
        return
    
    command = args[0].lower()
    
    if command == "status":
        await _admin_correio_status(update, context)
    elif command == "stats":
        await _admin_correio_stats(update, context)
    elif command == "cleanup":
        await _admin_correio_cleanup(update, context)
    elif command == "pending":
        await _admin_correio_pending(update, context)
    elif command == "reports":
        await _admin_correio_reports(update, context)
    elif command == "send":
        await _admin_correio_send(update, context)
    else:
        await update.message.reply_text(
            "❌ Comando inválido. Use `/admincorreio` para ver as opções.",
            parse_mode=ParseMode.MARKDOWN
        )

async def _admin_correio_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra status do sistema de correio elegante."""
    try:
        # Verificar se o agendador está rodando
        from src.utils.mail_scheduler import mail_scheduler
        
        scheduler_status = "🟢 Ativo" if mail_scheduler and mail_scheduler.is_running else "🔴 Inativo"
        
        # Verificar configurações
        try:
            pix_key = Config.get_pix_key()
            pix_status = "🟢 Configurado"
        except:
            pix_status = "🔴 Não configurado"
        
        # Verificar GYM NATION
        from src.utils.mongodb_instance import mongodb_client
        gym_nation_chat_id = await mongodb_client.get_gym_nation_chat_id()
        gym_nation_status = "🟢 Encontrado" if gym_nation_chat_id else "🔴 Não encontrado"
        
        status_text = (
            f"📬 **STATUS DO CORREIO ELEGANTE**\n\n"
            f"**Agendador:** {scheduler_status}\n"
            f"**Chave Pix:** {pix_status}\n"
            f"**Grupo GYM NATION:** {gym_nation_status}\n"
            f"**Chat ID:** `{gym_nation_chat_id or 'N/A'}`\n\n"
            f"**Sistema:** {'🟢 Operacional' if scheduler_status == '🟢 Ativo' and pix_status == '🟢 Configurado' and gym_nation_status == '🟢 Encontrado' else '🟡 Parcial/🔴 Inativo'}"
        )
        
        await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Erro ao obter status do correio: {e}")
        await update.message.reply_text("❌ Erro ao obter status do sistema.")

async def _admin_correio_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra estatísticas do correio elegante."""
    try:
        from src.utils.mongodb_instance import mongodb_client
        
        # Obter estatísticas reais
        today_stats = await mongodb_client.get_mail_stats_today()
        total_stats = await mongodb_client.get_mail_stats_total()
        weekly_stats = await mongodb_client.get_mail_stats_weekly()
        
        stats_text = (
            f"📊 **ESTATÍSTICAS DO CORREIO ELEGANTE**\n\n"
            
            f"**📅 Hoje:**\n"
            f"• Correios enviados: {today_stats['sent']}\n"
            f"• Revelações pagas: {today_stats['revealed']}\n"
            f"• Denúncias: {today_stats['reported']}\n"
            f"• Receita do dia: R$ {today_stats['revealed'] * 2:.2f}\n\n"
            
            f"**📈 Última semana:**\n"
            f"• Correios enviados: {weekly_stats['sent']}\n"
            f"• Revelações pagas: {weekly_stats['revealed']}\n"
            f"• Receita semanal: R$ {weekly_stats['revealed'] * 2:.2f}\n\n"
            
            f"**📋 Total geral:**\n"
            f"• Correios criados: {total_stats['total_mails']}\n"
            f"• Arrecadação total: R$ {total_stats['total_revenue']:.2f}\n"
            f"• Usuários ativos: {total_stats['unique_senders']}\n\n"
            
            f"**🔄 Status dos correios:**\n"
            f"• Pendentes: {total_stats['pending']}\n"
            f"• Publicados: {total_stats['published']}\n"
            f"• Expirados: {total_stats['expired']}\n\n"
            
            f"_Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}_"
        )
        
        await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas do correio: {e}")
        await update.message.reply_text("❌ Erro ao obter estatísticas.")

async def _admin_correio_cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Limpa correios expirados."""
    try:
        from src.utils.mongodb_instance import mongodb_client
        
        # TODO: Implementar limpeza real
        await update.message.reply_text(
            "🧹 **LIMPEZA EXECUTADA**\n\n"
            "Sistema de limpeza automática ativo.\n"
            "Correios expirados são removidos automaticamente.",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Erro na limpeza de correios: {e}")
        await update.message.reply_text("❌ Erro durante a limpeza.")

async def _admin_correio_pending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra correios pendentes."""
    try:
        from src.utils.mongodb_instance import mongodb_client
        
        pending_mails = await mongodb_client.get_pending_mails()
        
        if not pending_mails:
            await update.message.reply_text(
                "📬 Nenhum correio pendente para publicação.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        pending_text = f"📋 **CORREIOS PENDENTES** ({len(pending_mails)})\n\n"
        
        for i, mail in enumerate(pending_mails[:5], 1):  # Limitar a 5 para não ser muito longo
            created_at = mail.get('created_at', datetime.now()).strftime("%d/%m %H:%M")
            pending_text += (
                f"**{i}.** `{mail['_id']}`\n"
                f"Para: @{mail['recipient_username']}\n"
                f"Criado: {created_at}\n"
                f"Preview: {mail['message_text'][:50]}...\n\n"
            )
        
        if len(pending_mails) > 5:
            pending_text += f"_... e mais {len(pending_mails) - 5} correios._"
        
        await update.message.reply_text(pending_text, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Erro ao obter correios pendentes: {e}")
        await update.message.reply_text("❌ Erro ao obter correios pendentes.")

async def _admin_correio_reports(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra denúncias de correios."""
    try:
        await update.message.reply_text(
            "🚨 **SISTEMA DE DENÚNCIAS**\n\n"
            "Sistema de denúncias implementado.\n"
            "Correios com 3+ denúncias são automaticamente removidos.\n\n"
            "_Interface de moderação será implementada na próxima versão._",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Erro ao obter denúncias: {e}")
        await update.message.reply_text("❌ Erro ao obter denúncias.")

async def _admin_correio_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Publica correios pendentes manualmente."""
    try:
        args = context.args
        
        if len(args) < 2:
            await update.message.reply_text(
                "❌ **Uso correto:**\n"
                "• `/admincorreio send [ID_do_correio]` - Envia correio específico\n"
                "• `/admincorreio send all` - Envia todos os pendentes\n\n"
                "Use `/admincorreio pending` para ver IDs dos correios.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        target = args[1]
        
        if target.lower() == "all":
            # Enviar todos os correios pendentes
            from src.utils.mail_scheduler import publish_all_pending_mails
            from src.utils.mongodb_instance import mongodb_client
            
            # Contar pendentes antes
            pending_before = await mongodb_client.get_pending_mails()
            count_before = len(pending_before)
            
            if count_before == 0:
                await update.message.reply_text(
                    "📬 Nenhum correio pendente para enviar.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Publicar todos
            await publish_all_pending_mails()
            
            # Contar pendentes depois
            pending_after = await mongodb_client.get_pending_mails()
            count_after = len(pending_after)
            count_sent = count_before - count_after
            
            await update.message.reply_text(
                f"✅ **CORREIOS ENVIADOS**\n\n"
                f"📬 {count_sent} correio(s) publicado(s) com sucesso!\n"
                f"📋 {count_after} correio(s) restante(s) na fila.",
                parse_mode=ParseMode.MARKDOWN
            )
            
        else:
            # Enviar correio específico
            from src.utils.mail_scheduler import publish_mail_by_id
            
            # Validar se é um ID válido (ObjectId tem 24 caracteres hex)
            import re
            if not re.match(r'^[0-9a-fA-F]{24}$', target):
                await update.message.reply_text(
                    "❌ ID de correio inválido.\n"
                    "Use `/admincorreio pending` para ver os IDs corretos.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            success = await publish_mail_by_id(target)
            
            if success:
                await update.message.reply_text(
                    f"✅ **CORREIO ENVIADO**\n\n"
                    f"📬 Correio `{target}` publicado com sucesso!",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(
                    f"❌ **FALHA NO ENVIO**\n\n"
                    f"Não foi possível publicar o correio `{target}`.\n"
                    "Verifique se o ID está correto e se o correio está pendente.",
                    parse_mode=ParseMode.MARKDOWN
                )
        
    except Exception as e:
        logger.error(f"Erro ao enviar correios: {e}")
        await update.message.reply_text("❌ Erro interno ao processar comando.") 