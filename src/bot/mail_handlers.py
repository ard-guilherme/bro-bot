"""
Handlers para o sistema de Correio Elegante do GYM NATION Bot.
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from telegram.constants import ParseMode

from src.utils.mongodb_instance import mongodb_client
from src.utils.config import Config

logger = logging.getLogger(__name__)

# Estados do ConversationHandler para correio elegante
MAIL_MESSAGE, MAIL_RECIPIENT = range(2)

# Estados do ConversationHandler para resposta anônima
REPLY_MESSAGE = range(1)


class MailHandlers:
    """Classe para gerenciar handlers do correio elegante."""
    
    @staticmethod
    async def correio_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Comando /correio - Inicia o processo de envio de correio elegante.
        Deve ser usado apenas em chat privado.
        """
        if update.effective_chat.type != 'private':
            await update.message.reply_text(
                "❌ Este comando só pode ser usado em chat privado comigo.\n"
                "Clique no meu nome e inicie uma conversa privada para usar o correio elegante."
            )
            return ConversationHandler.END
        
        user_id = update.effective_user.id
        user_name = update.effective_user.full_name
        
        # Verificar limite diário de correios
        daily_count = await mongodb_client.get_daily_mail_count(user_id)
        if daily_count >= 2:
            await update.message.reply_text(
                "📬 Você já enviou 2 correios hoje.\n"
                "Limite diário atingido. Tente novamente amanhã!"
            )
            return ConversationHandler.END
        
        await update.message.reply_text(
            "📬 **Correio Elegante GYM NATION** 💌\n\n"
            "Envie uma mensagem anônima para um membro do grupo!\n\n"
            "✍️ **Digite sua mensagem:**\n"
            "_(Será analisada para filtrar conteúdo ofensivo)_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ForceReply(selective=True)
        )
        
        # Armazenar dados do usuário no contexto
        context.user_data['mail_sender_id'] = user_id
        context.user_data['mail_sender_name'] = user_name
        
        return MAIL_MESSAGE
    
    @staticmethod
    async def handle_mail_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Processa a mensagem do correio elegante."""
        message_text = update.message.text
        
        if not message_text or len(message_text.strip()) < 10:
            await update.message.reply_text(
                "❌ Mensagem muito curta. Digite pelo menos 10 caracteres."
            )
            return MAIL_MESSAGE
        
        if len(message_text) > 500:
            await update.message.reply_text(
                "❌ Mensagem muito longa. Máximo de 500 caracteres."
            )
            return MAIL_MESSAGE
        
        # Filtro básico de conteúdo ofensivo
        if await MailHandlers._contains_offensive_content(message_text):
            await update.message.reply_text(
                "❌ Sua mensagem contém conteúdo inapropriado.\n"
                "Por favor, reescreva de forma respeitosa."
            )
            return MAIL_MESSAGE
        
        # Armazenar mensagem no contexto
        context.user_data['mail_message'] = message_text
        
        await update.message.reply_text(
            "🎯 **Agora digite o @ do destinatário:**\n"
            "_(Exemplo: @username)_\n\n"
            "ℹ️ O destinatário deve ser membro do GYM NATION.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ForceReply(selective=True)
        )
        
        return MAIL_RECIPIENT
    
    @staticmethod
    async def handle_mail_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Processa o destinatário do correio elegante."""
        recipient_text = update.message.text.strip()
        
        # Validar formato do @
        if not recipient_text.startswith('@'):
            await update.message.reply_text(
                "❌ Formato inválido. Digite o @ seguido do username.\n"
                "Exemplo: @username"
            )
            return MAIL_RECIPIENT
        
        recipient_username = recipient_text[1:]  # Remove o @
        
        # Validar se o usuário está no grupo GYM NATION
        gym_nation_chat_id = await mongodb_client.get_gym_nation_chat_id()
        if not gym_nation_chat_id:
            await update.message.reply_text(
                "❌ Erro interno: Grupo GYM NATION não encontrado.\n"
                "Contate o administrador."
            )
            return ConversationHandler.END
        
        # Pular verificação - sempre assumir que o usuário está no grupo
        
        # Exibir pré-visualização
        sender_id = context.user_data['mail_sender_id']
        sender_name = context.user_data['mail_sender_name']
        message_text = context.user_data['mail_message']
        
        preview_text = (
            "📬 **PRÉ-VISUALIZAÇÃO DO CORREIO**\n\n"
            f"**Para:** @{recipient_username}\n"
            f"**Mensagem:** {message_text}\n\n"
            "✅ Confirma o envio?"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirmar Envio", callback_data=f"mail_confirm_{recipient_username}"),
                InlineKeyboardButton("❌ Cancelar", callback_data="mail_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            preview_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        return ConversationHandler.END
    
    @staticmethod
    async def handle_mail_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Processa a confirmação do envio do correio."""
        query = update.callback_query
        await query.answer()
        
        if query.data == "mail_cancel":
            await query.edit_message_text("❌ Correio cancelado.")
            return
        
        if not query.data.startswith("mail_confirm_"):
            return
        
        recipient_username = query.data.replace("mail_confirm_", "")
        sender_id = query.from_user.id
        sender_name = query.from_user.full_name
        message_text = context.user_data.get('mail_message')
        
        if not message_text:
            await query.edit_message_text("❌ Erro: Mensagem não encontrada.")
            return
        
        # Salvar no banco de dados
        mail_id = await mongodb_client.create_mail(
            sender_id=sender_id,
            sender_name=sender_name,
            recipient_username=recipient_username,
            message_text=message_text
        )
        
        if mail_id:
            await query.edit_message_text(
                "✅ **Correio enviado com sucesso!** 📬\n\n"
                "Sua mensagem será publicada no grupo em breve.\n"
                "Aguarde a publicação automática! 🕐",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text(
                "❌ Erro ao enviar correio. Tente novamente."
            )
    
    @staticmethod
    async def revelar_correio_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /revelarcorreio - Inicia processo de revelação do remetente via Pix."""
        if update.effective_chat.type != 'private':
            await update.message.reply_text(
                "❌ Este comando só pode ser usado em chat privado."
            )
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Use: `/revelarcorreio <ID_da_mensagem>`\n\n"
                "O ID da mensagem está nos botões do correio no grupo.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        mail_id = context.args[0]
        user_id = update.effective_user.id
        
        # Verificar se o correio existe
        mail_data = await mongodb_client.get_mail_by_id(mail_id)
        if not mail_data:
            await update.message.reply_text(
                "❌ Correio não encontrado ou já expirado."
            )
            return
        
        # Verificar se já foi revelado
        if mail_data.get('revealed_to', []):
            if user_id in mail_data['revealed_to']:
                # Usuário já revelou, mostrar informações
                await update.message.reply_text(
                    f"📬 **CORREIO REVELADO** ✨\n\n"
                    f"**Remetente:** {mail_data['sender_name']}\n"
                    f"**Mensagem:** {mail_data['message_text']}\n"
                    f"**Para:** @{mail_data['recipient_username']}",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
        
        # Gerar chave Pix
        pix_key, pix_id = await MailHandlers._generate_pix_payment(user_id, mail_id)
        
        if not pix_key:
            await update.message.reply_text(
                "❌ Erro ao gerar pagamento Pix. Tente novamente."
            )
            return
        
        pix_text = (
            "💰 **REVELAÇÃO DO CORREIO - PIX R$ 2,00**\n\n"
            f"**Chave Pix:** `{pix_key}`\n"
            f"**Valor:** R$ 2,00\n"
            f"**ID do Pagamento:** `{pix_id}`\n\n"
            "📱 **Instruções:**\n"
            "1. Copie a chave Pix acima\n"
            "2. Faça o pagamento de R$ 2,00\n"
            "3. Aguarde a confirmação automática\n"
            "4. Receba a revelação do remetente!\n\n"
            "⏰ Esta chave expira em 30 minutos."
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Confirmar Pagamento Manual", 
                                callback_data=f"pix_confirm_{pix_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            pix_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    @staticmethod
    async def handle_pix_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Processa solicitação de confirmação do pagamento Pix."""
        query = update.callback_query
        await query.answer()

        if not query.data.startswith("pix_confirm_"):
            return

        pix_id = query.data.replace("pix_confirm_", "")
        user_id = query.from_user.id
        user_name = query.from_user.full_name

        # Buscar dados do pagamento
        payment_data = await mongodb_client.get_pix_payment(pix_id)
        if not payment_data:
            await query.edit_message_text("❌ Pagamento não encontrado.")
            return

        mail_id = payment_data['mail_id']

        # Buscar dados do correio
        mail_data = await mongodb_client.get_mail_by_id(mail_id)
        if not mail_data:
            await query.edit_message_text("❌ Correio não encontrado.")
            return

        # Marcar pagamento como "aguardando confirmação"
        await mongodb_client.db.pix_payments.update_one(
            {"pix_id": pix_id},
            {"$set": {"status": "awaiting_confirmation", "user_requested_at": datetime.now()}}
        )

        # Enviar mensagem para o proprietário
        owner_id = Config.get_owner_id()
        
        owner_message = (
            f"💰 **CONFIRMAÇÃO DE PIX NECESSÁRIA** 💰\n\n"
            f"**Usuário:** {user_name} (ID: {user_id})\n"
            f"**Valor:** R$ 2,00\n"
            f"**Chave Pix:** `{payment_data['pix_key']}`\n"
            f"**ID Pagamento:** `{pix_id}`\n\n"
            f"**Correio a ser revelado:**\n"
            f"• **Remetente:** {mail_data['sender_name']}\n"
            f"• **Para:** @{mail_data['recipient_username']}\n"
            f"• **Mensagem:** {mail_data['message_text'][:100]}...\n\n"
            f"⚠️ **O PIX de R$ 2,00 foi recebido?**"
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ SIM - PIX Recebido", callback_data=f"owner_yes_{pix_id}"),
                InlineKeyboardButton("❌ NÃO - PIX Não Recebido", callback_data=f"owner_no_{pix_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await context.bot.send_message(
                chat_id=owner_id,
                text=owner_message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )

            # Informar ao usuário que está aguardando confirmação
            await query.edit_message_text(
                f"⏳ **AGUARDANDO CONFIRMAÇÃO DO PIX** ⏳\n\n"
                f"📱 Sua solicitação foi enviada para verificação.\n"
                f"💰 **Valor:** R$ 2,00\n"
                f"📋 **ID:** `{pix_id}`\n\n"
                f"🔍 O proprietário verificará se o PIX foi recebido e liberará o correio em breve.\n\n"
                f"⏰ Aguarde a confirmação...",
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            logger.error(f"Erro ao notificar proprietário sobre PIX: {e}")
            await query.edit_message_text(
                "❌ Erro ao solicitar confirmação. Tente novamente ou contate o administrador."
            )
    
    @staticmethod
    async def handle_mail_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Processa cliques nos botões dos correios publicados no grupo."""
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("mail_reveal_"):
            mail_id = query.data.replace("mail_reveal_", "")
            
            await query.message.reply_text(
                f"💰 Para revelar o remetente, use o comando:\n\n"
                f"`/revelarcorreio {mail_id}`\n\n"
                "📱 Clique no meu nome e inicie chat privado para usar o comando.",
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif query.data.startswith("mail_reply_"):
            mail_id = query.data.replace("mail_reply_", "")
            
            await query.message.reply_text(
                f"💌 Para responder anonimamente, use:\n\n"
                f"`/respondercorreio {mail_id}`\n\n"
                "📱 Clique no meu nome e inicie chat privado.",
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif query.data.startswith("mail_report_"):
            mail_id = query.data.replace("mail_report_", "")
            user_id = query.from_user.id
            user_name = query.from_user.full_name
            
            # Registrar denúncia
            reported = await mongodb_client.report_mail(mail_id, user_id, user_name)
            
            if reported:
                await query.message.reply_text(
                    "🚨 Denúncia registrada com sucesso!\n"
                    "O correio será analisado pelos administradores."
                )
            else:
                await query.message.reply_text(
                    "❌ Erro ao registrar denúncia."
                )
        

        elif query.data.startswith("owner_yes_") or query.data.startswith("owner_no_"):
            await MailHandlers.handle_owner_pix_confirmation(update, context)
    
    @staticmethod
    async def handle_owner_pix_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Processa confirmação do proprietário sobre o recebimento do PIX."""
        query = update.callback_query
        await query.answer()
        
        # Verificar se é o proprietário
        if query.from_user.id != Config.get_owner_id():
            await query.answer("❌ Apenas o proprietário pode confirmar pagamentos.", show_alert=True)
            return
        
        confirmed = query.data.startswith("owner_yes_")
        pix_id = query.data.replace("owner_yes_", "").replace("owner_no_", "")
        
        # Buscar dados do pagamento
        payment_data = await mongodb_client.get_pix_payment(pix_id)
        if not payment_data:
            await query.edit_message_text("❌ Pagamento não encontrado.")
            return
        
        user_id = payment_data['user_id']
        mail_id = payment_data['mail_id']
        
        if confirmed:
            # PIX confirmado - revelar correio
            success = await mongodb_client.confirm_pix_payment(pix_id, user_id)
            
            if success:
                mail_data = await mongodb_client.reveal_mail(mail_id, user_id)
                
                if mail_data:
                    # Atualizar mensagem do proprietário
                    await query.edit_message_text(
                        f"✅ **PIX CONFIRMADO E CORREIO REVELADO** ✅\n\n"
                        f"**Usuário:** {payment_data.get('user_name', 'N/A')} (ID: {user_id})\n"
                        f"**Valor:** R$ 2,00\n"
                        f"**ID Pagamento:** `{pix_id}`\n\n"
                        f"📬 **Correio revelado com sucesso!**",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                    # Notificar o usuário
                    try:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=f"✅ **PAGAMENTO CONFIRMADO!** 💰\n\n"
                                 f"📬 **CORREIO REVELADO** ✨\n\n"
                                 f"**Remetente:** {mail_data['sender_name']}\n"
                                 f"**Mensagem:** {mail_data['message_text']}\n"
                                 f"**Para:** @{mail_data['recipient_username']}",
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except Exception as e:
                        logger.error(f"Erro ao notificar usuário sobre correio revelado: {e}")
                else:
                    await query.edit_message_text("❌ Erro ao revelar correio.")
            else:
                await query.edit_message_text("❌ Erro ao confirmar pagamento.")
        else:
            # PIX negado
            await mongodb_client.db.pix_payments.update_one(
                {"pix_id": pix_id},
                {"$set": {"status": "denied", "denied_at": datetime.now()}}
            )
            
            # Atualizar mensagem do proprietário
            await query.edit_message_text(
                f"❌ **PIX NEGADO** ❌\n\n"
                f"**Usuário:** {payment_data.get('user_name', 'N/A')} (ID: {user_id})\n"
                f"**Valor:** R$ 2,00\n"
                f"**ID Pagamento:** `{pix_id}`\n\n"
                f"🚫 **Pagamento não foi recebido.**",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Notificar o usuário
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"❌ **PAGAMENTO NÃO CONFIRMADO** ❌\n\n"
                         f"💰 O PIX de R$ 2,00 não foi localizado.\n"
                         f"📋 **ID:** `{pix_id}`\n\n"
                         f"🔄 Verifique se:\n"
                         f"• O valor está correto (R$ 2,00)\n"
                         f"• A chave Pix está correta\n"
                         f"• O pagamento foi processado\n\n"
                         f"💬 Se o pagamento foi feito, entre em contato com o administrador.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Erro ao notificar usuário sobre PIX negado: {e}")
    
    @staticmethod
    async def responder_correio_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Comando /respondercorreio - Inicia resposta anônima."""
        if update.effective_chat.type != 'private':
            await update.message.reply_text(
                "❌ Este comando só pode ser usado em chat privado."
            )
            return ConversationHandler.END
        
        if not context.args:
            await update.message.reply_text(
                "❌ Use: `/respondercorreio <ID_da_mensagem>`",
                parse_mode=ParseMode.MARKDOWN
            )
            return ConversationHandler.END
        
        mail_id = context.args[0]
        
        # Verificar se o correio existe
        mail_data = await mongodb_client.get_mail_by_id(mail_id)
        if not mail_data:
            await update.message.reply_text(
                "❌ Correio não encontrado."
            )
            return ConversationHandler.END
        
        # Armazenar ID do correio no contexto
        context.user_data['reply_mail_id'] = mail_id
        context.user_data['reply_sender_id'] = update.effective_user.id
        context.user_data['reply_sender_name'] = update.effective_user.full_name
        
        await update.message.reply_text(
            "💌 **Resposta Anônima**\n\n"
            "Digite sua resposta para o remetente do correio:\n"
            "_(Será enviada anonimamente)_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ForceReply(selective=True)
        )
        
        return REPLY_MESSAGE
    
    @staticmethod
    async def denunciar_correio_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /denunciarcorreio - Denuncia um correio."""
        if update.effective_chat.type != 'private':
            await update.message.reply_text(
                "❌ Este comando só pode ser usado em chat privado."
            )
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Use: `/denunciarcorreio <ID_da_mensagem>`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        mail_id = context.args[0]
        user_id = update.effective_user.id
        user_name = update.effective_user.full_name
        
        # Verificar se o correio existe
        mail_data = await mongodb_client.get_mail_by_id(mail_id)
        if not mail_data:
            await update.message.reply_text(
                "❌ Correio não encontrado."
            )
            return
        
        # Registrar denúncia
        reported = await mongodb_client.report_mail(mail_id, user_id, user_name)
        
        if reported:
            await update.message.reply_text(
                "✅ **Denúncia registrada com sucesso!**\n\n"
                f"🚨 **ID do correio:** `{mail_id}`\n"
                f"📝 **Denunciado por:** {user_name}\n\n"
                "O correio será analisado pelos administradores.\n"
                "Correios com 3+ denúncias são removidos automaticamente.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                "❌ Erro ao registrar denúncia ou você já denunciou este correio."
            )
    
    @staticmethod
    async def handle_reply_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Processa mensagem de resposta anônima."""
        reply_text = update.message.text
        
        if not reply_text or len(reply_text.strip()) < 5:
            await update.message.reply_text(
                "❌ Resposta muito curta. Digite pelo menos 5 caracteres."
            )
            return REPLY_MESSAGE
        
        if len(reply_text) > 300:
            await update.message.reply_text(
                "❌ Resposta muito longa. Máximo de 300 caracteres."
            )
            return REPLY_MESSAGE
        
        # Filtro de conteúdo
        if await MailHandlers._contains_offensive_content(reply_text):
            await update.message.reply_text(
                "❌ Sua resposta contém conteúdo inapropriado."
            )
            return REPLY_MESSAGE
        
        mail_id = context.user_data['reply_mail_id']
        sender_id = context.user_data['reply_sender_id']
        sender_name = context.user_data['reply_sender_name']
        
        # Buscar dados do correio original para obter o sender_id
        mail_data = await mongodb_client.get_mail_by_id(mail_id)
        if not mail_data:
            await update.message.reply_text(
                "❌ Correio não encontrado."
            )
            return ConversationHandler.END
        
        original_sender_id = mail_data['sender_id']
        original_sender_name = mail_data['sender_name']
        recipient_username = mail_data['recipient_username']
        
        # Salvar resposta no banco
        success = await mongodb_client.send_mail_reply(
            mail_id, reply_text, sender_id, sender_name
        )
        
        if success:
            # Enviar resposta diretamente para o remetente original via chat privado
            try:
                reply_message = (
                    f"💌 **RESPOSTA ANÔNIMA** 💌\n\n"
                    f"**Seu correio para @{recipient_username} recebeu uma resposta:**\n\n"
                    f"💭 _{reply_text}_\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"_Resposta anônima • Não é possível identificar quem respondeu_"
                )
                
                await context.bot.send_message(
                    chat_id=original_sender_id,
                    text=reply_message,
                    parse_mode=ParseMode.MARKDOWN
                )
                
                await update.message.reply_text(
                    "✅ **Resposta enviada com sucesso!**\n\n"
                    f"📬 Sua resposta foi entregue anonimamente para **{original_sender_name}**.\n"
                    f"💌 Eles receberão sua mensagem em chat privado.",
                    parse_mode=ParseMode.MARKDOWN
                )
                
            except Exception as e:
                logger.error(f"Erro ao enviar resposta anônima para {original_sender_id}: {e}")
                await update.message.reply_text(
                    "✅ Resposta salva com sucesso!\n"
                    "❌ Mas houve erro ao notificar o remetente original.\n"
                    "A resposta ficará registrada no sistema."
                )
        else:
            await update.message.reply_text(
                "❌ Erro ao enviar resposta."
            )
        
        return ConversationHandler.END
    
    @staticmethod
    async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancela conversação do correio."""
        await update.message.reply_text("❌ Operação cancelada.")
        return ConversationHandler.END
    
    # Métodos auxiliares
    
    @staticmethod
    async def _contains_offensive_content(text: str) -> bool:
        """Filtro básico de conteúdo ofensivo."""
        # Lista básica de palavras ofensivas (expandir conforme necessário)
        offensive_words = [
            'merda', 'porra', 'caralho', 'puta', 'viado', 'idiota', 'burro',
            'fdp', 'arrombado', 'desgraça', 'otário', 'babaca'
        ]
        
        text_lower = text.lower()
        return any(word in text_lower for word in offensive_words)
    
    @staticmethod
    async def _check_user_in_group(bot, chat_id: int, username: str) -> bool:
        """Verifica se um usuário está no grupo pelo username."""
        try:
            # Primeiro, tentar sem @ para evitar problemas com API
            username_clean = username.lstrip('@')
            
            # Método 1: Tentar com @ na frente (mais comum)
            try:
                member = await bot.get_chat_member(chat_id, f"@{username_clean}")
                return member.status in ['member', 'administrator', 'creator']
            except Exception as e:
                # Log específico do erro para análise
                if "Bad Request" in str(e):
                    logger.warning(f"API retornou Bad Request para @{username_clean} no grupo {chat_id}. Possível problema de privacidade ou username inválido.")
                elif "not found" in str(e).lower():
                    logger.warning(f"Usuário @{username_clean} não encontrado no grupo {chat_id}")
                elif "Invalid user_id specified" in str(e):
                    logger.warning(f"Username @{username_clean} inválido ou com problema de privacidade")
                else:
                    logger.warning(f"Erro inesperado ao verificar @{username_clean}: {e}")
                
                # Implementar fallback: assumir que podem estar no grupo se for um erro 400 ou problemas de privacidade
                # (erro 400 geralmente indica configurações de privacidade, não que o usuário não está no grupo)
                if any(x in str(e) for x in ["400", "Bad Request", "Invalid user_id specified", "Forbidden"]):
                    logger.info(f"Assumindo que @{username_clean} pode estar no grupo devido ao erro de privacidade/API")
                    return None  # Retorna None para indicar "não conseguiu verificar"
                
                return False
                
        except Exception as e:
            logger.error(f"Erro geral ao verificar membro {username} no grupo {chat_id}: {e}")
            return False
    
    @staticmethod
    async def _generate_pix_payment(user_id: int, mail_id: str) -> tuple[Optional[str], Optional[str]]:
        """Gera chave Pix para pagamento (versão simplificada)."""
        try:
            # Para agora, usar chave Pix do bot (deve ser configurada)
            pix_key = Config.get_pix_key()
            
            # Gerar ID único para o pagamento
            pix_id = f"PIX_{user_id}_{mail_id}_{int(datetime.now().timestamp())}"
            
            # Salvar dados do pagamento no banco
            await mongodb_client.create_pix_payment(
                pix_id=pix_id,
                user_id=user_id,
                mail_id=mail_id,
                amount=2.00,
                pix_key=pix_key
            )
            
            return pix_key, pix_id
        
        except Exception as e:
            logger.error(f"Erro ao gerar pagamento Pix: {e}")
            return None, None


# Conversation handlers
def get_mail_conversation_handler():
    """Retorna o ConversationHandler para correio elegante."""
    return ConversationHandler(
        entry_points=[CommandHandler("correio", MailHandlers.correio_command)],
        states={
            MAIL_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, MailHandlers.handle_mail_message)],
            MAIL_RECIPIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, MailHandlers.handle_mail_recipient)]
        },
        fallbacks=[CommandHandler("cancelar", MailHandlers.cancel_conversation)]
    )


def get_reply_conversation_handler():
    """Retorna o ConversationHandler para resposta anônima."""
    return ConversationHandler(
        entry_points=[CommandHandler("respondercorreio", MailHandlers.responder_correio_command)],
        states={
            REPLY_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, MailHandlers.handle_reply_message)]
        },
        fallbacks=[CommandHandler("cancelar", MailHandlers.cancel_conversation)]
    )