"""
Handlers para os comandos de check-in.
"""
import logging
from typing import Optional, Dict, Any
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.error import TimedOut
from src.utils.mongodb_instance import mongodb_client
from src.bot.handlers import is_admin, send_temporary_message, delete_message_after
import asyncio
from datetime import datetime

# Configuração de logging
logger = logging.getLogger(__name__)

async def checkin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /checkin.
    Define uma mensagem como âncora de check-in.
    
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
    
    # Verifica se o comando foi usado como resposta a outra mensagem
    if not update.message.reply_to_message:
        await send_temporary_message(
            update, 
            context, 
            "Por favor, use este comando respondendo à mensagem que deseja definir como check-in."
        )
        return
    
    # Obtém os IDs do chat e da mensagem
    chat_id = update.effective_chat.id
    message_id = update.message.reply_to_message.message_id
    
    # Define a mensagem como âncora de check-in
    success = await mongodb_client.set_checkin_anchor(chat_id, message_id)
    
    if success:
        # Tenta deletar a mensagem de comando
        try:
            await update.message.delete()
        except Exception as e:
            logger.error(f"Erro ao deletar mensagem de comando: {e}")
        
        # Envia mensagem de confirmação
        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Check-in ativado! Os membros podem responder à mensagem marcada para registrar seu check-in diário.",
            reply_to_message_id=message_id
        )
    else:
        await send_temporary_message(
            update, 
            context, 
            "❌ Erro ao ativar o check-in. Por favor, tente novamente."
        )

async def endcheckin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /endcheckin.
    Desativa o check-in atual.
    
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
    
    # Obtém o ID do chat
    chat_id = update.effective_chat.id
    
    # Obtém o check-in ativo antes de desativá-lo
    active_checkin = await mongodb_client.get_active_checkin(chat_id)
    
    if not active_checkin:
        await send_temporary_message(
            update, 
            context, 
            "Não há check-in ativo para desativar."
        )
        return
    
    # Obtém a contagem de check-ins para a âncora ativa
    anchor_id = active_checkin["_id"]
    checkin_count = await mongodb_client.get_anchor_checkin_count(chat_id, anchor_id)
    
    # Desativa o check-in atual
    success = await mongodb_client.end_checkin(chat_id)
    
    if success:
        # Tenta deletar a mensagem de comando
        try:
            await update.message.delete()
        except Exception as e:
            logger.error(f"Erro ao deletar mensagem de comando: {e}")
        
        # Envia mensagem de confirmação com a contagem de check-ins
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ Check-in antigo finalizado! Foram registrados {checkin_count} check-ins."
        )
    else:
        await send_temporary_message(
            update, 
            context, 
            "❌ Erro ao desativar o check-in. Por favor, tente novamente."
        )

async def handle_checkin_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para respostas a mensagens de check-in.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    # Se a mensagem não for uma resposta, retorna
    if not update.message.reply_to_message:
        return
    
    # Verifica se a mensagem contém mídia (foto, vídeo, GIF, etc.)
    if not (update.message.photo or update.message.video or 
            update.message.animation or 
            (update.message.document and update.message.document.mime_type and 
             update.message.document.mime_type.startswith('image/'))):
        logger.debug(f"Mensagem de check-in sem mídia ignorada: {update.message.message_id}")
        return
    
    # Obtém o chat_id e o replied_message_id
    chat_id = update.effective_chat.id
    replied_message_id = update.message.reply_to_message.message_id
    
    # Obtém o check-in ativo
    active_checkin = await mongodb_client.get_active_checkin(chat_id)
    
    # Se não houver check-in ativo, retorna
    if not active_checkin:
        return
    
    # Se a mensagem não for uma resposta à mensagem âncora de check-in, retorna
    if active_checkin["message_id"] != replied_message_id:
        logger.debug(f"Ignorando mensagem: resposta não é para a âncora de check-in. Âncora: {active_checkin['message_id']}, Resposta para: {replied_message_id}")
        return
    
    logger.info(f"Check-in detectado de {update.effective_user.full_name} ({update.effective_user.id}) no chat {chat_id}")
    
    # Obtém informações do usuário
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name or "Usuário"
    username = update.effective_user.username  # Captura o username
    
    # Registra o check-in do usuário
    checkin_count = await mongodb_client.record_user_checkin(chat_id, user_id, user_name, username)
    
    # Se o usuário já fez check-in para esta âncora, retorna None
    if checkin_count is None:
        logger.debug(f"Usuário {user_id} já fez check-in para esta âncora")
        # Use username para exibição se disponível
        display_name = f"@{username}" if username else user_name
        await send_temporary_message(
            update, 
            context, 
            f"Você já fez seu check-in para esta mensagem, {display_name}! 😉"
        )
        return
    
    logger.info(f"Check-in registrado com sucesso. Total de check-ins do usuário: {checkin_count}")
    
    # Adiciona reação de fogo à mensagem do usuário
    try:
        await context.bot.set_message_reaction(
            chat_id=chat_id,
            message_id=update.message.message_id,
            reaction=["🔥"]
        )
    except Exception as e:
        logger.error(f"Erro ao adicionar reação à mensagem: {e}")
    
    # Gera uma mensagem de resposta personalizada
    # Use username para exibição se disponível
    display_name = f"@{username}" if username else user_name
    response_message = generate_checkin_response(display_name, checkin_count)
    
    # Responde ao usuário com uma mensagem permanente (sem usar send_temporary_message)
    await update.message.reply_text(response_message)

