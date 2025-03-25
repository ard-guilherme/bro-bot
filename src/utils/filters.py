"""
Filtros personalizados para o bot.
"""
import logging
from telegram import Update
from telegram.ext import filters
from src.utils.config import Config
from src.utils.mongodb_instance import mongodb_client

logger = logging.getLogger(__name__)

class CustomFilters:
    """Filtros personalizados para o bot."""
    
    @staticmethod
    def owner_filter():
        """
        Filtro que verifica se o usuário é o proprietário do bot OU um administrador do bot.
        
        Returns:
            filters.BaseFilter: Filtro que verifica se o usuário é o proprietário ou administrador do bot.
        """
        try:
            owner_id = Config.get_owner_id()
        except Exception as e:
            logger.error(f"Erro ao obter ID do proprietário: {e}")
            owner_id = None
        
        class OwnerFilter(filters.BaseFilter):
            def filter(self, update):
                """
                Função de filtro que verifica se o usuário é o proprietário ou administrador do bot.
                
                Args:
                    update (Update): Objeto de atualização do Telegram.
                    
                Returns:
                    bool: True se o usuário for o proprietário ou administrador do bot, False caso contrário.
                """
                try:
                    # Se não conseguimos obter o owner_id, retorna False
                    if owner_id is None:
                        return False
                        
                    user_id = update.effective_user.id
                    
                    # Verifica se o usuário é o proprietário
                    if user_id == owner_id:
                        return True
                    
                    # Verifica se o cliente MongoDB está conectado
                    if mongodb_client.db is None:
                        # Não podemos usar await aqui, então retornamos False
                        # O usuário terá que tentar novamente após o bot estar conectado ao MongoDB
                        logger.warning(
                            f"MongoDB não está conectado. Usuário {user_id} não pode ser verificado como administrador."
                        )
                        return False
                    
                    # Verifica se o usuário é um administrador do bot
                    # Como não podemos usar await aqui, usamos um método síncrono
                    # Isso é uma simplificação e pode não funcionar corretamente em todos os casos
                    is_admin = mongodb_client.db.bot_admins.find_one({"admin_id": user_id}) is not None
                    
                    if not is_admin:
                        logger.warning(
                            f"Usuário não autorizado tentou usar o bot. "
                            f"ID do usuário: {user_id}"
                        )
                    
                    return is_admin
                except Exception as e:
                    logger.error(f"Erro ao verificar se o usuário é autorizado: {e}")
                    return False
        
        return OwnerFilter()
    
    @staticmethod
    def only_owner_filter():
        """
        Filtro que verifica se o usuário é APENAS o proprietário do bot.
        
        Returns:
            filters.BaseFilter: Filtro que verifica se o usuário é o proprietário do bot.
        """
        try:
            owner_id = Config.get_owner_id()
        except Exception as e:
            logger.error(f"Erro ao obter ID do proprietário: {e}")
            owner_id = None
        
        class OnlyOwnerFilter(filters.BaseFilter):
            def filter(self, update):
                """
                Função de filtro que verifica se o usuário é o proprietário do bot.
                
                Args:
                    update (Update): Objeto de atualização do Telegram.
                    
                Returns:
                    bool: True se o usuário for o proprietário do bot, False caso contrário.
                """
                try:
                    # Se não conseguimos obter o owner_id, retorna False
                    if owner_id is None:
                        return False
                        
                    user_id = update.effective_user.id
                    
                    is_owner = user_id == owner_id
                    
                    if not is_owner:
                        logger.warning(
                            f"Usuário não proprietário tentou usar um comando restrito. "
                            f"ID do usuário: {user_id}, ID do proprietário: {owner_id}"
                        )
                    
                    return is_owner
                except Exception as e:
                    logger.error(f"Erro ao verificar se o usuário é o proprietário: {e}")
                    return False
        
        return OnlyOwnerFilter() 