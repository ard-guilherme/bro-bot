"""
Cliente para o MongoDB.
"""
import os
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import motor.motor_asyncio
from pymongo.errors import PyMongoError
import re
from bson import ObjectId

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
            "mongodb://localhost:27017"
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
    
    async def set_checkin_anchor(self, chat_id: int, message_id: int, points_value: int = 1, anchor_text: str = None) -> bool:
        """
        Define uma mensagem como âncora de check-in.
        
        Args:
            chat_id (int): ID do chat.
            message_id (int): ID da mensagem âncora.
            points_value (int): Valor em pontos deste check-in (default: 1).
            anchor_text (str): Texto da mensagem âncora (para check-in plus).
            
        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário.
        """
        try:
            # # Primeiro, desativa qualquer check-in ativo
            # await self.end_checkin(chat_id)
            
            # Prepara os dados da âncora
            anchor_data = {
                "chat_id": chat_id,
                "message_id": message_id,
                "created_at": datetime.now(),
                "active": True,
                "points_value": points_value
            }
            
            # Adiciona o texto da âncora se fornecido
            if anchor_text:
                anchor_data["anchor_text"] = anchor_text
            
            # Define o novo check-in
            result = await self.db.checkin_anchors.insert_one(anchor_data)
            
            return result.acknowledged
        except PyMongoError as e:
            logger.error(f"Erro ao definir âncora de check-in: {e}")
            return False
    
    async def end_checkin(self, chat_id: int, anchor_id: str) -> bool:
        """
        Desativa o check-in específico.
        
        Args:
            chat_id (int): ID do chat.
            anchor_id (str): ID da âncora de check-in a ser desativada.
            
        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário.
        """
        try:
            result = await self.db.checkin_anchors.update_one(
                {"_id": ObjectId(anchor_id), "chat_id": chat_id, "active": True},
                {"$set": {"active": False}}
            )
            
            return result.acknowledged
        except PyMongoError as e:
            logger.error(f"Erro ao desativar check-in {anchor_id} para chat {chat_id}: {e}")
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
            # Converte anchor_id para ObjectId
            try:
                anchor_object_id = ObjectId(anchor_id)
            except Exception as e:
                logger.error(f"Erro ao converter anchor_id para ObjectId: {anchor_id}. Erro: {e}")
                return 0

            count = await self.db.user_checkins.count_documents({
                "chat_id": chat_id,
                "anchor_id": anchor_object_id
            })
            
            return count
        except PyMongoError as e:
            logger.error(f"Erro ao obter contagem de check-ins para âncora: {e}")
            return 0
    
    async def get_active_checkin(self, chat_id: int) -> Optional[List[Dict]]:
        """
        Obtém todos os check-ins ativos para um chat.
        
        Args:
            chat_id (int): ID do chat.
            
        Returns:
            Optional[List[Dict]]: Lista com os dados dos check-ins ativos (incluindo points_value),
                                 ou None se não houver check-ins ativos.
        """
        try:
            cursor = self.db.checkin_anchors.find(
                {"chat_id": chat_id, "active": True}
            )
            
            results = await cursor.to_list(length=None)
            
            return results if results else None
        except PyMongoError as e:
            logger.error(f"Erro ao obter check-ins ativos: {e}")
            return None
    
    async def get_anchor_details(self, anchor_id: str) -> Optional[Dict]:
        """
        Obtém detalhes completos de uma âncora específica.
        
        Args:
            anchor_id (str): ID da âncora de check-in.
            
        Returns:
            Optional[Dict]: Dados completos da âncora incluindo texto (se disponível), ou None se não encontrada.
        """
        try:
            # Converte anchor_id para ObjectId
            try:
                anchor_object_id = ObjectId(anchor_id)
            except Exception as e:
                logger.error(f"Erro ao converter anchor_id para ObjectId: {anchor_id}. Erro: {e}")
                return None

            anchor_details = await self.db.checkin_anchors.find_one({
                "_id": anchor_object_id,
                "active": True
            })
            
            return anchor_details
        except PyMongoError as e:
            logger.error(f"Erro ao obter detalhes da âncora {anchor_id}: {e}")
            return None
    
    async def confirm_manual_checkin(self, chat_id: int, anchor_id: str, user_id: int, user_name: str, username: str = None) -> Optional[int]:
        """
        Confirma manualmente um check-in para um usuário no check-in ativo especificado.
        Retorna o novo total de pontos do usuário se bem-sucedido, None se já fez check-in ou erro.
        """
        try:
            active_checkins = await self.get_active_checkin(chat_id)
            if not active_checkins:
                logger.warning(f"Tentativa de confirmação manual sem check-ins ativos: chat {chat_id}")
                return None

            # Converte anchor_id para ObjectId para comparação
            try:
                anchor_object_id = ObjectId(anchor_id)
            except Exception as e:
                logger.error(f"Erro ao converter anchor_id para ObjectId: {anchor_id}. Erro: {e}")
                return None

            # Procura a âncora específica na lista de check-ins ativos
            active_checkin = None
            for checkin in active_checkins:
                if checkin["_id"] == anchor_object_id:
                    active_checkin = checkin
                    break

            if not active_checkin:
                logger.warning(f"Âncora {anchor_id} não encontrada nos check-ins ativos do chat {chat_id}")
                return None

            points_value = active_checkin.get("points_value", 1) # Obtém valor da âncora

            # Verifica se já existe check-in para esta âncora
            existing_checkin = await self.db.user_checkins.find_one({
                "chat_id": chat_id,
                "user_id": user_id,
                "anchor_id": anchor_object_id
            })

            if existing_checkin:
                logger.info(f"Check-in manual ignorado: usuário {user_id} já fez check-in para a âncora {anchor_id}")
                return None

            # Insere o novo registro de check-in com a pontuação
            insert_result = await self.db.user_checkins.insert_one({
                "chat_id": chat_id,
                "user_id": user_id,
                "user_name": user_name,
                "username": username,
                "anchor_id": anchor_object_id,
                "checkin_type": "manual", # Indica que foi manual
                "points_value": points_value, # Salva a pontuação
                "created_at": datetime.now()
            })

            if not insert_result.acknowledged:
                logger.error(f"Falha ao inserir check-in manual para usuário {user_id}, âncora {anchor_id}")
                return None

            # Calcula e retorna o novo score total (agora soma os pontos)
            new_total_score = await self.calculate_user_total_score(chat_id, user_id)
            logger.info(f"Check-in manual confirmado para {user_name} ({user_id}). Novo score: {new_total_score}")
            return new_total_score

        except PyMongoError as e:
            logger.error(f"Erro ao confirmar check-in manual: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao confirmar check-in manual: {e}")
            return None

    async def record_user_checkin(self, chat_id: int, anchor_id: str, user_id: int, user_name: str, username: str = None) -> Optional[int]:
        """
        Registra um check-in de um usuário para a âncora ativa.
        Verifica se o usuário já fez check-in para esta âncora específica.
        Salva a pontuação do check-in (baseada na âncora) e o tipo ('normal' ou 'plus').
        Retorna o novo total de pontos do usuário (somando as pontuações) se o check-in for registrado com sucesso,
        None se o usuário já fez check-in para esta âncora ou se ocorrer um erro.
        """
        try:
            # Converte anchor_id para ObjectId
            try:
                anchor_object_id = ObjectId(anchor_id)
            except Exception as e:
                logger.error(f"Erro ao converter anchor_id para ObjectId: {anchor_id}. Erro: {e}")
                return None

            # 1. Usa o anchor_id fornecido como parâmetro
            # Busca informações da âncora específica
            active_checkin = await self.db.checkin_anchors.find_one({
                "_id": anchor_object_id,
                "chat_id": chat_id,
                "active": True
            })
            
            if not active_checkin:
                logger.debug(f"Âncora {anchor_id} não encontrada ou não está ativa no chat {chat_id}")
                return None # Âncora não encontrada ou não ativa

            points_value = active_checkin.get("points_value", 1) # Pega a pontuação da âncora
            checkin_type = "plus" if points_value > 1 else "normal" # Define o tipo

            # 2. Verifica se o usuário já fez check-in *para esta âncora*
            existing_checkin = await self.db.user_checkins.find_one({
                "chat_id": chat_id,
                "user_id": user_id,
                "anchor_id": anchor_object_id
            })

            if existing_checkin:
                logger.debug(f"Usuário {user_id} já fez check-in para a âncora {anchor_id}")
                return None # Já fez check-in para esta âncora

            # 3. Registra o novo check-in na collection 'user_checkins' com pontuação e tipo
            insert_result = await self.db.user_checkins.insert_one({
                "chat_id": chat_id,
                "user_id": user_id,
                "user_name": user_name,
                "username": username,
                "anchor_id": anchor_object_id, # Link para a âncora específica
                "checkin_type": checkin_type, # Salva 'normal' ou 'plus'
                "points_value": points_value, # Salva a pontuação do check-in
                "created_at": datetime.now()
            })

            if not insert_result.acknowledged:
                logger.error(f"Falha ao inserir registro de check-in para usuário {user_id}, âncora {anchor_id}")
                return None # Falha ao inserir

            # 4. Calcula e retorna o novo score total do usuário (agora somando pontos)
            new_total_score = await self.calculate_user_total_score(chat_id, user_id)
            logger.info(f"Check-in {checkin_type} ({points_value} pts) registrado para {user_name} ({user_id}) na âncora {anchor_id}. Novo score total: {new_total_score}")
            return new_total_score

        except PyMongoError as e:
            logger.error(f"Erro ao registrar check-in: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao registrar check-in: {e}")
            return None

    async def calculate_user_total_score(self, chat_id: int, user_id: int) -> int:
        """
        Calcula o score total de um usuário em um chat somando os 'points_value' de seus check-ins.
        
        Args:
            chat_id (int): ID do chat.
            user_id (int): ID do usuário.
            
        Returns:
            int: Score total do usuário, ou 0 se não houver check-ins ou erro.
        """
        try:
            pipeline = [
                {
                    "$match": {
                        "chat_id": chat_id,
                        "user_id": user_id,
                        "points_value": {"$exists": True} # Considera apenas check-ins com pontuação definida
                    }
                },
                {
                    "$group": {
                        "_id": "$user_id", # Agrupa pelo usuário
                        "total_score": {"$sum": "$points_value"} # Soma os pontos
                    }
                }
            ]
            
            result_cursor = self.db.user_checkins.aggregate(pipeline)
            result = await result_cursor.to_list(length=1) # Espera apenas um resultado
            
            if result:
                return result[0].get("total_score", 0)
            else:
                return 0 # Nenhum check-in encontrado
        except PyMongoError as e:
            logger.error(f"Erro ao calcular score total para user {user_id} no chat {chat_id}: {e}")
            return 0
        except Exception as e:
            logger.error(f"Erro inesperado ao calcular score total: {e}")
            return 0

    async def get_checkin_scoreboard(self, chat_id: int) -> List[Dict[str, Any]]:
        """
        Obtém o ranking de check-ins (scoreboard) para um chat, ordenado por score total.
        O score é calculado somando os 'points_value' de cada check-in do usuário.
        """
        try:
            pipeline = [
                {
                    "$match": {
                        "chat_id": chat_id,
                        "points_value": {"$exists": True} # Considera apenas check-ins com pontuação
                    }
                },
                {
                    "$group": {
                        "_id": "$user_id", # Agrupa por usuário
                        # Pega o último nome/username conhecido para exibição
                        "user_name": {"$last": "$user_name"},
                        "username": {"$last": "$username"},
                        "total_score": {"$sum": "$points_value"}, # Soma os pontos
                        "last_checkin_time": {"$max": "$created_at"} # Pega a data do último check-in
                    }
                },
                {
                    "$sort": {
                        "total_score": -1, # Ordena por score (maior primeiro)
                        "last_checkin_time": -1 # Desempate pelo check-in mais recente
                    }
                },
                {
                  "$limit": 50 # Limita aos top 50 para evitar mensagens muito longas
                },
                {
                    "$project": { # Formata a saída
                        "_id": 0, # Remove o _id do grupo
                        "user_id": "$_id", # O _id do grupo é o user_id
                        "user_name": "$user_name",
                        "username": "$username",
                        "score": "$total_score",
                        "last_checkin": "$last_checkin_time"
                    }
                }
            ]

            scoreboard = await self.db.user_checkins.aggregate(pipeline).to_list(length=None) # Pega todos os resultados até o limite
            return scoreboard

        except PyMongoError as e:
            logger.error(f"Erro ao gerar scoreboard para chat {chat_id}: {e}")
            return [] # Retorna lista vazia em caso de erro

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
        Obtém o número de documentos de check-in de um usuário em um chat.
        NOTA: Isto conta o NÚMERO de check-ins, não o SCORE total.
              Use calculate_user_total_score para obter o score.
        """
        try:
            count = await self.db.user_checkins.count_documents({
                "chat_id": chat_id,
                "user_id": user_id
            })
            return count
        except PyMongoError as e:
            logger.error(f"Erro ao obter contagem de check-ins do usuário {user_id}: {e}")
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
                # Se existe e está ativo, não faz nada e retorna False
                if existing_admin.get("is_active", False):
                    logger.info(f"Admin {admin_id} já existe e está ativo.")
                    return False
                else:
                    # Se existe mas está inativo, reativa e atualiza nome/timestamp
                    logger.info(f"Reativando admin inativo {admin_id}")
                    update_result = await self.db.bot_admins.update_one(
                        {"admin_id": admin_id},
                        {
                            "$set": {
                                "is_active": True,
                                "admin_name": admin_name, # Atualiza o nome
                                "added_by": added_by, # Atualiza quem adicionou/reativou
                                "reactivated_at": datetime.now(),
                                "added_at": existing_admin.get("added_at") # Mantém data original
                            }
                        }
                    )
                    return update_result.modified_count > 0 # Retorna True se reativado
            else:
                # Se não existe, insere um novo admin ativo
                logger.info(f"Adicionando novo admin {admin_id}")
                insert_result = await self.db.bot_admins.insert_one({
                    "admin_id": admin_id,
                    "admin_name": admin_name,
                    "added_by": added_by,
                    "added_at": datetime.now(),
                    "is_active": True # Define como ativo por padrão
                })
                return insert_result.acknowledged
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
            async for item in cursor:
                blacklist.append(item)
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
                return chat_data.get("chat_id")
            else:
                logger.info("Nenhum grupo encontrado")

                # Lista todos os grupos monitorados para debug
                cursor = self.db.monitored_chats.find({})
                all_chats = []
                async for chat in cursor:
                    all_chats.append(chat)
                logger.debug(f"Grupos monitorados atualmente: {all_chats}")

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

    # Métodos para gerenciar informações do chat
    
    async def update_chat_info(self, chat_id: int, title: str, chat_type: str):
        """
        Atualiza ou insere informações sobre um chat.
        """
        try:
            await self.db.chats.update_one(
                {"chat_id": chat_id},
                {"$set": {"title": title, "type": chat_type, "last_seen": datetime.now()}},
                upsert=True # Cria o documento se não existir
            )
            logger.debug(f"Informações do chat {chat_id} ({title}) atualizadas.")
        except PyMongoError as e:
            logger.error(f"Erro ao atualizar informações do chat {chat_id}: {e}")
            
    async def get_chat_info(self, chat_id: int) -> Optional[Dict]:
        """
        Obtém informações sobre um chat pelo ID.
        """
        try:
            return await self.db.chats.find_one({"chat_id": chat_id})
        except PyMongoError as e:
            logger.error(f"Erro ao obter informações do chat {chat_id}: {e}")
            return None

    async def get_chat_info_by_title(self, title: str) -> Optional[Dict]:
        """
        Obtém informações sobre um chat pelo título (case-insensitive) 
        a partir da coleção 'monitored_chats'.
        Retorna o primeiro chat encontrado com o título correspondente.
        """
        try:
            # Busca case-insensitive usando regex
            # Adiciona ^ e $ para buscar o título exato (ignorando maiúsculas/minúsculas)
            regex_pattern = re.compile(f"^{re.escape(title)}$", re.IGNORECASE)
            
            logger.debug(f"Buscando chat pelo título em 'monitored_chats': '{title}' (regex: {regex_pattern})")
            # Busca na coleção correta ('monitored_chats')
            chat_info = await self.db.monitored_chats.find_one({"title": regex_pattern})
            
            if chat_info:
                logger.debug(f"Chat encontrado em 'monitored_chats' pelo título '{title}': ID {chat_info.get('chat_id')}")
            else:
                logger.debug(f"Nenhum chat encontrado com o título '{title}'.")
            return chat_info
                
        except PyMongoError as e:
            logger.error(f"Erro ao obter informações do chat pelo título '{title}': {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao buscar chat por título: {e}")
            return None

    async def get_chat_id_by_group_name(self, group_name: str) -> Optional[int]:
        """
        Obtém o ID numérico de um chat ativo monitorado pelo nome do grupo.

        Args:
            group_name (str): O nome (título) do grupo.

        Returns:
            Optional[int]: O chat_id numérico se encontrado e ativo, None caso contrário.
        """
        chat_info = await self.get_chat_info_by_title(group_name)
        if chat_info and chat_info.get("active"):
            chat_id = chat_info.get("chat_id")
            if isinstance(chat_id, (int, float)): # Verifica se é numérico
                 # Tenta converter para int, tratando $numberLong do BSON
                try:
                    return int(chat_id)
                except (ValueError, TypeError):
                    logger.error(f"Chat ID encontrado para '{group_name}' não é um número válido: {chat_id}")
                    return None
            else:
                 logger.warning(f"Chat ID encontrado para '{group_name}' não é numérico: {chat_id} (Tipo: {type(chat_id)})")
                 return None # Retorna None se o tipo não for numérico
        elif chat_info:
            logger.warning(f"Grupo '{group_name}' encontrado, mas não está ativo.")
            return None
        else:
            logger.info(f"Grupo '{group_name}' não encontrado na coleção monitored_chats.")
            return None

    async def remove_blacklist_items_by_ids(self, item_ids: List[Union[str, ObjectId]]) -> int:
        """
        Remove múltiplos itens da coleção blacklist pelos seus ObjectIds.

        Args:
            item_ids (List[Union[str, ObjectId]]): Lista de IDs (como string ou ObjectId) dos itens a serem removidos.

        Returns:
            int: O número de documentos removidos.
        """
        if not self.db:
            logger.error("Conexão com MongoDB não estabelecida")
            return 0
        if not item_ids:
            logger.warning("Tentativa de remover itens da blacklist com lista de IDs vazia.")
            return 0

        # Converte todos os IDs para ObjectId se forem strings válidas
        object_ids = []
        for item_id in item_ids:
            if isinstance(item_id, ObjectId):
                object_ids.append(item_id)
            elif isinstance(item_id, str):
                try:
                    object_ids.append(ObjectId(item_id))
                except Exception as e:
                    logger.warning(f"ID inválido fornecido para remoção da blacklist: {item_id}. Erro: {e}")
            else:
                 logger.warning(f"Tipo de ID inválido fornecido para remoção da blacklist: {type(item_id)}")
        
        if not object_ids: # Se nenhum ID válido foi encontrado após a conversão
            logger.error("Nenhum ObjectId válido fornecido para remoção da blacklist.")
            return 0

        try:
            result = await self.db.blacklist.delete_many({
                "_id": {"$in": object_ids}
            })
            logger.info(f"Removidos {result.deleted_count} itens da blacklist.")
            return result.deleted_count
        except PyMongoError as e:
            logger.error(f"Erro ao remover itens da blacklist por IDs: {e}")
            return 0
        except Exception as e:
            logger.error(f"Erro inesperado ao remover itens da blacklist por IDs: {e}")
            return 0

    # Métodos para Correio Elegante
    
    async def create_mail(self, sender_id: int, sender_name: str, recipient_username: str, message_text: str) -> Optional[str]:
        """
        Cria uma nova mensagem de correio elegante.
        
        Args:
            sender_id (int): ID do remetente.
            sender_name (str): Nome do remetente.
            recipient_username (str): Username do destinatário (sem @).
            message_text (str): Texto da mensagem.
            
        Returns:
            Optional[str]: ID da mensagem criada ou None em caso de erro.
        """
        try:
            mail_data = {
                "sender_id": sender_id,
                "sender_name": sender_name,
                "recipient_username": recipient_username,
                "message_text": message_text,
                "status": "pending",  # pending, published, expired
                "created_at": datetime.now(),
                "published_at": None,
                "expires_at": None,
                "revealed_to": [],  # Lista de user_ids que revelaram o remetente
                "reported_by": [],  # Lista de user_ids que denunciaram
                "replies": []  # Lista de respostas anônimas
            }
            
            result = await self.db.correio_elegante.insert_one(mail_data)
            
            if result.acknowledged:
                logger.info(f"Correio criado: ID {result.inserted_id}")
                return str(result.inserted_id)
            
            return None
            
        except PyMongoError as e:
            logger.error(f"Erro ao criar correio: {e}")
            return None
    
    async def get_daily_mail_count(self, user_id: int) -> int:
        """
        Obtém o número de correios enviados pelo usuário hoje.
        
        Args:
            user_id (int): ID do usuário.
            
        Returns:
            int: Número de correios enviados hoje.
        """
        try:
            # Início e fim do dia atual
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            
            count = await self.db.correio_elegante.count_documents({
                "sender_id": user_id,
                "created_at": {
                    "$gte": today_start,
                    "$lt": today_end
                }
            })
            
            return count
            
        except PyMongoError as e:
            logger.error(f"Erro ao obter contagem diária de correios: {e}")
            return 0
    
    async def get_pending_mails(self) -> List[Dict[str, Any]]:
        """
        Obtém todos os correios pendentes para publicação.
        
        Returns:
            List[Dict[str, Any]]: Lista de correios pendentes.
        """
        try:
            cursor = self.db.correio_elegante.find({"status": "pending"})
            mails = await cursor.to_list(length=None)
            return mails
            
        except PyMongoError as e:
            logger.error(f"Erro ao obter correios pendentes: {e}")
            return []
    
    async def publish_mail(self, mail_id: str, published_message_id: int) -> bool:
        """
        Marca um correio como publicado.
        
        Args:
            mail_id (str): ID do correio.
            published_message_id (int): ID da mensagem publicada no grupo.
            
        Returns:
            bool: True se atualizado com sucesso.
        """
        try:
            # Define expiração para 24 horas após publicação
            expires_at = datetime.now() + timedelta(hours=24)
            
            result = await self.db.correio_elegante.update_one(
                {"_id": ObjectId(mail_id)},
                {
                    "$set": {
                        "status": "published",
                        "published_at": datetime.now(),
                        "published_message_id": published_message_id,
                        "expires_at": expires_at
                    }
                }
            )
            
            return result.modified_count > 0
            
        except PyMongoError as e:
            logger.error(f"Erro ao marcar correio como publicado: {e}")
            return False
    
    async def get_mail_by_id(self, mail_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém um correio pelo ID.
        
        Args:
            mail_id (str): ID do correio.
            
        Returns:
            Optional[Dict[str, Any]]: Dados do correio ou None se não encontrado.
        """
        try:
            mail = await self.db.correio_elegante.find_one({"_id": ObjectId(mail_id)})
            
            # Verificar se não expirou
            if mail and mail.get("expires_at") and mail["expires_at"] < datetime.now():
                # Marcar como expirado
                await self.db.correio_elegante.update_one(
                    {"_id": ObjectId(mail_id)},
                    {"$set": {"status": "expired"}}
                )
                return None
            
            return mail
            
        except PyMongoError as e:
            logger.error(f"Erro ao obter correio por ID: {e}")
            return None
    
    async def reveal_mail(self, mail_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Marca que um usuário revelou o remetente de um correio.
        
        Args:
            mail_id (str): ID do correio.
            user_id (int): ID do usuário que revelou.
            
        Returns:
            Optional[Dict[str, Any]]: Dados do correio revelado ou None.
        """
        try:
            # Adicionar user_id à lista de quem revelou
            result = await self.db.correio_elegante.update_one(
                {"_id": ObjectId(mail_id)},
                {"$addToSet": {"revealed_to": user_id}}
            )
            
            if result.modified_count > 0:
                # Retornar dados do correio
                return await self.get_mail_by_id(mail_id)
            
            return None
            
        except PyMongoError as e:
            logger.error(f"Erro ao revelar correio: {e}")
            return None
    
    async def report_mail(self, mail_id: str, user_id: int, user_name: str) -> bool:
        """
        Registra denúncia de um correio.
        
        Args:
            mail_id (str): ID do correio.
            user_id (int): ID do usuário que denunciou.
            user_name (str): Nome do usuário que denunciou.
            
        Returns:
            bool: True se denúncia registrada com sucesso.
        """
        try:
            report_data = {
                "user_id": user_id,
                "user_name": user_name,
                "reported_at": datetime.now()
            }
            
            result = await self.db.correio_elegante.update_one(
                {"_id": ObjectId(mail_id)},
                {"$addToSet": {"reported_by": report_data}}
            )
            
            # Se chegou a 3 denúncias, marcar como expirado
            mail = await self.get_mail_by_id(mail_id)
            if mail and len(mail.get("reported_by", [])) >= 3:
                await self.db.correio_elegante.update_one(
                    {"_id": ObjectId(mail_id)},
                    {"$set": {"status": "expired"}}
                )
            
            return result.modified_count > 0
            
        except PyMongoError as e:
            logger.error(f"Erro ao registrar denúncia de correio: {e}")
            return False
    
    async def send_mail_reply(self, mail_id: str, reply_text: str, sender_id: int, sender_name: str) -> bool:
        """
        Envia resposta anônima para um correio.
        
        Args:
            mail_id (str): ID do correio original.
            reply_text (str): Texto da resposta.
            sender_id (int): ID de quem está respondendo.
            sender_name (str): Nome de quem está respondendo.
            
        Returns:
            bool: True se resposta enviada com sucesso.
        """
        try:
            reply_data = {
                "reply_text": reply_text,
                "sender_id": sender_id,
                "sender_name": sender_name,
                "sent_at": datetime.now()
            }
            
            result = await self.db.correio_elegante.update_one(
                {"_id": ObjectId(mail_id)},
                {"$push": {"replies": reply_data}}
            )
            
            return result.modified_count > 0
            
        except PyMongoError as e:
            logger.error(f"Erro ao enviar resposta de correio: {e}")
            return False
    
    async def get_gym_nation_chat_id(self) -> Optional[int]:
        """
        Obtém o chat_id do grupo GYM NATION.
        
        Returns:
            Optional[int]: Chat ID do grupo GYM NATION ou None se não encontrado.
        """
        try:
            # Primeiro, tentar usar o Chat ID configurado no .env
            from src.utils.config import Config
            
            configured_chat_id = Config.get_gym_nation_chat_id()
            if configured_chat_id:
                logger.info(f"Usando Chat ID configurado: {configured_chat_id}")
                return configured_chat_id
            
            # Fallback: Buscar pelo título "GYM NATION" (case insensitive)
            gym_nation = await self.db.monitored_chats.find_one({
                "title": {"$regex": "^GYM NATION.*$", "$options": "i"},
                "active": True
            })
            
            if gym_nation:
                logger.info(f"Chat ID encontrado via MongoDB: {gym_nation.get('chat_id')}")
                return gym_nation.get("chat_id")
            
            logger.warning("Chat ID do GYM NATION não encontrado. Configure GYM_NATION_CHAT_ID no .env")
            return None
            
        except PyMongoError as e:
            logger.error(f"Erro ao obter chat_id do GYM NATION: {e}")
            return None
    
    # Métodos para pagamento Pix
    
    async def create_pix_payment(self, pix_id: str, user_id: int, mail_id: str, amount: float, pix_key: str) -> bool:
        """
        Cria um registro de pagamento Pix.
        
        Args:
            pix_id (str): ID único do pagamento.
            user_id (int): ID do usuário que vai pagar.
            mail_id (str): ID do correio a ser revelado.
            amount (float): Valor do pagamento.
            pix_key (str): Chave Pix para pagamento.
            
        Returns:
            bool: True se criado com sucesso.
        """
        try:
            payment_data = {
                "pix_id": pix_id,
                "user_id": user_id,
                "mail_id": mail_id,
                "amount": amount,
                "pix_key": pix_key,
                "status": "pending",  # pending, confirmed, expired
                "created_at": datetime.now(),
                "expires_at": datetime.now() + timedelta(minutes=30),
                "confirmed_at": None
            }
            
            result = await self.db.pix_payments.insert_one(payment_data)
            return result.acknowledged
            
        except PyMongoError as e:
            logger.error(f"Erro ao criar pagamento Pix: {e}")
            return False
    
    async def get_pix_payment(self, pix_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém dados de um pagamento Pix.
        
        Args:
            pix_id (str): ID do pagamento Pix.
            
        Returns:
            Optional[Dict[str, Any]]: Dados do pagamento ou None se não encontrado.
        """
        try:
            payment = await self.db.pix_payments.find_one({"pix_id": pix_id})
            
            # Verificar se não expirou
            if payment and payment.get("expires_at") and payment["expires_at"] < datetime.now():
                # Marcar como expirado
                await self.db.pix_payments.update_one(
                    {"pix_id": pix_id},
                    {"$set": {"status": "expired"}}
                )
                return None
            
            return payment
            
        except PyMongoError as e:
            logger.error(f"Erro ao obter pagamento Pix: {e}")
            return None
    
    async def confirm_pix_payment(self, pix_id: str, user_id: int) -> bool:
        """
        Confirma um pagamento Pix.
        
        Args:
            pix_id (str): ID do pagamento Pix.
            user_id (int): ID do usuário que confirmou.
            
        Returns:
            bool: True se confirmado com sucesso.
        """
        try:
            result = await self.db.pix_payments.update_one(
                {
                    "pix_id": pix_id,
                    "user_id": user_id,
                    "status": {"$in": ["pending", "awaiting_confirmation"]}
                },
                {
                    "$set": {
                        "status": "confirmed",
                        "confirmed_at": datetime.now()
                    }
                }
            )
            
            return result.modified_count > 0
            
        except PyMongoError as e:
            logger.error(f"Erro ao confirmar pagamento Pix: {e}")
            return False

    # Métodos para estatísticas do correio elegante
    
    async def get_mail_stats_today(self) -> Dict[str, int]:
        """
        Obtém estatísticas de correio elegante do dia atual.
        
        Returns:
            Dict[str, int]: Estatísticas do dia (sent, revealed, reported).
        """
        try:
            # Início e fim do dia atual
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            
            # Correios enviados hoje
            mails_sent_today = await self.db.correio_elegante.count_documents({
                "created_at": {
                    "$gte": today_start,
                    "$lt": today_end
                }
            })
            
            # Revelações pagas hoje
            revelations_today = await self.db.pix_payments.count_documents({
                "created_at": {
                    "$gte": today_start,
                    "$lt": today_end
                },
                "status": "confirmed"
            })
            
            # Denúncias hoje
            reports_today = 0
            cursor = self.db.correio_elegante.find({
                "reported_by.reported_at": {
                    "$gte": today_start,
                    "$lt": today_end
                }
            })
            
            async for mail in cursor:
                reports_in_period = [
                    report for report in mail.get("reported_by", [])
                    if report.get("reported_at") and 
                    today_start <= report["reported_at"] < today_end
                ]
                reports_today += len(reports_in_period)
            
            return {
                "sent": mails_sent_today,
                "revealed": revelations_today,
                "reported": reports_today
            }
            
        except PyMongoError as e:
            logger.error(f"Erro ao obter estatísticas diárias: {e}")
            return {"sent": 0, "revealed": 0, "reported": 0}
    
    async def get_mail_stats_total(self) -> Dict[str, Any]:
        """
        Obtém estatísticas totais do correio elegante.
        
        Returns:
            Dict[str, Any]: Estatísticas totais.
        """
        try:
            # Total de correios criados
            total_mails = await self.db.correio_elegante.count_documents({})
            
            # Arrecadação total (R$ 2,00 por revelação confirmada)
            total_revelations = await self.db.pix_payments.count_documents({
                "status": "confirmed"
            })
            total_revenue = total_revelations * 2.0
            
            # Usuários únicos que enviaram correios
            pipeline = [
                {"$group": {"_id": "$sender_id"}},
                {"$count": "unique_senders"}
            ]
            
            result = await self.db.correio_elegante.aggregate(pipeline).to_list(length=1)
            unique_senders = result[0]["unique_senders"] if result else 0
            
            # Correios por status
            pipeline_status = [
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ]
            
            status_results = await self.db.correio_elegante.aggregate(pipeline_status).to_list(length=None)
            status_counts = {item["_id"]: item["count"] for item in status_results}
            
            return {
                "total_mails": total_mails,
                "total_revenue": total_revenue,
                "unique_senders": unique_senders,
                "pending": status_counts.get("pending", 0),
                "published": status_counts.get("published", 0),
                "expired": status_counts.get("expired", 0)
            }
            
        except PyMongoError as e:
            logger.error(f"Erro ao obter estatísticas totais: {e}")
            return {
                "total_mails": 0,
                "total_revenue": 0.0,
                "unique_senders": 0,
                "pending": 0,
                "published": 0,
                "expired": 0
            }
    
    async def get_mail_stats_weekly(self) -> Dict[str, int]:
        """
        Obtém estatísticas da última semana.
        
        Returns:
            Dict[str, int]: Estatísticas da semana.
        """
        try:
            # Últimos 7 dias
            week_start = datetime.now() - timedelta(days=7)
            
            # Correios da semana
            mails_week = await self.db.correio_elegante.count_documents({
                "created_at": {"$gte": week_start}
            })
            
            # Revelações da semana
            revelations_week = await self.db.pix_payments.count_documents({
                "created_at": {"$gte": week_start},
                "status": "confirmed"
            })
            
            return {
                "sent": mails_week,
                "revealed": revelations_week
            }
            
        except PyMongoError as e:
            logger.error(f"Erro ao obter estatísticas semanais: {e}")
            return {"sent": 0, "revealed": 0}