async def checkinscore_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /checkinscore.
    Envia um scoreboard com os check-ins dos usuários.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    # Obtém o scoreboard de check-ins
    scoreboard = await mongodb_client.get_checkin_scoreboard(update.effective_chat.id)
    
    # Tenta deletar a mensagem de comando
    try:
        await update.message.delete()
    except Exception as e:
        logger.error(f"Erro ao deletar mensagem de comando: {e}")
    
    if not scoreboard or len(scoreboard) == 0:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Ainda não há check-ins registrados neste chat. 😢"
        )
        return
    
    # Obtém estatísticas adicionais
    total_participants = await mongodb_client.get_total_checkin_participants(update.effective_chat.id)
    first_checkin_date = await mongodb_client.get_first_checkin_date(update.effective_chat.id)
    
    # Calcula há quantos dias o primeiro check-in foi registrado
    days_since_first_checkin = None
    if first_checkin_date:
        days_since_first_checkin = (datetime.now() - first_checkin_date).days
    
    # Limita o scoreboard a no máximo 10 usuários
    scoreboard = scoreboard[:10]
    
    # Cria a mensagem do scoreboard
    message = "🏆 *GYM NATION CHECK-INS* 🏆\n\n"
    
    # Agrupa usuários com a mesma contagem
    grouped_scoreboard = {}
    for i, user in enumerate(scoreboard):
        count = user['count']
        if count not in grouped_scoreboard:
            grouped_scoreboard[count] = []
        grouped_scoreboard[count].append(user)
    
    # Adiciona usuários ao scoreboard
    current_position = 1
    for count, users in sorted(grouped_scoreboard.items(), key=lambda x: x[0], reverse=True):
        # Atribui medalha com base na posição
        if current_position == 1:
            medal = "🥇 "
        elif current_position == 2:
            medal = "🥈 "
        elif current_position == 3:
            medal = "🥉 "
        else:
            medal = "▫️ "
        
        # Processa usuários empatados
        if len(users) > 1:
            user_list = []
            for user in users:
                # SEMPRE usa o username com @ se disponível, caso contrário usa o nome
                display_name = f"@{user['username']}" if user['username'] else user['user_name']
                user_list.append(display_name)
            
            # Formata a lista de usuários empatados
            users_text = " e ".join([", ".join(user_list[:-1]), user_list[-1]]) if len(user_list) > 1 else user_list[0]
            message += f"{medal}*{current_position}.* {users_text}: *{count}* check-ins\n"
        else:
            user = users[0]
            # SEMPRE usa o username com @ se disponível, caso contrário usa o nome
            display_name = f"@{user['username']}" if user['username'] else user['user_name']
            message += f"{medal}*{current_position}.* {display_name}: *{count}* check-ins\n"
        
        # Incrementa a posição pelo número de usuários na posição atual
        current_position += len(users)
    
    # Adiciona estatísticas adicionais
    message += "\n💪 Continue mantendo a consistência! 🔥\n"
    
    if total_participants and days_since_first_checkin is not None:
        message += f"\n📊 *Estatísticas:*\n"
        message += f"• *{total_participants}* pessoas já participaram dos check-ins\n"
        message += f"• Primeiro check-in registrado há *{days_since_first_checkin}* dias\n"
    
    # Envia a mensagem
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        parse_mode=ParseMode.MARKDOWN
    )

def generate_checkin_response(user_name: str, checkin_count: int) -> str:
    """
    Gera uma mensagem de resposta personalizada com base no número de check-ins do usuário.
    
    Args:
        user_name (str): Nome do usuário.
        checkin_count (int): Número de check-ins do usuário.
        
    Returns:
        str: Mensagem personalizada.
    """
    # Mensagens personalizadas com base no número de check-ins
    if checkin_count == 1:
        return f"Primeiro check-in de {user_name}! 🎉 Bem-vindo ao GYM NATION!"
    elif checkin_count == 3:
        return f"Terceiro check-in de {user_name}! 🔥 Você está criando consistência!"
    elif checkin_count == 5:
        return f"Quinto check-in de {user_name}! 💪 Você está no caminho certo!"
    elif checkin_count == 10:
        return f"Uau! {user_name} já está no check-in #10! Sua consistência é inspiradora! 🔥"
    elif checkin_count == 30:
        return f"Um mês de check-ins! {user_name} está construindo um hábito incrível! 🏆"
    elif checkin_count == 100:
        return f"INACREDITÁVEL! {user_name} alcançou 100 check-ins! Você é uma lenda! 👑"
    elif checkin_count % 50 == 0:
        return f"WOW! {user_name} atingiu {checkin_count} check-ins! Que dedicação impressionante! 🌟"
    elif checkin_count % 25 == 0:
        return f"Parabéns, {user_name}! Você alcançou {checkin_count} check-ins! Continue assim! 🚀"
    elif checkin_count % 10 == 0:
        return f"Mais um marco! {user_name} completou {checkin_count} check-ins! 💯"
    else:
        # Mensagens aleatórias para outros números de check-in
        messages = [
            f"Check-in #{checkin_count} registrado para {user_name}! 💪",
            f"{user_name} está em chamas! 🔥 Check-in #{checkin_count}!",
            f"Mais um dia, mais um check-in para {user_name}! #{checkin_count} 🏋️",
            f"A consistência de {user_name} é admirável! Check-in #{checkin_count} 👏",
            f"{user_name} não para! Check-in #{checkin_count} registrado! 🚀"
        ]
        return messages[checkin_count % len(messages)]

