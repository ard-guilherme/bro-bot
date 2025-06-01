"""
Handlers para os comandos de blacklist.
"""
import logging
from typing import Optional, List, Dict, Any, Set
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReactionTypeEmoji
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ReactionEmoji
from telegram.error import BadRequest, TimedOut
from datetime import datetime
import asyncio
from src.utils.mongodb_instance import mongodb_client
from src.bot.handlers import is_admin, send_temporary_message
from html import escape as escape_html
from bson import ObjectId

# Configuração de logging
logger = logging.getLogger(__name__)

def escape_markdown_v2(text: str) -> str:
    """
    Escapa caracteres especiais do MarkdownV2.
    
    Args:
        text (str): Texto para escapar.
        
    Returns:
        str: Texto com caracteres especiais escapados.
    """
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def escape_markdown_v2_url(url: str) -> str:
    """
    Escapa caracteres especiais em URLs para MarkdownV2.
    
    Args:
        url (str): URL para escapar.
        
    Returns:
        str: URL com caracteres especiais escapados.
    """
    special_chars = [')', '.', '!', '+', '-', '_', '=', '{', '}', '|']
    for char in special_chars:
        url = url.replace(char, f'\\{char}')
    return url

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
        
        # Tenta enviar mensagem privada para o usuário
        try:
            # Prepara o link direto para a mensagem
            chat_id_str = str(chat_id)
            formatted_chat_id = chat_id_str
            # Formata o chat_id para o link
            if chat_id_str.startswith("-100"):
                formatted_chat_id = chat_id_str[4:]
            elif chat_id_str.startswith("-"):
                formatted_chat_id = chat_id_str[1:]
            
            message_link = f"https://t.me/c/{formatted_chat_id}/{message_id}"
            
            # Obtém o nome do grupo/chat
            try:
                chat = await context.bot.get_chat(chat_id)
                chat_title = chat.title
            except Exception as e:
                logger.error(f"Erro ao obter informações do chat {chat_id}: {e}")
                chat_title = "do grupo"
            
            # Envia mensagem privada
            notification_text = (
                f"Olá, [sua postagem]({message_link}) foi adicionada à blacklist por não estar alinhada com o propósito do grupo {chat_title}.\n\n"
                f"Mesmo que ela tenha sido excluída, entre em contato com um ADM para justificar e removê-lo da lista. "
                f"Caso contrário, eventualmente poderá sofrer banimento."
            )
            
            await context.bot.send_message(
                chat_id=user_id,
                text=notification_text,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            logger.info(f"Mensagem de notificação enviada ao usuário {user_id} sobre adição à blacklist")
        except Exception as e:
            error_message = str(e)
            logger.warning(f"Não foi possível enviar mensagem privada ao usuário {user_id}: {e}")
            
            # Verifica se é o erro específico de não poder iniciar conversa
            if "bot can't initiate conversation with a user" in error_message:
                logger.info(f"O usuário {user_id} nunca interagiu com o bot antes, não foi possível enviar mensagem privada")
                
                # Prepara username/menção para notificação pública
                display_name = f"@{username}" if username else user_name
                
                try:
                    # Envia uma mensagem temporária no grupo
                    public_notification = (
                        f"{display_name}, [sua postagem]({message_link}) foi adicionada à blacklist por não estar alinhada com o propósito do grupo {chat_title}.\n\n"
                        f"Mesmo que ela tenha sido excluída, entre em contato com um ADM para justificar e removê-lo da lista. "
                        f"Caso contrário, eventualmente poderá sofrer banimento."
                    )
                    
                    # Envia a mensagem e programa para ser excluída após 60 segundos
                    sent_message = await context.bot.send_message(
                        chat_id=chat_id,
                        text=public_notification,
                        parse_mode=ParseMode.MARKDOWN,
                        disable_web_page_preview=True
                    )
                    
                    # Programa a exclusão da mensagem após 60 segundos
                    context.job_queue.run_once(
                        lambda context: context.bot.delete_message_after(
                            chat_id=sent_message.chat_id, 
                            message_id=sent_message.message_id
                        ),
                        60,  # 60 segundos
                        data={"chat_id": sent_message.chat_id, "message_id": sent_message.message_id}
                    )
                    
                    logger.info(f"Enviada notificação pública temporária para {user_id} sobre adição à blacklist")
                except Exception as e2:
                    logger.error(f"Erro ao enviar notificação pública para {user_id}: {e2}")
        
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
                     "2. O bot está no grupo"
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
            text="📋 BLACKLIST\n\nNão há mensagens na blacklist deste chat."
        )
        return
    
    # Constante para o limite de caracteres por mensagem
    MESSAGE_LENGTH_LIMIT = 4000
    
    # Formata as entradas da blacklist
    items_text = []
    for i, item in enumerate(blacklist, start=1):
        try:
            # Formata data de adição
            added_at = item.get("added_at", datetime.now()).strftime("%d/%m/%Y %H:%M")
            
            # Formata nome de usuário (escapado para HTML)
            user_name = item.get("user_name", "Usuário desconhecido")
            username = item.get("username")
            display_name = f"@{username}" if username else user_name
            escaped_display_name = escape_html(display_name)
            
            # Formata link da mensagem
            item_chat_id = item.get("chat_id")
            message_id = item.get("message_id")
            
            # Para grupos, o ID geralmente começa com "-100" e precisa ser formatado para o link
            formatted_chat_id = str(item_chat_id)
            if formatted_chat_id.startswith("-100"):
                formatted_chat_id = formatted_chat_id[4:]
            elif formatted_chat_id.startswith("-"):
                formatted_chat_id = formatted_chat_id[1:]
            
            message_link = f"https://t.me/c/{formatted_chat_id}/{message_id}"
            
            # Formata texto da mensagem (limitado e escapado)
            message_text = item.get("message_text", "")
            escaped_message_text = escape_html(message_text[:100] + ("..." if len(message_text) > 100 else "")) # Limita o texto para evitar estouro fácil
            
            # Formata nome do admin (escapado)
            admin_name = item.get("added_by_name", "Admin desconhecido")
            escaped_admin_name = escape_html(admin_name)
            
            # ID único do item para referência (usado no rmblacklist)
            item_id_str = str(item.get('_id'))

            item_str = (
                f"{i}. <b>Usuário:</b> {escaped_display_name} \n"
                f"   <b>Adicionado por:</b> {escaped_admin_name} em {added_at}\n"
                f"   <b>Mensagem:</b> <a href='{message_link}'>Link</a> \n"
                f"   <b>Texto:</b> <i>{escaped_message_text}</i>\n"
                f"   <b>ID para remover:</b> <code>{item_id_str}</code>\n" # Adicionado ID
            )
            items_text.append(item_str)
            
        except Exception as e:
            logger.error(f"Erro ao formatar item {item.get('_id', 'N/A')} da blacklist: {e}")
            items_text.append(f"{i}. Erro ao formatar este item.\n")

    # Lógica de Paginação
    current_message = ""
    message_parts = []
    
    for item_str in items_text:
        # Verifica se adicionar o próximo item + uma linha extra excede o limite
        if len(current_message) + len(item_str) + 1 > MESSAGE_LENGTH_LIMIT:
            # Se exceder e a mensagem atual não estiver vazia, adiciona a parte atual
            if current_message:
                message_parts.append(current_message)
            # Começa uma nova parte com o item atual
            current_message = item_str + "\n"
        else:
            # Adiciona o item à parte atual
            current_message += item_str + "\n"
            
    # Adiciona a última parte se não estiver vazia
    if current_message:
        message_parts.append(current_message)

    total_parts = len(message_parts)

    # Envia as partes paginadas
    for i, part in enumerate(message_parts, start=1):
        header = f"<b>📋 BLACKLIST (Parte {i}/{total_parts})</b>\n\n"
        final_message = header + part
        
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=final_message,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True # Desabilitar preview para economizar espaço e evitar clutter
            )
            # Pequeno delay para evitar flood limits do Telegram
            if total_parts > 1 and i < total_parts:
                await asyncio.sleep(0.5) 
        except BadRequest as e:
            logger.error(f"Erro (BadRequest) ao enviar parte {i}/{total_parts} da blacklist: {e}")
            # Tenta enviar uma mensagem de erro genérica se a parte específica falhar
            if i == 1:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ Ocorreu um erro ao formatar ou enviar a lista da blacklist. Verifique os logs."
                )
            break # Interrompe o envio das demais partes se uma falhar
        except TimedOut:
            logger.warning(f"Timeout ao enviar parte {i}/{total_parts} da blacklist. Tentando novamente...")
            await asyncio.sleep(1) # Espera um pouco mais
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=final_message,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True
                )
            except Exception as e_retry:
                logger.error(f"Erro (Retry) ao enviar parte {i}/{total_parts} da blacklist: {e_retry}")
                if i == 1:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="❌ Ocorreu um erro de timeout ao enviar a lista da blacklist. Tente novamente mais tarde."
                    )
                break # Interrompe
        except Exception as e:
            logger.error(f"Erro inesperado ao enviar parte {i}/{total_parts} da blacklist: {e}")
            if i == 1:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ Ocorreu um erro inesperado ao processar a blacklist. Verifique os logs."
                )
            break # Interrompe

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

