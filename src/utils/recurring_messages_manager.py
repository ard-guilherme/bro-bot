"""
Gerenciador de mensagens recorrentes.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import math

from telegram.ext import Application
from src.utils.mongodb_instance import mongodb_client

logger = logging.getLogger(__name__)

class RecurringMessagesManager:
    """Gerenciador de mensagens recorrentes."""
    
    def __init__(self, application: Application):
        """
        Inicializa o gerenciador de mensagens recorrentes.
        
        Args:
            application (Application): Aplicação do Telegram.
        """
        self.application = application
        self.scheduled_tasks = {}  # Dicionário para armazenar as tarefas agendadas
        self.running = False
    
    async def start(self):
        """Inicia o gerenciador de mensagens recorrentes."""
        if self.running:
            return
            
        self.running = True
        logger.info("Iniciando gerenciador de mensagens recorrentes...")
        
        # Carrega todas as mensagens recorrentes ativas
        await self.load_recurring_messages()
        
        # Inicia uma tarefa para verificar periodicamente novas mensagens
        asyncio.create_task(self._check_for_new_messages())
    
    async def stop(self):
        """Para o gerenciador de mensagens recorrentes."""
        self.running = False
        logger.info("Parando gerenciador de mensagens recorrentes...")
        
        # Cancela todas as tarefas agendadas
        for task in self.scheduled_tasks.values():
            task.cancel()
        
        self.scheduled_tasks = {}
    
    async def load_recurring_messages(self):
        """Carrega todas as mensagens recorrentes ativas do banco de dados."""
        if mongodb_client.db is None:
            logger.warning("MongoDB não está conectado. Não é possível carregar mensagens recorrentes.")
            return
            
        messages = await mongodb_client.get_all_active_recurring_messages()
        logger.info(f"Carregadas {len(messages)} mensagens recorrentes ativas.")
        
        for message in messages:
            self._schedule_message(message)  # Removido o await, pois _schedule_message não é assíncrono
    
    async def add_recurring_message(
        self,
        chat_id: int,
        message: str,
        interval_hours: float,
        added_by: int,
        added_by_name: str
    ) -> Optional[str]:
        """
        Adiciona uma nova mensagem recorrente.
        
        Args:
            chat_id (int): ID do chat onde a mensagem será enviada.
            message (str): Texto da mensagem.
            interval_hours (float): Intervalo em horas entre os envios.
            added_by (int): ID do usuário que adicionou a mensagem.
            added_by_name (str): Nome do usuário que adicionou a mensagem.
            
        Returns:
            Optional[str]: ID da mensagem adicionada, ou None se falhou.
        """
        try:
            # Adiciona a mensagem ao banco de dados
            message_id = await mongodb_client.add_recurring_message(
                chat_id, message, interval_hours, added_by, added_by_name
            )
            
            if message_id:
                # Obtém os dados da mensagem
                message_data = await mongodb_client.get_recurring_message(message_id)
                
                if message_data:
                    # Agenda a mensagem para envio
                    self._schedule_message(message_data)
                    logger.info(f"Mensagem recorrente adicionada com sucesso: {message_id}")
                    return message_id
            
            return None
        except Exception as e:
            logger.error(f"Erro ao adicionar mensagem recorrente: {e}")
            return None
    
    async def delete_recurring_message(self, message_id: str) -> bool:
        """
        Desativa uma mensagem recorrente.
        
        Args:
            message_id (str): ID da mensagem recorrente.
            
        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário.
        """
        if mongodb_client.db is None:
            logger.warning("MongoDB não está conectado. Não é possível desativar mensagem recorrente.")
            return False
            
        result = await mongodb_client.delete_recurring_message(message_id)
        
        if result and message_id in self.scheduled_tasks:
            # Cancela a tarefa agendada
            self.scheduled_tasks[message_id].cancel()
            del self.scheduled_tasks[message_id]
            logger.info(f"Mensagem recorrente desativada com sucesso: {message_id}")
        
        return result
    
    async def get_recurring_messages(self, chat_id: int) -> List[Dict]:
        """
        Obtém todas as mensagens recorrentes de um chat.
        
        Args:
            chat_id (int): ID do chat.
            
        Returns:
            List[Dict]: Lista de mensagens recorrentes.
        """
        if mongodb_client.db is None:
            logger.warning("MongoDB não está conectado. Não é possível obter mensagens recorrentes.")
            return []
            
        return await mongodb_client.get_recurring_messages_by_chat(chat_id)
    
    def _schedule_message(self, message_data: Dict) -> None:
        """
        Agenda uma mensagem recorrente para envio.
        
        Args:
            message_data (dict): Dados da mensagem recorrente.
        """
        message_id = str(message_data["_id"])
        
        # Cancela qualquer tarefa existente para esta mensagem
        if message_id in self.scheduled_tasks:
            self.scheduled_tasks[message_id].cancel()
            logger.info(f"Envio da mensagem recorrente {message_id} cancelado.")
        
        # Calcula o próximo horário de envio
        next_send_time = self._calculate_next_send_time(message_data)
        
        # Calcula o atraso em segundos
        now = datetime.now()
        delay = (next_send_time - now).total_seconds()
        delay = max(1.0, delay)  # Garante que o atraso seja de pelo menos 1 segundo
        
        # Log detalhado para debug
        last_sent = message_data.get("last_sent_at")
        interval = message_data.get("interval_hours", 1.0)
        last_sent_str = last_sent.strftime('%Y-%m-%d %H:%M:%S') if last_sent else "Nunca"
        
        logger.info(
            f"Detalhes do agendamento para mensagem {message_id}:\n"
            f"- Texto: '{message_data.get('message')[:30]}...'\n"
            f"- Chat ID: {message_data.get('chat_id')}\n"
            f"- Intervalo: {interval} horas\n"
            f"- Último envio: {last_sent_str}\n"
            f"- Hora atual: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"- Próximo envio: {next_send_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"- Atraso calculado: {delay:.2f} segundos"
        )
        
        # Cria uma nova tarefa para enviar a mensagem
        task = asyncio.create_task(
            self._send_message_after_delay(message_data, delay)
        )
        
        # Armazena a tarefa
        self.scheduled_tasks[message_id] = task
        
        # Registra o agendamento
        logger.info(
            f"Mensagem recorrente agendada: {message_id}, "
            f"próximo envio em {delay:.2f} segundos ({next_send_time.strftime('%Y-%m-%d %H:%M:%S')})"
        )
    
    def _calculate_next_send_time(self, message_data: Dict) -> datetime:
        """
        Calcula o próximo horário de envio para uma mensagem recorrente.
        
        Args:
            message_data (Dict): Dados da mensagem recorrente.
            
        Returns:
            datetime: Próximo horário de envio.
        """
        interval_hours = message_data.get("interval_hours", 1.0)
        last_sent_at = message_data.get("last_sent_at")
        
        now = datetime.now()
        
        # Se a mensagem nunca foi enviada, agende para agora + 1 minuto
        if last_sent_at is None:
            return now + timedelta(minutes=1)
            
        # Calcula o próximo horário de envio com base no último envio
        next_send_time = last_sent_at + timedelta(hours=interval_hours)
        
        # Se o próximo horário de envio já passou, agende para agora + intervalo
        if next_send_time <= now:
            # Calcular quantos intervalos já passaram desde o último envio
            hours_since_last_send = (now - last_sent_at).total_seconds() / 3600
            intervals_passed = math.ceil(hours_since_last_send / interval_hours)
            
            # Agendar para o próximo intervalo a partir do último envio
            return last_sent_at + timedelta(hours=interval_hours * intervals_passed)
        
        return next_send_time
    
    async def _send_message_after_delay(self, message_data: Dict, delay_seconds: float):
        """
        Envia uma mensagem recorrente após um determinado tempo.
        
        Args:
            message_data (Dict): Dados da mensagem recorrente.
            delay_seconds (float): Tempo de espera em segundos.
        """
        try:
            message_id = str(message_data["_id"])
            
            # Aguarda o tempo especificado
            await asyncio.sleep(delay_seconds)
            
            # Obtém os dados atualizados da mensagem
            updated_message_data = await mongodb_client.get_recurring_message(message_id)
            
            if not updated_message_data or not updated_message_data.get("active", False):
                logger.info(f"Mensagem recorrente {message_id} não está mais ativa.")
                if message_id in self.scheduled_tasks:
                    del self.scheduled_tasks[message_id]
                return
            
            # Verifica se o horário de envio ainda é válido
            last_sent_at = updated_message_data.get("last_sent_at")
            interval_hours = updated_message_data.get("interval_hours", 1.0)
            
            now = datetime.now()
            
            # Se já foi enviada e ainda não passou tempo suficiente, reagenda
            if last_sent_at and (now - last_sent_at).total_seconds() < interval_hours * 3600 * 0.9:
                next_time = self._calculate_next_send_time(updated_message_data)
                new_delay = max(1.0, (next_time - now).total_seconds())
                
                logger.info(f"Mensagem {message_id} foi enviada recentemente. Reagendando para {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                task = asyncio.create_task(
                    self._send_message_after_delay(updated_message_data, new_delay)
                )
                self.scheduled_tasks[message_id] = task
                return
            
            # Envia a mensagem
            chat_id = updated_message_data["chat_id"]
            message_text = updated_message_data["message"]
            
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=f"🟢 *MENSAGEM DA ADMINISTRAÇÃO* 🟢\n\n{message_text}",
                parse_mode="Markdown"
            )
            
            logger.info(f"Mensagem recorrente enviada: {message_id}")
            
            # Atualiza o timestamp de envio
            await mongodb_client.update_recurring_message_last_sent(message_id)
            
            # Agenda o próximo envio
            self._schedule_message(updated_message_data)
            
        except asyncio.CancelledError:
            logger.info(f"Envio da mensagem recorrente {str(message_data['_id'])} cancelado.")
        except Exception as e:
            message_id = str(message_data["_id"])
            logger.error(f"Erro ao enviar mensagem recorrente {message_id}: {e}")
            
            # Tenta reagendar mesmo em caso de erro
            try:
                updated_message_data = await mongodb_client.get_recurring_message(message_id)
                if updated_message_data and updated_message_data.get("active", False):
                    # Agenda para tentar novamente em 5 minutos
                    task = asyncio.create_task(
                        self._send_message_after_delay(updated_message_data, 300)  # 5 minutos
                    )
                    self.scheduled_tasks[message_id] = task
            except Exception as e2:
                logger.error(f"Erro ao reagendar mensagem recorrente {message_id}: {e2}")
    
    async def _check_for_new_messages(self):
        """Verifica periodicamente se há novas mensagens recorrentes."""
        while self.running:
            try:
                # Aguarda 5 minutos entre as verificações
                await asyncio.sleep(300)
                
                if not self.running:
                    break
                
                # Carrega todas as mensagens recorrentes ativas
                messages = await mongodb_client.get_all_active_recurring_messages()
                
                # Verifica se há novas mensagens ou mensagens que não estão agendadas
                for message in messages:
                    message_id = str(message["_id"])
                    if message_id not in self.scheduled_tasks:
                        self._schedule_message(message)  # Removido o await, pois _schedule_message não é assíncrono
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro ao verificar novas mensagens recorrentes: {e}")

# Instância global do gerenciador
recurring_messages_manager = None

def initialize_recurring_messages_manager(application: Application):
    """
    Inicializa o gerenciador de mensagens recorrentes.
    
    Args:
        application (Application): Aplicação do Telegram.
    """
    global recurring_messages_manager
    recurring_messages_manager = RecurringMessagesManager(application)
    return recurring_messages_manager 