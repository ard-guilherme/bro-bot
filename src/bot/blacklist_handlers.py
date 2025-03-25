"""
Handlers para os comandos de blacklist.
"""
import logging
from typing import Optional, List, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReactionTypeEmoji
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ReactionEmoji
from telegram.error import BadRequest, TimedOut
from datetime import datetime
import asyncio
from src.utils.mongodb_instance import mongodb_client
from src.bot.handlers import is_admin, send_temporary_message, delete_message_after

# Configuração de logging
logger = logging.getLogger(__name__)

async def addblacklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /addblacklist.
    Adiciona uma mensagem à blacklist, marcando-a como inapropriada.
    
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
            "Por favor, use este comando respondendo à mensagem que deseja adicionar à blacklist."
        )
        return
    
    # Obtém informações da mensagem e do usuário
    chat_id = update.effective_chat.id
    message = update.message.reply_to_message
    message_id = message.message_id
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    username = message.from_user.username
    message_text = message.text or message.caption or ""
    
    # Informações do admin que está adicionando à blacklist
    admin_id = update.effective_user.id
    admin_name = update.effective_user.full_name
    
    # Adiciona a mensagem à blacklist
    doc_id = await mongodb_client.add_to_blacklist(
        chat_id=chat_id,
        message_id=message_id,
        user_id=user_id,
        user_name=user_name,
        username=username,
        message_text=message_text,
        added_by=admin_id,
        added_by_name=admin_name
    )
    
    if doc_id:
        logger.info(f"Mensagem {message_id} de {user_name} ({user_id}) adicionada à blacklist por {admin_name} ({admin_id})")
        
        # Adiciona reação de X à mensagem
        try:
            # Usando o objeto ReactionTypeEmoji correto
            reaction = ReactionTypeEmoji(emoji="👎")
            await context.bot.set_message_reaction(
                chat_id=chat_id,
                message_id=message_id,
                reaction=[reaction]
            )
        except Exception as e:
            logger.error(f"Erro ao adicionar reação à mensagem: {e}")
        
        # Não enviamos mais mensagem de confirmação
        
        try:
            await update.message.delete()
        except Exception as e:
            logger.error(f"Erro ao deletar mensagem de comando: {e}")
    else:
        await send_temporary_message(
            update, 
            context, 
            "❌ Erro ao adicionar mensagem à blacklist. Por favor, tente novamente."
        )

async def blacklist_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para os botões da blacklist.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    query = update.callback_query
    
    # Verifica se é um admin
    if not await is_admin(update, context):
        await query.answer("Apenas administradores podem remover itens da blacklist")
        return
    
    # Extrai o ID do item
    item_id = query.data.split("_")[1]
    
    # Remove o item
    success = await mongodb_client.remove_from_blacklist(item_id)
    
    if success:
        # Atualiza a mensagem removendo o item
        await query.answer("Item removido da blacklist")
        # Atualiza a lista completa
        await blacklist_command(update, context)
    else:
        await query.answer("Erro ao remover item da blacklist")