async def ban_blacklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /ban_blacklist <group_name>.
    Bane todos os usuários únicos da blacklist de um grupo específico e limpa
    as entradas correspondentes (apenas dos usuários banidos com sucesso).
    """
    # 1. Verificações Iniciais
    if not await is_admin(update, context):
        await send_temporary_message(update, context, "Apenas administradores do bot podem usar este comando.")
        return

    if not context.args or len(context.args) == 0:
        await send_temporary_message(update, context, "Uso: /ban_blacklist <nome_do_grupo>")
        return

    group_name = " ".join(context.args)
    admin_user = update.effective_user
    original_chat_id = update.effective_chat.id # Onde o admin executou o comando

    # Deleta o comando original imediatamente
    try:
        await update.message.delete()
    except Exception as e:
        logger.error(f"Erro ao deletar mensagem de comando /ban_blacklist: {e}")
        
    # Envia mensagem inicial
    processing_message = await context.bot.send_message(
        chat_id=original_chat_id,
        text=f"⚙️ Iniciando processo de banimento da blacklist para o grupo '{group_name}'..."
    )

    # 2. Obter Chat ID do Grupo Alvo
    logger.info(f"Buscando chat_id para o grupo: {group_name}")
    target_chat_id = await mongodb_client.get_chat_id_by_group_name(group_name)

    if target_chat_id is None:
        await processing_message.edit_text(f"❌ Grupo '{group_name}' não encontrado ou não monitorado ativamente.")
        return
    
    logger.info(f"Chat ID encontrado para '{group_name}': {target_chat_id}")

    # 3. Obter Blacklist e Usuários Únicos
    logger.info(f"Buscando blacklist para o chat: {target_chat_id}")
    blacklist_entries = await mongodb_client.get_blacklist(target_chat_id)

    if not blacklist_entries:
        await processing_message.edit_text(f"✅ A blacklist para o grupo '{group_name}' (ID: {target_chat_id}) já está vazia.")
        return

    unique_user_ids: Set[int] = set()
    user_details_map: Dict[int, Dict[str, Any]] = {}
    for entry in blacklist_entries:
        user_id = entry.get("user_id")
        if user_id:
            unique_user_ids.add(user_id)
            if user_id not in user_details_map: # Armazena detalhes do primeiro encontrado
                user_details_map[user_id] = {
                    "name": entry.get("user_name", "Nome Desconhecido"),
                    "username": entry.get("username")
                }
    
    total_unique_users = len(unique_user_ids)
    logger.info(f"Encontrados {total_unique_users} usuários únicos na blacklist do chat {target_chat_id}.")
    await processing_message.edit_text(
        f"⚙️ Encontrados {total_unique_users} usuários únicos. Iniciando tentativas de banimento em '{group_name}' (ID: {target_chat_id})..."
    )

    # 4. Processo de Banimento e Coleta de Resultados
    banned_count = 0
    failed_count = 0
    failed_user_details = []
    ids_to_delete: List[ObjectId] = [] # Armazena ObjectIds das entradas a remover

    for i, user_id in enumerate(unique_user_ids):
        user_display = user_details_map.get(user_id, {}).get("username") or user_details_map.get(user_id, {}).get("name")
        user_display = f"@{user_display}" if user_details_map.get(user_id, {}).get("username") else user_display
        user_display = escape_html(f"{user_display} ({user_id})")
        
        logger.debug(f"Tentando banir usuário {user_id} do chat {target_chat_id} ({i+1}/{total_unique_users})")
        try:
            # Tenta banir o usuário
            # O parâmetro revoke_messages=True não existe mais na v20+, ban apenas bane.
            success = await context.bot.ban_chat_member(chat_id=target_chat_id, user_id=user_id)
            
            if success:
                banned_count += 1
                logger.info(f"Usuário {user_id} banido com sucesso do chat {target_chat_id}.")
                # Coleta os _id de todas as entradas deste usuário neste chat
                for entry in blacklist_entries:
                    if entry.get("user_id") == user_id and entry.get("chat_id") == target_chat_id:
                        entry_obj_id = entry.get("_id")
                        if isinstance(entry_obj_id, ObjectId):
                             ids_to_delete.append(entry_obj_id)
            else:
                 # Este caso não deve ocorrer com ban_chat_member se não lançar exceção, mas incluído por segurança
                 raise Exception("ban_chat_member retornou False")
                 
        except BadRequest as e:
            failed_count += 1
            error_message = str(e)
            logger.warning(f"Falha ao banir usuário {user_id} do chat {target_chat_id}: {error_message}")
            failed_user_details.append({"id": user_id, "name": user_display, "error": escape_html(error_message)})
        except Exception as e: # Captura outras exceções inesperadas
            failed_count += 1
            error_message = str(e)
            logger.error(f"Erro inesperado ao tentar banir usuário {user_id} do chat {target_chat_id}: {error_message}")
            failed_user_details.append({"id": user_id, "name": user_display, "error": escape_html(f"Erro inesperado: {error_message}")})
        
        # Adiciona delay
        await asyncio.sleep(0.6) 

    # 5. Limpeza da Blacklist
    deleted_count = 0
    if ids_to_delete:
        logger.info(f"Tentando remover {len(ids_to_delete)} itens da blacklist para usuários banidos com sucesso...")
        deleted_count = await mongodb_client.remove_blacklist_items_by_ids(ids_to_delete)
        logger.info(f"{deleted_count} itens da blacklist efetivamente removidos.")
    else:
        logger.info("Nenhum usuário banido com sucesso, nenhum item removido da blacklist.")

    # 6. Relatório Final
    report_message = f"<b>📊 Relatório de Banimento da Blacklist</b>\n\n"
    report_message += f"<b>Grupo:</b> {escape_html(group_name)} (ID: <code>{target_chat_id}</code>)\n"
    report_message += f"<b>Usuários únicos na blacklist:</b> {total_unique_users}\n"
    report_message += f"<b>Banidos com sucesso:</b> ✅ {banned_count}\n"
    report_message += f"<b>Falhas ao banir:</b> ❌ {failed_count}\n"
    report_message += f"<b>Itens removidos da blacklist:</b> 🗑️ {deleted_count}\n"
    report_message += f"<i>(Apenas itens de usuários banidos com sucesso foram removidos)</i>\n"

    if failed_user_details:
        report_message += "\n<b>Detalhes das Falhas:</b>\n"
        # Limita a exibição de detalhes para não estourar a mensagem
        max_details = 15
        for i, detail in enumerate(failed_user_details[:max_details]):
            report_message += f"- {detail['name']}: {detail['error']}\n"
        if len(failed_user_details) > max_details:
            report_message += f"<i>... e mais {len(failed_user_details) - max_details} falhas. Verifique os logs para detalhes completos.</i>\n"
            
    # Edita a mensagem de processamento com o resultado final
    try:
        await processing_message.edit_text(report_message, parse_mode=ParseMode.HTML)
    except BadRequest as e:
        logger.error(f"Erro ao enviar relatório final de ban_blacklist: {e}")
        # Tenta enviar como nova mensagem se a edição falhar
        await context.bot.send_message(
            chat_id=original_chat_id, 
            text="Ocorreu um erro ao editar a mensagem de status. Relatório:\n" + report_message,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
         logger.error(f"Erro inesperado ao editar mensagem de relatório: {e}") 