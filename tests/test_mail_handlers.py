"""
Testes para os handlers do correio elegante.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.bot.mail_handlers import MailHandlers


class TestMailHandlers:
    """Testes para a classe MailHandlers."""
    
    @pytest.mark.asyncio
    async def test_contains_offensive_content(self):
        """Testa o filtro de conteúdo ofensivo."""
        # Conteúdo ofensivo
        assert await MailHandlers._contains_offensive_content("Você é um idiota")
        assert await MailHandlers._contains_offensive_content("Que merda é essa?")
        assert await MailHandlers._contains_offensive_content("PORRA!")
        
        # Conteúdo normal
        assert not await MailHandlers._contains_offensive_content("Olá, como vai?")
        assert not await MailHandlers._contains_offensive_content("Bom treino hoje!")
        assert not await MailHandlers._contains_offensive_content("Parabéns pelo shape!")
    
    @pytest.mark.asyncio
    async def test_check_user_in_group_success(self):
        """Testa verificação de usuário no grupo - sucesso."""
        # Mock do bot
        mock_bot = AsyncMock()
        mock_member = MagicMock()
        mock_member.status = 'member'
        mock_bot.get_chat_member.return_value = mock_member
        
        # Teste
        result = await MailHandlers._check_user_in_group(mock_bot, -123456789, "testuser")
        
        assert result is True
        mock_bot.get_chat_member.assert_called_once_with(-123456789, "@testuser")
    
    @pytest.mark.asyncio
    async def test_check_user_in_group_not_member(self):
        """Testa verificação de usuário no grupo - não é membro."""
        # Mock do bot
        mock_bot = AsyncMock()
        mock_member = MagicMock()
        mock_member.status = 'left'
        mock_bot.get_chat_member.return_value = mock_member
        
        # Teste
        result = await MailHandlers._check_user_in_group(mock_bot, -123456789, "testuser")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_user_in_group_error(self):
        """Testa verificação de usuário no grupo - erro."""
        # Mock do bot que gera exceção
        mock_bot = AsyncMock()
        mock_bot.get_chat_member.side_effect = Exception("User not found")
        
        # Teste
        result = await MailHandlers._check_user_in_group(mock_bot, -123456789, "testuser")
        
        assert result is False
    
    @pytest.mark.asyncio
    @patch('src.bot.mail_handlers.mongodb_client')
    async def test_generate_pix_payment_success(self, mock_mongodb):
        """Testa geração de pagamento Pix - sucesso."""
        # Mock das configurações
        with patch('src.bot.mail_handlers.Config.get_pix_key', return_value="12345678901"):
            # Mock do MongoDB
            mock_mongodb.create_pix_payment.return_value = True
            
            # Teste
            pix_key, pix_id = await MailHandlers._generate_pix_payment(123456, "mail_id_123")
            
            assert pix_key == "12345678901"
            assert pix_id is not None
            assert pix_id.startswith("PIX_123456_mail_id_123_")
            mock_mongodb.create_pix_payment.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.bot.mail_handlers.mongodb_client')
    async def test_generate_pix_payment_config_error(self, mock_mongodb):
        """Testa geração de pagamento Pix - erro de configuração."""
        # Mock das configurações que gera erro
        with patch('src.bot.mail_handlers.Config.get_pix_key', side_effect=ValueError("Chave não encontrada")):
            # Teste
            pix_key, pix_id = await MailHandlers._generate_pix_payment(123456, "mail_id_123")
            
            assert pix_key is None
            assert pix_id is None
            mock_mongodb.create_pix_payment.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('src.bot.mail_handlers.mongodb_client')
    async def test_correio_command_not_private_chat(self, mock_mongodb):
        """Testa comando /correio em chat que não é privado."""
        # Mock do update
        mock_update = MagicMock()
        mock_update.effective_chat.type = 'group'
        mock_update.message.reply_text = AsyncMock()
        
        # Mock do context
        mock_context = MagicMock()
        
        # Teste
        result = await MailHandlers.correio_command(mock_update, mock_context)
        
        # Verificações
        assert result == -1  # ConversationHandler.END
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "chat privado" in call_args
    
    @pytest.mark.asyncio
    @patch('src.bot.mail_handlers.mongodb_client')
    async def test_correio_command_daily_limit_reached(self, mock_mongodb):
        """Testa comando /correio com limite diário atingido."""
        # Mock do MongoDB
        mock_mongodb.get_daily_mail_count.return_value = 2
        
        # Mock do update
        mock_update = MagicMock()
        mock_update.effective_chat.type = 'private'
        mock_update.effective_user.id = 123456
        mock_update.effective_user.full_name = "Test User"
        mock_update.message.reply_text = AsyncMock()
        
        # Mock do context
        mock_context = MagicMock()
        
        # Teste
        result = await MailHandlers.correio_command(mock_update, mock_context)
        
        # Verificações
        assert result == -1  # ConversationHandler.END
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "2 correios hoje" in call_args
        mock_mongodb.get_daily_mail_count.assert_called_once_with(123456)
    
    @pytest.mark.asyncio
    @patch('src.bot.mail_handlers.mongodb_client')
    async def test_correio_command_success(self, mock_mongodb):
        """Testa comando /correio com sucesso."""
        # Mock do MongoDB
        mock_mongodb.get_daily_mail_count.return_value = 0
        
        # Mock do update
        mock_update = MagicMock()
        mock_update.effective_chat.type = 'private'
        mock_update.effective_user.id = 123456
        mock_update.effective_user.full_name = "Test User"
        mock_update.message.reply_text = AsyncMock()
        
        # Mock do context
        mock_context = MagicMock()
        
        # Teste
        result = await MailHandlers.correio_command(mock_update, mock_context)
        
        # Verificações
        assert result == 0  # MAIL_MESSAGE state
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "CORREIO ELEGANTE" in call_args
        assert "Digite sua mensagem" in call_args
        
        # Verificar se dados foram armazenados no contexto
        assert mock_context.user_data['mail_sender_id'] == 123456
        assert mock_context.user_data['mail_sender_name'] == "Test User"
    
    @pytest.mark.asyncio
    async def test_handle_mail_message_too_short(self):
        """Testa processamento de mensagem muito curta."""
        # Mock do update
        mock_update = MagicMock()
        mock_update.message.text = "Oi"
        mock_update.message.reply_text = AsyncMock()
        
        # Mock do context
        mock_context = MagicMock()
        
        # Teste
        result = await MailHandlers.handle_mail_message(mock_update, mock_context)
        
        # Verificações
        assert result == 0  # MAIL_MESSAGE state (continua no mesmo estado)
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "muito curta" in call_args
    
    @pytest.mark.asyncio
    async def test_handle_mail_message_too_long(self):
        """Testa processamento de mensagem muito longa."""
        # Mock do update
        mock_update = MagicMock()
        mock_update.message.text = "A" * 501  # 501 caracteres
        mock_update.message.reply_text = AsyncMock()
        
        # Mock do context
        mock_context = MagicMock()
        
        # Teste
        result = await MailHandlers.handle_mail_message(mock_update, mock_context)
        
        # Verificações
        assert result == 0  # MAIL_MESSAGE state (continua no mesmo estado)
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "muito longa" in call_args
    
    @pytest.mark.asyncio
    async def test_handle_mail_message_offensive_content(self):
        """Testa processamento de mensagem com conteúdo ofensivo."""
        # Mock do update
        mock_update = MagicMock()
        mock_update.message.text = "Você é um idiota completo"
        mock_update.message.reply_text = AsyncMock()
        
        # Mock do context
        mock_context = MagicMock()
        
        # Teste
        result = await MailHandlers.handle_mail_message(mock_update, mock_context)
        
        # Verificações
        assert result == 0  # MAIL_MESSAGE state (continua no mesmo estado)
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "inapropriado" in call_args
    
    @pytest.mark.asyncio
    async def test_handle_mail_message_success(self):
        """Testa processamento de mensagem válida."""
        # Mock do update
        mock_update = MagicMock()
        mock_update.message.text = "Esta é uma mensagem válida para o correio elegante"
        mock_update.message.reply_text = AsyncMock()
        
        # Mock do context
        mock_context = MagicMock()
        
        # Teste
        result = await MailHandlers.handle_mail_message(mock_update, mock_context)
        
        # Verificações
        assert result == 1  # MAIL_RECIPIENT state
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "@ do destinatário" in call_args
        
        # Verificar se mensagem foi armazenada no contexto
        assert mock_context.user_data['mail_message'] == "Esta é uma mensagem válida para o correio elegante"


if __name__ == "__main__":
    pytest.main([__file__]) 