async def blacklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /blacklist.
    Lista as mensagens na blacklist de um chat.
    
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
    
    # Verifica se foi especificado um nome de grupo
    chat_id = update.effective_chat.id
    blacklist = []
    
    # Se foram passados argumentos, considera como nome do grupo
    if context.args and len(context.args) > 0:
        group_name = " ".join(context.args)
        # Remove o @ do início se existir
        if group_name.startswith("@"):
            group_name = group_name[1:]
        logger.info(f"Buscando blacklist para o grupo: {group_name}")
        blacklist = await mongodb_client.get_blacklist_by_group_name(group_name)
        
        # Se não encontrou o grupo ou não está sendo monitorado
        if not blacklist:
            # Deleta o comando original
            try:
                await update.message.delete()
            except Exception as e:
                logger.error(f"Erro ao deletar mensagem de comando: {e}")
                
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Grupo não encontrado.\n\n"
                     "Certifique-se de que:\n"
                     "1. O nome do grupo está correto\n"
                     "2. O bot está no grupo",
                parse_mode=ParseMode.MARKDOWN
            )
            return
    else:
        # Caso contrário, obtém a blacklist do chat atual
        logger.info(f"Buscando blacklist para o chat atual: {chat_id}")
        blacklist = await mongodb_client.get_blacklist(chat_id)
    
    # Deleta o comando original
    try:
        await update.message.delete()
    except Exception as e:
        logger.error(f"Erro ao deletar mensagem de comando: {e}")
    
    # Se não houver mensagens na blacklist
    if not blacklist or len(blacklist) == 0:
        await context.bot.send_message(
            chat_id=chat_id,
            text="📋 *BLACKLIST*\n\nNão há mensagens na blacklist deste chat.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Formata a mensagem com as informações da blacklist
    message = "📋 *BLACKLIST*\n\n"
    keyboard = []
    
    for i, item in enumerate(blacklist, start=1):  # Removida a limitação de 10 itens
        # Formata data de adição
        added_at = item.get("added_at", datetime.now()).strftime("%d/%m/%Y %H:%M")
        
        # Formata nome de usuário
        user_name = item.get("user_name", "Usuário desconhecido")
        username = item.get("username")
        display_name = f"@{username}" if username else user_name
        
        # Formata link da mensagem
        item_chat_id = item.get("chat_id")
        message_id = item.get("message_id")
        
        # Para grupos, o ID geralmente começa com "-100" e precisa ser formatado para o link
        # Removendo o prefixo "-100" e mantendo apenas o identificador numérico real do grupo
        formatted_chat_id = str(item_chat_id)
        if formatted_chat_id.startswith("-100"):
            formatted_chat_id = formatted_chat_id[4:]  # Remove os primeiros 4 caracteres ("-100")
        elif formatted_chat_id.startswith("-"):
            formatted_chat_id = formatted_chat_id[1:]  # Remove apenas o hífen se não tiver o prefixo "-100"
        
        # Gera o link da mensagem
        message_link = f"https://t.me/c/{formatted_chat_id}/{message_id}"
        link_text = f"[Ver mensagem]({message_link})"
        
        # Formata texto da mensagem (limitado a 50 caracteres)
        message_text = item.get("message_text", "")
        if message_text:
            if len(message_text) > 50:
                message_text = message_text[:47] + "..."
            message_text = f"\n_\"{message_text}\"_"
        
        # Formata informações do admin
        added_by_name = item.get("added_by_name", "Admin desconhecido")
        
        # Adiciona item à mensagem
        message += f"*{i}.* {display_name}{message_text}\n"
        message += f"📅 {added_at} • 👮 {added_by_name} • {link_text}\n\n"
        
        # Adiciona botão de remover
        keyboard.append([
            InlineKeyboardButton(
                text=f"🗑️ Remover item {i}",
                callback_data=f"rmblacklist_{str(item['_id'])}"
            )
        ])
    
    # Cria o teclado inline
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Envia a mensagem com a blacklist
    await context.bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,  # Impede a pré-visualização dos links
        reply_markup=reply_markup  # Adiciona os botões
    )

async def rmblacklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /rmblacklist.
    Remove uma mensagem da blacklist pelo seu ID ou link.
    
    Exemplos:
        /rmblacklist 60f1a5b5a9c1e2b3c4d5e6f7
        /rmblacklist https://t.me/c/2288213607/1452
    
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
    
    # Verifica se foi fornecido um argumento
    if not context.args or len(context.args) == 0:
        await send_temporary_message(
            update, 
            context, 
            "Por favor, forneça o ID ou link da mensagem a ser removida da blacklist.\n\n"
            "Exemplos:\n"
            "• `/rmblacklist 60f1a5b5a9c1e2b3c4d5e6f7`\n"
            "• `/rmblacklist https://t.me/c/2288213607/1452`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Obtém o argumento fornecido (ID ou link)
    arg = context.args[0]
    success = False
    
    # Verifica se o argumento é um link
    if arg.startswith("https://t.me/"):
        logger.info(f"Removendo item da blacklist pelo link: {arg}")
        success = await mongodb_client.remove_from_blacklist_by_link(arg)
    else:
        # Trata como ID
        logger.info(f"Removendo item da blacklist pelo ID: {arg}")
        success = await mongodb_client.remove_from_blacklist(arg)
    
    if success:
        logger.info(f"Item removido da blacklist por {update.effective_user.full_name} ({update.effective_user.id})")
    else:
        # Envia mensagem de erro
        await send_temporary_message(
            update, 
            context, 
            f"❌ Erro ao remover item da blacklist. Verifique se o ID ou link está correto."
        )
    
    # Deleta a mensagem de comando
    try:
        await update.message.delete()
    except Exception as e:
        logger.error(f"Erro ao deletar mensagem de comando: {e}") 