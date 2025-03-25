"""
Testes para o arquivo main.py.
"""
import unittest
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Chat, User
from telegram.ext import ContextTypes
from src.main import unauthorized_message_handler

class TestMain(unittest.TestCase):
    """Testes para o arquivo main.py."""

    def setUp(self):
        """Configuração inicial para os testes."""
        # Mock para o objeto Update
        self.update = MagicMock(spec=Update)
        self.update.effective_user = MagicMock(spec=User)
        self.update.effective_user.id = 123456789
        self.update.effective_chat = MagicMock(spec=Chat)
        self.update.effective_chat.id = 987654321
        self.update.effective_chat.type = "private"
        
        # Mock para o objeto Context
        self.context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        self.context.bot = MagicMock()
        self.context.bot.send_message = AsyncMock()

    @pytest.mark.asyncio
    @patch('src.main.logger')
    async def test_unauthorized_message_handler(self, mock_logger):
        """Testa o handler de mensagens não autorizadas."""
        # Act
        await unauthorized_message_handler(self.update, self.context)
        
        # Assert
        # Verifica se o logger foi chamado com a mensagem de aviso
        mock_logger.warning.assert_called_once()
        
        # Verifica se a mensagem de aviso contém as informações corretas
        warning_message = mock_logger.warning.call_args[0][0]
        assert "Usuário não autorizado" in warning_message
        assert str(self.update.effective_user.id) in warning_message
        assert str(self.update.effective_chat.id) in warning_message
        assert self.update.effective_chat.type in warning_message
        
        # Verifica se o bot não enviou nenhuma mensagem
        self.context.bot.send_message.assert_not_called() 