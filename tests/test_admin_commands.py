"""
Testes para os comandos de administração do bot.
"""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from telegram import Update, User, Message, Chat
from telegram.ext import ContextTypes

from src.bot.handlers import setadmin_command, deladmin_command, listadmins_command
from src.utils.config import Config

class TestAdminCommands(unittest.TestCase):
    """Testes para os comandos de administração do bot."""
    
    def setUp(self):
        """Configuração inicial para os testes."""
        self.update = MagicMock(spec=Update)
        self.context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        
        # Configura o usuário
        self.user = MagicMock(spec=User)
        self.user.id = 123456789
        self.user.full_name = "Test User"
        
        # Configura a mensagem
        self.message = MagicMock(spec=Message)
        self.message.from_user = self.user
        self.message.chat = MagicMock(spec=Chat)
        self.message.chat.id = -1001234567890
        self.message.reply_text = AsyncMock()
        self.message.reply_to_message = None
        
        # Configura o update
        self.update.effective_user = self.user
        self.update.message = self.message
        self.update.effective_message = self.message
        
        # Configura o context
        self.context.args = []
        
        # Patch para Config.get_owner_id
        self.owner_id_patcher = patch('src.utils.config.Config.get_owner_id', return_value=123456789)
        self.mock_get_owner_id = self.owner_id_patcher.start()
        
        # Patch para mongodb_client
        self.mongodb_patcher = patch('src.bot.handlers.mongodb_client')
        self.mock_mongodb = self.mongodb_patcher.start()
        self.mock_mongodb.db = MagicMock()
        
    def tearDown(self):
        """Limpeza após os testes."""
        self.owner_id_patcher.stop()
        self.mongodb_patcher.stop()
    
    @pytest.mark.asyncio
    async def test_setadmin_command_no_args_no_reply(self):
        """Testa o comando /setadmin sem argumentos e sem resposta."""
        await setadmin_command(self.update, self.context)
        
        self.message.reply_text.assert_called_once()
        args, kwargs = self.message.reply_text.call_args
        assert "Erro: Você deve fornecer o ID do usuário ou responder a uma mensagem" in args[0]
        
    @pytest.mark.asyncio
    async def test_setadmin_command_with_args(self):
        """Testa o comando /setadmin com ID do usuário como argumento."""
        # Configura o argumento
        self.context.args = ["987654321"]
        
        # Configura o mock para add_admin
        self.mock_mongodb.add_admin = AsyncMock(return_value=True)
        
        await setadmin_command(self.update, self.context)
        
        # Verifica se add_admin foi chamado com os parâmetros corretos
        self.mock_mongodb.add_admin.assert_called_once_with(
            admin_id=987654321,
            admin_name="Usuário 987654321",
            added_by=123456789
        )
        
        # Verifica a mensagem de resposta
        self.message.reply_text.assert_called_once()
        args, kwargs = self.message.reply_text.call_args
        assert "foi adicionado como administrador do bot" in args[0]
        
    @pytest.mark.asyncio
    async def test_setadmin_command_with_reply(self):
        """Testa o comando /setadmin respondendo a uma mensagem."""
        # Configura a mensagem de resposta
        reply_user = MagicMock(spec=User)
        reply_user.id = 987654321
        reply_user.full_name = "Reply User"
        
        reply_message = MagicMock(spec=Message)
        reply_message.from_user = reply_user
        
        self.message.reply_to_message = reply_message
        
        # Configura o mock para add_admin
        self.mock_mongodb.add_admin = AsyncMock(return_value=True)
        
        await setadmin_command(self.update, self.context)
        
        # Verifica se add_admin foi chamado com os parâmetros corretos
        self.mock_mongodb.add_admin.assert_called_once_with(
            admin_id=987654321,
            admin_name="Reply User",
            added_by=123456789
        )
        
        # Verifica a mensagem de resposta
        self.message.reply_text.assert_called_once()
        args, kwargs = self.message.reply_text.call_args
        assert "foi adicionado como administrador do bot" in args[0]
        
    @pytest.mark.asyncio
    async def test_setadmin_command_user_already_admin(self):
        """Testa o comando /setadmin quando o usuário já é administrador."""
        # Configura o argumento
        self.context.args = ["987654321"]
        
        # Configura o mock para add_admin
        self.mock_mongodb.add_admin = AsyncMock(return_value=False)
        
        await setadmin_command(self.update, self.context)
        
        # Verifica a mensagem de resposta
        self.message.reply_text.assert_called_once()
        args, kwargs = self.message.reply_text.call_args
        assert "já é um administrador do bot" in args[0]
        
    @pytest.mark.asyncio
    async def test_setadmin_command_invalid_user_id(self):
        """Testa o comando /setadmin com ID de usuário inválido."""
        # Configura o argumento
        self.context.args = ["invalid_id"]
        
        await setadmin_command(self.update, self.context)
        
        # Verifica a mensagem de resposta
        self.message.reply_text.assert_called_once()
        args, kwargs = self.message.reply_text.call_args
        assert "Erro: O ID do usuário deve ser um número inteiro" in args[0]
        
    @pytest.mark.asyncio
    async def test_setadmin_command_add_self(self):
        """Testa o comando /setadmin tentando adicionar a si mesmo."""
        # Configura o argumento
        self.context.args = ["123456789"]  # Mesmo ID do usuário atual
        
        await setadmin_command(self.update, self.context)
        
        # Verifica a mensagem de resposta
        self.message.reply_text.assert_called_once()
        args, kwargs = self.message.reply_text.call_args
        assert "Você já é o proprietário do bot" in args[0]
        
    @pytest.mark.asyncio
    async def test_setadmin_command_add_owner(self):
        """Testa o comando /setadmin tentando adicionar o proprietário."""
        # Configura o argumento para um ID diferente
        self.context.args = ["987654321"]
        
        # Altera o retorno de get_owner_id para simular que o argumento é o proprietário
        self.mock_get_owner_id.return_value = 987654321
        
        await setadmin_command(self.update, self.context)
        
        # Verifica a mensagem de resposta
        self.message.reply_text.assert_called_once()
        args, kwargs = self.message.reply_text.call_args
        assert "Este usuário já é o proprietário do bot" in args[0]
        
    @pytest.mark.asyncio
    async def test_deladmin_command_no_args_no_reply(self):
        """Testa o comando /deladmin sem argumentos e sem resposta."""
        await deladmin_command(self.update, self.context)
        
        self.message.reply_text.assert_called_once()
        args, kwargs = self.message.reply_text.call_args
        assert "Erro: Você deve fornecer o ID do usuário ou responder a uma mensagem" in args[0]
        
    @pytest.mark.asyncio
    async def test_deladmin_command_with_args(self):
        """Testa o comando /deladmin com ID do usuário como argumento."""
        # Configura o argumento
        self.context.args = ["987654321"]
        
        # Configura o mock para remove_admin
        self.mock_mongodb.remove_admin = AsyncMock(return_value=True)
        
        await deladmin_command(self.update, self.context)
        
        # Verifica se remove_admin foi chamado com os parâmetros corretos
        self.mock_mongodb.remove_admin.assert_called_once_with(user_id=987654321)
        
        # Verifica a mensagem de resposta
        self.message.reply_text.assert_called_once()
        args, kwargs = self.message.reply_text.call_args
        assert "foi removido da lista de administradores do bot" in args[0]
        
    @pytest.mark.asyncio
    async def test_deladmin_command_with_reply(self):
        """Testa o comando /deladmin respondendo a uma mensagem."""
        # Configura a mensagem de resposta
        reply_user = MagicMock(spec=User)
        reply_user.id = 987654321
        
        reply_message = MagicMock(spec=Message)
        reply_message.from_user = reply_user
        
        self.message.reply_to_message = reply_message
        
        # Configura o mock para remove_admin
        self.mock_mongodb.remove_admin = AsyncMock(return_value=True)
        
        await deladmin_command(self.update, self.context)
        
        # Verifica se remove_admin foi chamado com os parâmetros corretos
        self.mock_mongodb.remove_admin.assert_called_once_with(user_id=987654321)
        
        # Verifica a mensagem de resposta
        self.message.reply_text.assert_called_once()
        args, kwargs = self.message.reply_text.call_args
        assert "foi removido da lista de administradores do bot" in args[0]
        
    @pytest.mark.asyncio
    async def test_deladmin_command_user_not_admin(self):
        """Testa o comando /deladmin quando o usuário não é administrador."""
        # Configura o argumento
        self.context.args = ["987654321"]
        
        # Configura o mock para remove_admin
        self.mock_mongodb.remove_admin = AsyncMock(return_value=False)
        
        await deladmin_command(self.update, self.context)
        
        # Verifica a mensagem de resposta
        self.message.reply_text.assert_called_once()
        args, kwargs = self.message.reply_text.call_args
        assert "não é um administrador do bot" in args[0]
        
    @pytest.mark.asyncio
    async def test_deladmin_command_invalid_user_id(self):
        """Testa o comando /deladmin com ID de usuário inválido."""
        # Configura o argumento
        self.context.args = ["invalid_id"]
        
        await deladmin_command(self.update, self.context)
        
        # Verifica a mensagem de resposta
        self.message.reply_text.assert_called_once()
        args, kwargs = self.message.reply_text.call_args
        assert "Erro: O ID do usuário deve ser um número inteiro" in args[0]
        
    @pytest.mark.asyncio
    async def test_deladmin_command_remove_self(self):
        """Testa o comando /deladmin tentando remover a si mesmo."""
        # Configura o argumento
        self.context.args = ["123456789"]  # Mesmo ID do usuário atual
        
        await deladmin_command(self.update, self.context)
        
        # Verifica a mensagem de resposta
        self.message.reply_text.assert_called_once()
        args, kwargs = self.message.reply_text.call_args
        assert "Você é o proprietário do bot e não pode remover a si mesmo" in args[0]
        
    @pytest.mark.asyncio
    async def test_deladmin_command_remove_owner(self):
        """Testa o comando /deladmin tentando remover o proprietário."""
        # Configura o argumento para um ID diferente
        self.context.args = ["987654321"]
        
        # Altera o retorno de get_owner_id para simular que o argumento é o proprietário
        self.mock_get_owner_id.return_value = 987654321
        
        await deladmin_command(self.update, self.context)
        
        # Verifica a mensagem de resposta
        self.message.reply_text.assert_called_once()
        args, kwargs = self.message.reply_text.call_args
        assert "Não é possível remover o proprietário do bot" in args[0]
        
    @pytest.mark.asyncio
    async def test_listadmins_command_with_admins(self):
        """Testa o comando /listadmins quando há administradores."""
        # Configura o mock para get_admins
        admin1 = {"admin_id": 111111, "admin_name": "Admin 1"}
        admin2 = {"admin_id": 222222, "admin_name": "Admin 2"}
        self.mock_mongodb.get_admins = AsyncMock(return_value=[admin1, admin2])
        
        await listadmins_command(self.update, self.context)
        
        # Verifica a mensagem de resposta
        self.message.reply_text.assert_called_once()
        args, kwargs = self.message.reply_text.call_args
        assert "Lista de administradores do bot" in args[0]
        assert "Admin 1" in args[0]
        assert "Admin 2" in args[0]
        assert "Total: 2 administrador(es)" in args[0]
        
    @pytest.mark.asyncio
    async def test_listadmins_command_no_admins(self):
        """Testa o comando /listadmins quando não há administradores."""
        # Configura o mock para get_admins
        self.mock_mongodb.get_admins = AsyncMock(return_value=[])
        
        await listadmins_command(self.update, self.context)
        
        # Verifica a mensagem de resposta
        self.message.reply_text.assert_called_once()
        args, kwargs = self.message.reply_text.call_args
        assert "Não há administradores adicionais configurados para o bot" in args[0] 