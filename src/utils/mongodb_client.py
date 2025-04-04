"""
Cliente para o MongoDB.
"""
import os
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import motor.motor_asyncio
from pymongo.errors import PyMongoError
import re

logger = logging.getLogger(__name__)

class MongoDBClient:
    """Cliente para o MongoDB."""
    
    def __init__(self, connection_string: Optional[str] = None):
        """
        Inicializa o cliente do MongoDB.
        
        Args:
            connection_string (Optional[str]): String de conexão com o MongoDB.
                                              Se não for fornecida, será buscada na variável
                                              de ambiente MONGODB_CONNECTION_STRING.
        """
        self.connection_string = connection_string or os.getenv(
            "MONGODB_CONNECTION_STRING", 
            "mongodb://admin:password@localhost:27017"
        )
        self.client = None
        self.db = None
        
    async def connect(self, db_name: str = "gym_nation_bot"):
        """
        Conecta ao banco de dados MongoDB.
        
        Args:
            db_name (str): Nome do banco de dados.
        """
        try:
            self.client = motor.motor_asyncio.AsyncIOMotorClient(self.connection_string)
            # Armazena o nome do banco padrão e define o objeto db
            self.db_name = db_name
            self.db = self.client[db_name]
            logger.info(f"Conectado ao MongoDB: {db_name}")
        except PyMongoError as e:
            logger.error(f"Erro ao conectar ao MongoDB: {e}")
            raise
    
    async def close(self):
        """Fecha a conexão com o MongoDB."""
        if self.client:
            self.client.close()
            logger.info("Conexão com o MongoDB fechada")
    
    # Métodos para gerenciar o check-in
    
    async def set_checkin_anchor(self, chat_id: int, message_id: int) -> bool:
        """
        Define uma mensagem como âncora de check-in.
        
        Args:
            chat_id (int): ID do chat.
            message_id (int): ID da mensagem âncora.
            
        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário.
        """
        try:
            # Primeiro, desativa qualquer check-in ativo
            await self.end_checkin(chat_id)
            
            # Define o novo check-in
            result = await self.db.checkin_anchors.insert_one({
                "chat_id": chat_id,
                "message_id": message_id,
                "created_at": datetime.now(),
                "active": True
            })
            
            return result.acknowledged
        except PyMongoError as e:
            logger.error(f"Erro ao definir âncora de check-in: {e}")
            return False
    
    async def end_checkin(self, chat_id: int) -> bool:
        """
        Desativa o check-in atual.
        
        Args:
            chat_id (int): ID do chat.
            
        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário.
        """
        try:
            result = await self.db.checkin_anchors.update_many(
                {"chat_id": chat_id, "active": True},
                {"$set": {"active": False}}
            )
            
            return result.acknowledged
        except PyMongoError as e:
            logger.error(f"Erro ao desativar check-in: {e}")
            return False
    
    async def get_anchor_checkin_count(self, chat_id: int, anchor_id: str) -> int:
        """
        Obtém o número de check-ins para uma âncora específica.
        
        Args:
            chat_id (int): ID do chat.
            anchor_id (str): ID da âncora de check-in.
            
        Returns:
            int: Número de check-ins para a âncora.
        """
        try:
            count = await self.db.user_checkins.count_documents({
                "chat_id": chat_id,
                "anchor_id": anchor_id
            })
            
            return count
        except PyMongoError as e:
            logger.error(f"Erro ao obter contagem de check-ins para âncora: {e}")
            return 0
    
    async def get_active_checkin(self, chat_id: int) -> Optional[Dict]:
        """
        Obtém o check-in ativo para um chat.
        
        Args:
            chat_id (int): ID do chat.
            
        Returns:
            Optional[Dict]: Dicionário com os dados do check-in, ou None se não houver check-in ativo.
        """
        try:
            result = await self.db.checkin_anchors.find_one(
                {"chat_id": chat_id, "active": True}
            )
            
            return result
        except PyMongoError as e:
            logger.error(f"Erro ao obter check-in ativo: {e}")
            return None
    
    async def register_checkin(self, chat_id: int, user_id: int, user_name: str, message_id: int) -> bool:
        """
        Registra um check-in de um usuário.
        
        Args:
            chat_id (int): ID do chat.
            user_id (int): ID do usuário.
            user_name (str): Nome do usuário.
            message_id (int): ID da mensagem de check-in.
            
        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário.
        """
        try:
            # Verifica se existe um check-in ativo
            active_checkin = await self.get_active_checkin(chat_id)
            
            if not active_checkin:
                logger.warning(f"Tentativa de registro de check-in sem check-in ativo: chat_id={chat_id}, user_id={user_id}")
                return False
            
            anchor_id = active_checkin["_id"]
            
            # Verifica se o usuário já fez check-in neste check-in ativo
            existing_checkin = await self.db.checkins.find_one({
                "chat_id": chat_id,
                "user_id": user_id,
                "anchor_id": anchor_id
            })
            
            if existing_checkin:
                logger.info(f"Usuário já registrou check-in: chat_id={chat_id}, user_id={user_id}")
                return False
            
            # Registra o novo check-in
            result = await self.db.checkins.insert_one({
                "chat_id": chat_id,
                "user_id": user_id,
                "user_name": user_name,
                "message_id": message_id,
                "anchor_id": anchor_id,
                "created_at": datetime.now()
            })
            
            return result.acknowledged
        except PyMongoError as e:
            logger.error(f"Erro ao registrar check-in: {e}")
            return False
    
    async def get_checkin_count(self, chat_id: int, user_id: int) -> int:
        """
        Obtém o número de check-ins de um usuário em um chat.
        
        Args:
            chat_id (int): ID do chat.
            user_id (int): ID do usuário.
            
        Returns:
            int: Número de check-ins do usuário.
        """
        try:
            count = await self.db.checkins.count_documents({
                "chat_id": chat_id,
                "user_id": user_id
            })
            
            return count
        except PyMongoError as e:
            logger.error(f"Erro ao obter contagem de check-ins: {e}")
            return 0
    
    async def get_checkin_ranking(self, chat_id: int, limit: int = 10) -> List[Dict]:
        """
        Obtém o ranking de check-ins para um chat.
        
        Args:
            chat_id (int): ID do chat.
            limit (int): Número máximo de usuários a serem retornados.
            
        Returns:
            List[Dict]: Lista de dicionários com os dados dos usuários e suas contagens de check-in.
        """
        try:
            pipeline = [
                {"$match": {"chat_id": chat_id}},
                {"$group": {
                    "_id": {"user_id": "$user_id", "user_name": "$user_name"},
                    "count": {"$sum": 1},
                    "last_checkin": {"$max": "$created_at"}
                }},
                {"$sort": {"count": -1, "last_checkin": -1}},
                {"$limit": limit},
                {"$project": {
                    "user_id": "$_id.user_id",
                    "user_name": "$_id.user_name",
                    "count": 1,
                    "last_checkin": 1,
                    "_id": 0
                }}
            ]
            
            result = []
            async for doc in self.db.checkins.aggregate(pipeline):
                result.append(doc)
            
            return result
        except PyMongoError as e:
            logger.error(f"Erro ao obter ranking de check-ins: {e}")
            return []
    
    async def confirm_manual_checkin(self, chat_id: int, user_id: int, user_name: str) -> bool:
        """
        Confirma manualmente o check-in de um usuário.
        
        Args:
            chat_id (int): ID do chat.
            user_id (int): ID do usuário.
            user_name (str): Nome do usuário.
            
        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário.
        """
        try:
            # Verifica se existe um check-in ativo
            active_checkin = await self.get_active_checkin(chat_id)
            
            if not active_checkin:
                logger.warning(f"Tentativa de confirmação manual de check-in sem check-in ativo: chat_id={chat_id}, user_id={user_id}")
                return False
            
            anchor_id = active_checkin["_id"]
            
            # Verifica se o usuário já fez check-in neste check-in ativo
            existing_checkin = await self.db.checkins.find_one({
                "chat_id": chat_id,
                "user_id": user_id,
                "anchor_id": anchor_id
            })
            
            if existing_checkin:
                logger.info(f"Usuário já registrou check-in: chat_id={chat_id}, user_id={user_id}")
                return False
            
            # Registra o novo check-in
            result = await self.db.checkins.insert_one({
                "chat_id": chat_id,
                "user_id": user_id,
                "user_name": user_name,
                "message_id": None,  # Check-in manual não tem mensagem associada
                "anchor_id": anchor_id,
                "created_at": datetime.now(),
                "manual": True  # Marca como check-in manual
            })
            
            return result.acknowledged
        except PyMongoError as e:
            logger.error(f"Erro ao confirmar check-in manual: {e}")
            return False
    
    async def record_user_checkin(self, chat_id: int, user_id: int, user_name: str, username: str = None) -> Optional[int]:
        """
        Registra um check-in de um usuário.
        
        Args:
            chat_id (int): ID do chat.
            user_id (int): ID do usuário.
            user_name (str): Nome do usuário.
            username (str, optional): Nome de usuário (@username) do Telegram.
            
        Returns:
            Optional[int]: Número total de check-ins do usuário, ou None se falhar.
        """
        try:
            # Verifica se existe um check-in ativo
            active_checkin = await self.get_active_checkin(chat_id)
            
            if not active_checkin:
                logger.warning(f"Tentativa de registro de check-in sem check-in ativo: chat_id={chat_id}, user_id={user_id}")
                return None
            
            anchor_id = active_checkin["_id"]
            
            # Verifica se o usuário já fez check-in neste check-in ativo
            existing_checkin = await self.db.user_checkins.find_one({
                "chat_id": chat_id,
                "user_id": user_id,
                "anchor_id": anchor_id
            })
            
            if existing_checkin:
                logger.info(f"Usuário já registrou check-in: chat_id={chat_id}, user_id={user_id}")
                return None
            
            # Registra o novo check-in
            checkin_doc = {
                "chat_id": chat_id,
                "user_id": user_id,
                "user_name": user_name,
                "anchor_id": anchor_id,
                "created_at": datetime.now()
            }
            
            # Adiciona o username se disponível
            if username:
                checkin_doc["username"] = username
                
            await self.db.user_checkins.insert_one(checkin_doc)
            
            # Atualiza também o username em todos os check-ins anteriores deste usuário
            # para que o scoreboard mostre sempre o username mais recente
            if username:
                await self.db.user_checkins.update_many(
                    {"chat_id": chat_id, "user_id": user_id, "username": {"$exists": False}},
                    {"$set": {"username": username}}
                )
            
            # Conta o número total de check-ins do usuário
            count = await self.db.user_checkins.count_documents({
                "chat_id": chat_id,
                "user_id": user_id
            })
            
            return count
        except PyMongoError as e:
            logger.error(f"Erro ao registrar check-in: {e}")
            return None
    
    async def get_checkin_scoreboard(self, chat_id: int) -> List[Dict[str, Any]]:
        """
        Obtém o placar de check-ins para um chat específico.
        
        Args:
            chat_id (int): ID do chat.
            
        Returns:
            List[Dict[str, Any]]: Lista de usuários com suas contagens de check-in, ordenada por contagem.
        """
        try:
            # Obtém a lista de usuários únicos que fizeram check-in neste chat
            user_ids = await self.db.user_checkins.distinct("user_id", {"chat_id": chat_id})
            
            scoreboard = []
            for user_id in user_ids:
                # Obtém o check-in mais recente do usuário para ter os dados mais atualizados
                user_info = await self.db.user_checkins.find_one(
                    {"user_id": user_id, "chat_id": chat_id},
                    sort=[("created_at", -1)]  # Ordenar pelo mais recente
                )
                
                if user_info:
                    # Conta o número de check-ins do usuário
                    count = await self.db.user_checkins.count_documents({
                        "chat_id": chat_id,
                        "user_id": user_id
                    })
                    
                    # Obtém o nome de usuário (username) do Telegram, se disponível
                    username = user_info.get("username", None)
                    user_name = user_info.get("user_name", f"Usuário {user_id}")
                    
                    # Adiciona ao placar
                    scoreboard.append({
                        "user_id": user_id,
                        "user_name": user_name,
                        "username": username,  # Pode ser None se não estiver disponível
                        "count": count
                    })
            
            # Ordena o placar por contagem (decrescente)
            scoreboard.sort(key=lambda x: x["count"], reverse=True)
            
            return scoreboard
        except PyMongoError as e:
            logger.error(f"Erro ao obter placar de check-ins: {e}")
            return []
    
    async def get_total_checkin_participants(self, chat_id: int) -> int:
        """
        Obtém o número total de participantes distintos que já fizeram check-in no chat.
        
        Args:
            chat_id (int): ID do chat.
            
        Returns:
            int: Número de participantes distintos.
        """
        try:
            # Conta o número de usuários distintos que fizeram check-in
            user_ids = await self.db.user_checkins.distinct("user_id", {"chat_id": chat_id})
            return len(user_ids)
        except PyMongoError as e:
            logger.error(f"Erro ao obter total de participantes de check-in: {e}")
            return 0
    
    async def get_first_checkin_date(self, chat_id: int) -> Optional[datetime]:
        """
        Obtém a data do primeiro check-in registrado no chat.
        
        Args:
            chat_id (int): ID do chat.
            
        Returns:
            Optional[datetime]: Data do primeiro check-in ou None se não houver check-ins.
        """
        try:
            # Busca o check-in mais antigo
            first_checkin = await self.db.user_checkins.find_one(
                {"chat_id": chat_id},
                sort=[("created_at", 1)]  # Ordena por data de criação (ascendente)
            )
            
            if first_checkin:
                return first_checkin.get("created_at")
            return None
        except PyMongoError as e:
            logger.error(f"Erro ao obter data do primeiro check-in: {e}")
            return None
    
    async def count_total_checkins(self, chat_id: int) -> int:
        """
        Conta o número total de check-ins registrados em um chat.
        
        Args:
            chat_id (int): ID do chat.
            
        Returns:
            int: Número total de check-ins.
        """
        try:
            count = await self.db.user_checkins.count_documents({"chat_id": chat_id})
            return count
        except PyMongoError as e:
            logger.error(f"Erro ao contar total de check-ins: {e}")
            return 0
    
    async def get_user_checkin_count(self, chat_id: int, user_id: int) -> int:
        """
        Obtém o número de check-ins de um usuário em um chat específico.
        
        Args:
            chat_id (int): ID do chat.
            user_id (int): ID do usuário.
            
        Returns:
            int: Número de check-ins do usuário.
        """
        try:
            count = await self.db.user_checkins.count_documents({
                "chat_id": chat_id,
                "user_id": user_id
            })
            
            return count
        except PyMongoError as e:
            logger.error(f"Erro ao obter contagem de check-ins do usuário: {e}")
            return 0
    
    # Métodos para gerenciar administradores
    
    async def add_admin(self, admin_id: int, admin_name: str, added_by: int) -> bool:
        """
        Adiciona um usuário como administrador do bot.
        
        Args:
            admin_id (int): ID do usuário a ser adicionado como administrador.
            admin_name (str): Nome do usuário.
            added_by (int): ID do usuário que adicionou o administrador.
            
        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário.
        """
        try:
            # Verifica se o administrador já existe
            existing_admin = await self.db.bot_admins.find_one({"admin_id": admin_id})
            
            if existing_admin:
                return False  # Admin já existe
            
            # Adiciona o novo administrador
            result = await self.db.bot_admins.insert_one({
                "admin_id": admin_id,
                "admin_name": admin_name,
                "added_by": added_by,
                "added_at": datetime.now()
            })
            
            return result.acknowledged
        except PyMongoError as e:
            logger.error(f"Erro ao adicionar administrador: {e}")
            return False
    
    async def remove_admin(self, admin_id: int) -> bool:
        """
        Remove um usuário da lista de administradores.
        
        Args:
            admin_id (int): ID do usuário a ser removido.
            
        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário.
        """
        try:
            result = await self.db.bot_admins.delete_one({"admin_id": admin_id})
            
            return result.deleted_count > 0
        except PyMongoError as e:
            logger.error(f"Erro ao remover administrador: {e}")
            return False
    
    async def get_admins(self) -> List[Dict]:
        """
        Obtém a lista de administradores.
        
        Returns:
            List[Dict]: Lista de administradores.
        """
        try:
            admins = []
            cursor = self.db.bot_admins.find()
            
            async for doc in cursor:
                admins.append(doc)
            
            return admins
        except PyMongoError as e:
            logger.error(f"Erro ao obter administradores: {e}")
            return []
    
    async def is_admin(self, user_id: int) -> bool:
        """
        Verifica se um usuário é administrador.
        
        Args:
            user_id (int): ID do usuário a ser verificado.
            
        Returns:
            bool: True se o usuário é administrador, False caso contrário.
        """
        try:
            admin = await self.db.bot_admins.find_one({"admin_id": user_id})
            
            return admin is not None
        except PyMongoError as e:
            logger.error(f"Erro ao verificar administrador: {e}")
            return False
            
    # Métodos para gerenciar interações Q&A
    
    async def store_qa_interaction(
        self, 
        qa_interaction: Dict[str, Any]
    ) -> bool:
        """
        Armazena uma interação de pergunta e resposta.
        
        Args:
            qa_interaction (Dict[str, Any]): Dicionário contendo os dados da interação.
                Deve conter as chaves: chat_id, message_id, user_id, question, answer, category.
            
        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário.
        """
        try:
            # Adiciona o timestamp se não existir
            if "timestamp" not in qa_interaction:
                qa_interaction["timestamp"] = datetime.now()
                
            # Adiciona o campo feedback como None se não existir
            if "feedback" not in qa_interaction:
                qa_interaction["feedback"] = None
                
            result = await self.db.qa_interactions.insert_one(qa_interaction)
            
            return result.acknowledged
        except Exception as e:
            logging.error(f"Erro ao armazenar interação Q&A: {e}")
            return False
    
    async def store_qa_feedback(
        self, 
        chat_id: int, 
        message_id: int, 
        feedback: str
    ) -> bool:
        """
        Armazena feedback para uma resposta.
        
        Args:
            chat_id (int): ID do chat.
            message_id (int): ID da mensagem de resposta.
            feedback (str): Tipo de feedback ("positive" ou "negative").
            
        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário.
        """
        try:
            result = await self.db.qa_interactions.update_one(
                {"chat_id": chat_id, "message_id": message_id},
                {"$set": {"feedback": feedback, "feedback_at": datetime.now()}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logging.error(f"Erro ao armazenar feedback: {e}")
            return False

    async def get_qa_interaction(self, chat_id: int, message_id: int) -> Optional[dict]:
        """
        Obtém uma interação de pergunta e resposta.
        
        Args:
            chat_id (int): ID do chat.
            message_id (int): ID da mensagem de resposta.
            
        Returns:
            Optional[dict]: Dicionário contendo os dados da interação, ou None se não encontrado.
        """
        try:
            result = await self.db.qa_interactions.find_one(
                {"chat_id": chat_id, "message_id": message_id}
            )
            return result
        except Exception as e:
            logging.error(f"Erro ao obter interação Q&A: {e}")
            return None
    
    async def get_daily_qa_count(self, user_id: int, chat_id: int) -> int:
        """
        Obtém o número de perguntas feitas por um usuário em um chat no dia atual.
        
        Args:
            user_id (int): ID do usuário.
            chat_id (int): ID do chat.
            
        Returns:
            int: Número de perguntas feitas no dia atual.
        """
        try:
            # Define o início do dia atual
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Conta as interações do usuário no chat no dia atual
            count = await self.db.qa_usage.count_documents({
                "user_id": user_id,
                "chat_id": chat_id,
                "timestamp": {"$gte": today_start}
            })
            
            return count
        except Exception as e:
            logging.error(f"Erro ao obter contagem diária de Q&A: {e}")
            return 0
    
    async def get_last_qa_timestamp(self, user_id: int, chat_id: int) -> Optional[datetime]:
        """
        Obtém o timestamp da última pergunta feita por um usuário em um chat.
        
        Args:
            user_id (int): ID do usuário.
            chat_id (int): ID do chat.
            
        Returns:
            Optional[datetime]: Timestamp da última pergunta, ou None se não houver.
        """
        try:
            # Busca a última interação do usuário no chat
            result = await self.db.qa_usage.find_one(
                {"user_id": user_id, "chat_id": chat_id},
                sort=[("timestamp", -1)]  # Ordena por timestamp decrescente
            )
            
            if result:
                return result.get("timestamp")
            return None
        except Exception as e:
            logging.error(f"Erro ao obter timestamp da última Q&A: {e}")
            return None
    
    async def increment_qa_usage(self, user_id: int, chat_id: int) -> bool:
        """
        Incrementa o contador de uso de Q&A para um usuário em um chat.
        
        Args:
            user_id (int): ID do usuário.
            chat_id (int): ID do chat.
            
        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário.
        """
        try:
            result = await self.db.qa_usage.insert_one({
                "user_id": user_id,
                "chat_id": chat_id,
                "timestamp": datetime.now()
            })
            
            return result.acknowledged
        except Exception as e:
            logging.error(f"Erro ao incrementar uso de Q&A: {e}")
            return False
    
    def get_database(self):
        """
        Obtém a referência para o banco de dados padrão.
        
        Returns:
            Database: Objeto do banco de dados.
        """
        return self.db

    # Métodos para gerenciar o monitoramento de mensagens
    
    async def start_monitoring(self, chat_id: int, title: str = None, username: str = None) -> bool:
        """
        Inicia o monitoramento de mensagens em um chat.
        
        Args:
            chat_id (int): ID do chat a ser monitorado.
            title (str, optional): Título do grupo.
            username (str, optional): Username do grupo.
            
        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário.
        """
        try:
            # Verifica se já existe um monitoramento ativo
            existing = await self.db.monitored_chats.find_one({"chat_id": chat_id})
            
            if existing and existing.get("active", False):
                # Se já está sendo monitorado, atualiza o título e username se fornecidos
                if title or username:
                    update_data = {}
                    if title:
                        update_data["title"] = title
                    if username:
                        update_data["username"] = username
                    
                    if update_data:
                        await self.db.monitored_chats.update_one(
                            {"chat_id": chat_id},
                            {"$set": update_data}
                        )
                return True
                
            # Cria ou atualiza o registro
            update_data = {
                "active": True,
                "started_at": datetime.now()
            }
            
            # Adiciona título e username se fornecidos
            if title:
                update_data["title"] = title
            if username:
                update_data["username"] = username
            
            result = await self.db.monitored_chats.update_one(
                {"chat_id": chat_id},
                {"$set": update_data},
                upsert=True
            )
            
            return result.acknowledged
        except PyMongoError as e:
            logger.error(f"Erro ao iniciar monitoramento do chat {chat_id}: {e}")
            return False
    
    async def stop_monitoring(self, chat_id: int) -> bool:
        """
        Para o monitoramento de mensagens em um chat.
        
        Args:
            chat_id (int): ID do chat a parar de monitorar.
            
        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário.
        """
        try:
            result = await self.db.monitored_chats.update_one(
                {"chat_id": chat_id},
                {
                    "$set": {
                        "active": False,
                        "stopped_at": datetime.now()
                    }
                }
            )
            
            return result.acknowledged
        except PyMongoError as e:
            logger.error(f"Erro ao parar monitoramento do chat {chat_id}: {e}")
            return False
    
    async def is_chat_monitored(self, chat_id: int) -> bool:
        """
        Verifica se um chat está sendo monitorado.
        
        Args:
            chat_id (int): ID do chat.
            
        Returns:
            bool: True se o chat está sendo monitorado, False caso contrário.
        """
        try:
            chat = await self.db.monitored_chats.find_one({"chat_id": chat_id})
            return chat is not None and chat.get("active", False)
        except PyMongoError as e:
            logger.error(f"Erro ao verificar monitoramento do chat {chat_id}: {e}")
            return False
    
    async def store_message(self, chat_id: int, message_id: int, user_id: int, 
                           user_name: str, text: str, timestamp: datetime) -> bool:
        """
        Armazena uma mensagem de texto no banco de dados.
        
        Args:
            chat_id (int): ID do chat.
            message_id (int): ID da mensagem.
            user_id (int): ID do usuário que enviou a mensagem.
            user_name (str): Nome do usuário que enviou a mensagem.
            text (str): Texto da mensagem.
            timestamp (datetime): Data e hora da mensagem.
            
        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário.
        """
        try:
            result = await self.db.monitored_messages.insert_one({
                "chat_id": chat_id,
                "message_id": message_id,
                "user_id": user_id,
                "user_name": user_name,
                "text": text,
                "timestamp": timestamp
            })
            
            return result.acknowledged
        except PyMongoError as e:
            logger.error(f"Erro ao armazenar mensagem {message_id} do chat {chat_id}: {e}")
            return False

    # Métodos para gerenciar mensagens recorrentes
    
    async def add_recurring_message(
        self, 
        chat_id: int, 
        message: str, 
        interval_hours: float, 
        added_by: int,
        added_by_name: str
    ) -> Optional[str]:
        """
        Adiciona uma mensagem recorrente.
        
        Args:
            chat_id (int): ID do chat onde a mensagem será enviada.
            message (str): Texto da mensagem.
            interval_hours (float): Intervalo em horas entre as mensagens.
            added_by (int): ID do usuário que adicionou a mensagem.
            added_by_name (str): Nome do usuário que adicionou a mensagem.
            
        Returns:
            Optional[str]: ID da mensagem recorrente ou None se falhar.
        """
        try:
            result = await self.db.recurring_messages.insert_one({
                "chat_id": chat_id,
                "message": message,
                "interval_hours": interval_hours,
                "added_by": added_by,
                "added_by_name": added_by_name,
                "created_at": datetime.now(),
                "last_sent_at": None,
                "active": True
            })
            
            return str(result.inserted_id) if result.acknowledged else None
        except PyMongoError as e:
            logger.error(f"Erro ao adicionar mensagem recorrente: {e}")
            return None
    
    async def get_recurring_message(self, message_id: str) -> Optional[Dict]:
        """
        Obtém uma mensagem recorrente pelo ID.
        
        Args:
            message_id (str): ID da mensagem recorrente.
            
        Returns:
            Optional[Dict]: Dados da mensagem recorrente ou None se não encontrada.
        """
        try:
            from bson.objectid import ObjectId
            
            result = await self.db.recurring_messages.find_one({"_id": ObjectId(message_id)})
            return result
        except PyMongoError as e:
            logger.error(f"Erro ao obter mensagem recorrente: {e}")
            return None
    
    async def get_recurring_messages_by_chat(self, chat_id: int) -> List[Dict]:
        """
        Obtém todas as mensagens recorrentes de um chat.
        
        Args:
            chat_id (int): ID do chat.
            
        Returns:
            List[Dict]: Lista de mensagens recorrentes.
        """
        try:
            cursor = self.db.recurring_messages.find({"chat_id": chat_id, "active": True})
            messages = []
            async for doc in cursor:
                messages.append(doc)
            return messages
        except PyMongoError as e:
            logger.error(f"Erro ao obter mensagens recorrentes do chat {chat_id}: {e}")
            return []
    
    async def get_all_active_recurring_messages(self) -> List[Dict]:
        """
        Obtém todas as mensagens recorrentes ativas.
        
        Returns:
            List[Dict]: Lista de mensagens recorrentes ativas.
        """
        try:
            cursor = self.db.recurring_messages.find({"active": True})
            messages = []
            async for doc in cursor:
                messages.append(doc)
            return messages
        except PyMongoError as e:
            logger.error(f"Erro ao obter mensagens recorrentes ativas: {e}")
            return []
    
    async def update_recurring_message_last_sent(self, message_id: str) -> bool:
        """
        Atualiza o timestamp da última vez que a mensagem foi enviada.
        
        Args:
            message_id (str): ID da mensagem recorrente.
            
        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário.
        """
        try:
            from bson.objectid import ObjectId
            
            result = await self.db.recurring_messages.update_one(
                {"_id": ObjectId(message_id)},
                {"$set": {"last_sent_at": datetime.now()}}
            )
            
            return result.modified_count > 0
        except PyMongoError as e:
            logger.error(f"Erro ao atualizar timestamp da mensagem recorrente: {e}")
            return False
    
    async def delete_recurring_message(self, message_id: str) -> bool:
        """
        Desativa uma mensagem recorrente (exclusão lógica).
        
        Args:
            message_id (str): ID da mensagem recorrente.
            
        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário.
        """
        try:
            from bson.objectid import ObjectId
            
            result = await self.db.recurring_messages.update_one(
                {"_id": ObjectId(message_id)},
                {"$set": {"active": False}}
            )
            
            return result.modified_count > 0
        except PyMongoError as e:
            logger.error(f"Erro ao desativar mensagem recorrente: {e}")
            return False

    async def add_to_blacklist(
        self, 
        chat_id: int, 
        message_id: int, 
        user_id: int, 
        user_name: str, 
        username: str = None, 
        message_text: str = None,
        added_by: int = None,
        added_by_name: str = None
    ) -> str:
        """
        Adiciona uma mensagem à blacklist.
        
        Args:
            chat_id (int): ID do chat.
            message_id (int): ID da mensagem.
            user_id (int): ID do usuário que enviou a mensagem.
            user_name (str): Nome do usuário que enviou a mensagem.
            username (str, optional): Username do usuário que enviou a mensagem.
            message_text (str, optional): Texto da mensagem.
            added_by (int, optional): ID do usuário que adicionou à blacklist.
            added_by_name (str, optional): Nome do usuário que adicionou à blacklist.
            
        Returns:
            str: ID do documento criado ou None se falhar.
        """
        try:
            # Adiciona à collection de blacklist
            doc = {
                "chat_id": chat_id,
                "message_id": message_id,
                "user_id": user_id,
                "user_name": user_name,
                "username": username,
                "message_text": message_text,
                "added_by": added_by,
                "added_by_name": added_by_name,
                "added_at": datetime.now()
            }
            
            result = await self.db.blacklist.insert_one(doc)
            
            # Retorna o ID do documento criado
            return str(result.inserted_id)
        except PyMongoError as e:
            logger.error(f"Erro ao adicionar mensagem à blacklist: {e}")
            return None
    
    async def get_blacklist(self, chat_id: int) -> List[Dict[str, Any]]:
        """
        Obtém a lista de mensagens na blacklist de um chat.
        
        Args:
            chat_id (int): ID do chat.
            
        Returns:
            List[Dict[str, Any]]: Lista de mensagens na blacklist.
        """
        try:
            cursor = self.db.blacklist.find({"chat_id": chat_id}).sort("added_at", -1)
            blacklist = []
            async for doc in cursor:
                blacklist.append(doc)
            return blacklist
        except PyMongoError as e:
            logger.error(f"Erro ao obter blacklist do chat {chat_id}: {e}")
            return []
    
    async def get_blacklist_by_group_name(self, group_name: str) -> List[Dict[str, Any]]:
        """
        Obtém a lista de mensagens na blacklist de um grupo pelo nome.
        
        Args:
            group_name (str): Nome do grupo.
            
        Returns:
            List[Dict[str, Any]]: Lista de mensagens na blacklist.
        """
        try:
            # Procura em todos os chats monitorados pelo nome
            chat_id = await self._get_chat_id_by_name(group_name)
            
            if not chat_id:
                return []
            
            # Obtém a blacklist deste chat
            return await self.get_blacklist(chat_id)
        except PyMongoError as e:
            logger.error(f"Erro ao obter blacklist pelo nome do grupo '{group_name}': {e}")
            return []
    
    async def _get_chat_username(self, chat_id: int) -> Optional[str]:
        """
        Obtém o username de um chat.
        
        Args:
            chat_id (int): ID do chat.
            
        Returns:
            Optional[str]: Username do chat ou None se não encontrado.
        """
        try:
            chat_data = await self.db.monitored_chats.find_one({"chat_id": chat_id})
            if chat_data and "username" in chat_data:
                return chat_data["username"]
            return None
        except PyMongoError as e:
            logger.error(f"Erro ao obter username do chat {chat_id}: {e}")
            return None
    
    async def _get_chat_id_by_name(self, group_name: str) -> Optional[int]:
        """
        Obtém o ID de um chat pelo nome ou username.
        
        Args:
            group_name (str): Nome ou username do grupo.
            
        Returns:
            Optional[int]: ID do chat ou None se não encontrado.
        """
        try:
            # Log para debug
            logger.info(f"Buscando grupo com nome/username: {group_name}")
            
            # Escapa caracteres especiais do regex
            escaped_name = re.escape(group_name)
            
            # Procura por nome exato ou parcial (case insensitive) no título ou username
            chat_data = await self.db.monitored_chats.find_one({
                "$or": [
                    {"title": {"$regex": f"^{escaped_name}$", "$options": "i"}},  # Match exato
                    {"title": {"$regex": escaped_name, "$options": "i"}},  # Match parcial
                    {"username": {"$regex": f"^{escaped_name}$", "$options": "i"}},  # Match exato
                    {"username": {"$regex": escaped_name, "$options": "i"}}  # Match parcial
                ]
            })
            
            # Log para debug
            if chat_data:
                logger.info(f"Grupo encontrado: {chat_data}")
            else:
                logger.info("Nenhum grupo encontrado")
                
                # Lista todos os grupos monitorados para debug
                cursor = self.db.monitored_chats.find({})
                all_chats = []
                async for chat in cursor:
                    all_chats.append({
                        "chat_id": chat.get("chat_id"),
                        "title": chat.get("title"),
                        "username": chat.get("username")
                    })
                logger.info(f"Grupos monitorados disponíveis: {all_chats}")
            
            if chat_data:
                return chat_data["chat_id"]
            return None
        except PyMongoError as e:
            logger.error(f"Erro ao obter ID do chat pelo nome/username '{group_name}': {e}")
            return None
            
    async def remove_from_blacklist(self, item_id: str) -> bool:
        """
        Remove uma mensagem da blacklist.
        
        Args:
            item_id (str): ID do item na blacklist.
            
        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário.
        """
        try:
            from bson.objectid import ObjectId
            
            result = await self.db.blacklist.delete_one({"_id": ObjectId(item_id)})
            
            return result.deleted_count > 0
        except PyMongoError as e:
            logger.error(f"Erro ao remover item da blacklist: {e}")
            return False
            
    async def remove_from_blacklist_by_link(self, message_link: str) -> bool:
        """
        Remove uma mensagem da blacklist usando o link da mensagem.
        
        Args:
            message_link (str): Link da mensagem (formato: https://t.me/c/{chat_id}/{message_id}).
            
        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário.
        """
        try:
            # Extrai chat_id e message_id do link
            # Formato esperado: https://t.me/c/{chat_id}/{message_id}
            import re
            
            # Padrão para extrair chat_id e message_id do link
            pattern = r"https://t\.me/c/(\d+)/(\d+)"
            match = re.match(pattern, message_link)
            
            if not match:
                logger.error(f"Formato de link inválido: {message_link}")
                return False
                
            chat_id_str, message_id_str = match.groups()
            
            # Converte para os tipos corretos
            chat_id = int(f"-100{chat_id_str}")  # Adiciona o prefixo -100 para obter o chat_id real
            message_id = int(message_id_str)
            
            # Procura e remove o item correspondente na blacklist
            result = await self.db.blacklist.delete_one({
                "chat_id": chat_id,
                "message_id": message_id
            })
            
            if result.deleted_count > 0:
                logger.info(f"Item removido da blacklist: chat_id={chat_id}, message_id={message_id}")
                return True
            else:
                logger.warning(f"Nenhum item encontrado na blacklist com chat_id={chat_id}, message_id={message_id}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao remover item da blacklist por link: {e}")
            return False