"""
Agendador para publicação automática de correios elegantes.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from src.utils.mongodb_instance import mongodb_client
from src.utils.config import Config

logger = logging.getLogger(__name__)


class MailScheduler:
    """Agendador para publicação automática de correios elegantes."""
    
    def __init__(self, bot: Bot):
        """
        Inicializa o agendador.
        
        Args:
            bot (Bot): Instância do bot Telegram.
        """
        self.bot = bot
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
    
    async def start(self, interval_minutes: int = 60) -> None:
        """
        Inicia o agendador.
        
        Args:
            interval_minutes (int): Intervalo em minutos para verificar correios pendentes.
        """
        if self.is_running:
            logger.warning("Agendador de correio já está em execução.")
            return
        
        self.is_running = True
        self.task = asyncio.create_task(self._run_scheduler(interval_minutes))
        logger.info(f"Agendador de correio iniciado. Intervalo: {interval_minutes} minutos.")
    
    async def stop(self) -> None:
        """Para o agendador."""
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Agendador de correio parado.")
    
    async def _run_scheduler(self, interval_minutes: int) -> None:
        """Loop principal do agendador."""
        logger.info(f"Agendador iniciado. Próxima execução em {interval_minutes} minutos.")
        
        while self.is_running:
            try:
                # Aguardar o intervalo ANTES de processar (não imediatamente)
                await asyncio.sleep(interval_minutes * 60)  # Converter para segundos
                
                # Verificar se ainda está rodando após o sleep
                if not self.is_running:
                    break
                    
                await self._process_pending_mails()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no agendador de correio: {e}")
                await asyncio.sleep(60)  # Aguardar 1 minuto antes de tentar novamente
    
    async def _process_pending_mails(self) -> None:
        """Processa e publica correios pendentes."""
        try:
            # Obter correios pendentes
            pending_mails = await mongodb_client.get_pending_mails()
            
            if not pending_mails:
                logger.debug("Nenhum correio pendente encontrado.")
                return
            
            # Obter chat_id do GYM NATION
            gym_nation_chat_id = await mongodb_client.get_gym_nation_chat_id()
            if not gym_nation_chat_id:
                logger.error("Chat do GYM NATION não encontrado. Correios não podem ser publicados.")
                return
            
            logger.info(f"Processando {len(pending_mails)} correios pendentes.")
            
            for mail in pending_mails:
                try:
                    await self._publish_mail(mail, gym_nation_chat_id)
                    await asyncio.sleep(2)  # Evitar spam
                except Exception as e:
                    logger.error(f"Erro ao publicar correio {mail['_id']}: {e}")
        
        except Exception as e:
            logger.error(f"Erro ao processar correios pendentes: {e}")
    
    async def _publish_mail(self, mail: Dict[str, Any], chat_id: int) -> None:
        """
        Publica um correio específico no grupo.
        
        Args:
            mail (Dict[str, Any]): Dados do correio.
            chat_id (int): ID do chat onde publicar.
        """
        try:
            mail_id = str(mail['_id'])
            recipient_username = mail['recipient_username']
            message_text = mail['message_text']
            
            # Montar mensagem do correio
            mail_message = (
                f"📬 *CORREIO ELEGANTE* 💌💚\n\n"
                f"*Para:* @{recipient_username}\n\n"
                f"💭 _{message_text}_\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"_Mensagem anônima • Expira em 24h_\n\n"
                f"💡 *Interaja com este correio usando os botões abaixo:*"
            )
            
            # Criar botões para interagir com o correio
            bot_username = Config.get_bot_username()
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔍 Descobrir remetente (R$ 2,00)", 
                    url=f"https://t.me/{bot_username}?start=revelar_{mail_id}"
                )],
                [InlineKeyboardButton(
                    "💌 Responder anonimamente", 
                    url=f"https://t.me/{bot_username}?start=responder_{mail_id}"
                )],
                [InlineKeyboardButton(
                    "🚨 Denunciar conteúdo", 
                    url=f"https://t.me/{bot_username}?start=denunciar_{mail_id}"
                )]
            ])
            
            # Enviar mensagem com botão
            sent_message = await self.bot.send_message(
                chat_id=chat_id,
                text=mail_message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
            
            # Marcar como publicado no banco de dados
            success = await mongodb_client.publish_mail(mail_id, sent_message.message_id)
            
            if success:
                logger.info(f"Correio {mail_id} publicado com sucesso.")
            else:
                logger.error(f"Erro ao marcar correio {mail_id} como publicado no banco.")
        
        except Exception as e:
            logger.error(f"Erro ao publicar correio {mail['_id']}: {e}")
    
    async def cleanup_expired_mails(self) -> None:
        """Remove correios expirados (função auxiliar para limpeza)."""
        try:
            # Esta função pode ser chamada separadamente para limpeza
            # Por enquanto, apenas log - a limpeza é feita automaticamente nas consultas
            logger.info("Limpeza de correios expirados executada.")
        except Exception as e:
            logger.error(f"Erro na limpeza de correios expirados: {e}")


# Instância global do agendador
mail_scheduler: Optional[MailScheduler] = None


async def start_mail_scheduler(bot: Bot, interval_minutes: int = 60, process_immediately: bool = False) -> None:
    """
    Inicia o agendador de correio global.
    
    Args:
        bot (Bot): Instância do bot.
        interval_minutes (int): Intervalo em minutos.
        process_immediately (bool): Se True, processa correios pendentes imediatamente na inicialização.
    """
    global mail_scheduler
    
    if mail_scheduler is None:
        mail_scheduler = MailScheduler(bot)
    
    # Se solicitado, processar correios pendentes imediatamente
    if process_immediately:
        logger.info("Processando correios pendentes imediatamente na inicialização...")
        try:
            await mail_scheduler._process_pending_mails()
        except Exception as e:
            logger.error(f"Erro ao processar correios pendentes na inicialização: {e}")
    
    await mail_scheduler.start(interval_minutes)


async def stop_mail_scheduler() -> None:
    """Para o agendador de correio global."""
    global mail_scheduler
    
    if mail_scheduler:
        await mail_scheduler.stop()


async def publish_mail_by_id(mail_id: str) -> bool:
    """
    Publica um correio específico imediatamente.
    
    Args:
        mail_id (str): ID do correio a ser publicado.
        
    Returns:
        bool: True se publicado com sucesso.
    """
    global mail_scheduler
    
    if not mail_scheduler:
        logger.error("Agendador de correio não inicializado.")
        return False
    
    try:
        # Buscar o correio no banco
        from src.utils.mongodb_instance import mongodb_client
        
        mail = await mongodb_client.get_mail_by_id(mail_id)
        if not mail:
            logger.error(f"Correio {mail_id} não encontrado.")
            return False
        
        if mail.get('status') != 'pending':
            logger.error(f"Correio {mail_id} não está pendente (status: {mail.get('status')}).")
            return False
        
        # Obter chat_id do GYM NATION
        gym_nation_chat_id = await mongodb_client.get_gym_nation_chat_id()
        if not gym_nation_chat_id:
            logger.error("Chat do GYM NATION não encontrado. Correio não pode ser publicado.")
            return False
        
        # Publicar o correio
        await mail_scheduler._publish_mail(mail, gym_nation_chat_id)
        
        logger.info(f"Correio {mail_id} publicado manualmente com sucesso.")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao publicar correio {mail_id}: {e}")
        return False


async def publish_all_pending_mails() -> int:
    """
    Publica todos os correios pendentes imediatamente.
    
    Returns:
        int: Número de correios publicados.
    """
    global mail_scheduler
    
    if not mail_scheduler:
        logger.error("Agendador de correio não inicializado.")
        return 0
    
    try:
        # Forçar processamento de correios pendentes
        await mail_scheduler._process_pending_mails()
        
        # Contar quantos foram processados
        from src.utils.mongodb_instance import mongodb_client
        remaining_pending = await mongodb_client.get_pending_mails()
        
        logger.info("Todos os correios pendentes foram processados manualmente.")
        return len(remaining_pending)
        
    except Exception as e:
        logger.error(f"Erro ao publicar todos os correios pendentes: {e}")
        return 0 