async def confirmcheckin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando para confirmar manualmente um check-in que não foi processado automaticamente.
    Deve ser usado por um administrador respondendo à mensagem de um usuário.
    
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
    
    # Verifica se o comando foi usado como resposta a outra mensagem
    if not update.message.reply_to_message:
        await send_temporary_message(
            update, 
            context, 
            "Por favor, use este comando respondendo à mensagem do usuário para confirmar o check-in."
        )
        return
    
    # Obtém os IDs do chat e da mensagem
    chat_id = update.effective_chat.id
    target_message = update.message.reply_to_message
    target_user_id = target_message.from_user.id
    target_user_name = target_message.from_user.full_name or f"@{target_message.from_user.username}" or "Usuário"
    target_username = target_message.from_user.username  # Captura o username
    
    # Verifica se há um check-in ativo
    try:
        active_checkin = await mongodb_client.get_active_checkin(chat_id)
        
        if not active_checkin:
            await send_temporary_message(
                update, 
                context, 
                "Não há check-in ativo neste momento. Use /checkin para ativar um."
            )
            return
        
        # Registra o check-in do usuário
        checkin_count = await mongodb_client.record_user_checkin(chat_id, target_user_id, target_user_name, target_username)
        
        # Se o usuário já fez check-in, envia mensagem e retorna
        if checkin_count is None:
            # Armazena a mensagem temporária antes de deletar o comando
            temp_message = await context.bot.send_message(
                chat_id=chat_id,
                text=f"{target_user_name} já fez check-in para a âncora atual. 😉",
                reply_to_message_id=target_message.message_id
            )
            
            # Agenda a exclusão da mensagem temporária
            asyncio.create_task(delete_message_after(temp_message, 20))
            
            # Tenta deletar a mensagem de comando
            try:
                await update.message.delete()
            except Exception as e:
                logger.error(f"Erro ao deletar mensagem de comando: {e}")
                
            return
        
        logger.info(f"Check-in manual registrado para {target_user_name} ({target_user_id}). Total: {checkin_count}")
        
        # Adiciona uma reação à mensagem do usuário para confirmar o check-in
        try:
            await context.bot.set_message_reaction(
                chat_id=chat_id,
                message_id=target_message.message_id,
                reaction=["🔥"]
            )
            
            # Gera e envia uma mensagem de confirmação personalizada
            response_message = generate_checkin_response(target_user_name, checkin_count)
            await context.bot.send_message(
                chat_id=chat_id,
                text=response_message,
                reply_to_message_id=target_message.message_id
            )
            
            # Tenta deletar a mensagem de comando DEPOIS de enviar a resposta
            try:
                await update.message.delete()
            except Exception as e:
                logger.error(f"Erro ao deletar mensagem de comando: {e}")
                
        except Exception as reaction_error:
            logger.error(f"Erro ao adicionar reação à mensagem: {reaction_error}")
            # Apenas envia mensagem de confirmação se houver erro na reação
            if not isinstance(reaction_error, TimedOut):
                # Gera e envia uma mensagem de confirmação personalizada
                response_message = generate_checkin_response(target_user_name, checkin_count)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=response_message,
                    reply_to_message_id=target_message.message_id
                )
                
                # Tenta deletar a mensagem de comando DEPOIS de enviar a resposta
                try:
                    await update.message.delete()
                except Exception as e:
                    logger.error(f"Erro ao deletar mensagem de comando: {e}")
                
    except Exception as db_error:
        logger.error(f"Erro ao registrar check-in no banco de dados: {db_error}")
        
        # Envia mensagem de erro antes de tentar deletar o comando
        temp_message = await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Erro ao registrar check-in. Por favor, tente novamente.",
            reply_to_message_id=target_message.message_id
        )
        
        # Agenda a exclusão da mensagem temporária
        asyncio.create_task(delete_message_after(temp_message, 20))
        
        # Tenta deletar a mensagem de comando
        try:
            await update.message.delete()
        except Exception as e:
            logger.error(f"Erro ao deletar mensagem de comando: {e}") 