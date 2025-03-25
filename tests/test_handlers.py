"""
Testes para os handlers do bot.
"""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from telegram import Update, Message, Chat, User, ReactionTypeEmoji, PhotoSize, File
from telegram.ext import ContextTypes, CallbackContext
from src.bot.handlers import (
    start_command,
    help_command,
    error_handler,
    motivation_command,
    presentation_command,
    fecho_command,
    say_command,
    sayrecurrent_command,
    listrecurrent_command,
    delrecurrent_command
)
from src.bot.messages import Messages
import pytest

class TestHandlers(unittest.TestCase):
    """Testes para os handlers do bot."""

    def setUp(self):
        """Configuração inicial para os testes."""
        # Mock para o objeto Update
        self.update = MagicMock(spec=Update)
        self.update.effective_chat.id = 123456789
        self.update.message = MagicMock(spec=Message)
        self.update.message.chat = MagicMock(spec=Chat)
        self.update.message.chat.id = 123456789
        self.update.message.from_user = MagicMock(spec=User)
        self.update.message.from_user.first_name = "Test"
        self.update.message.delete = AsyncMock()
        
        # Mock para o objeto Context
        self.context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        self.context.bot = MagicMock()
        self.context.bot.send_message = AsyncMock()
        self.context.bot.set_message_reaction = AsyncMock()

    async def test_start_command(self):
        """Testa o comando /start."""
        # Act
        await start_command(self.update, self.context)
        
        # Assert
        self.context.bot.send_message.assert_called_once_with(
            chat_id=self.update.effective_chat.id,
            text=Messages.get_start_message()
        )
        
    async def test_help_command(self):
        """Testa o comando /help."""
        # Act
        await help_command(self.update, self.context)
        
        # Assert
        self.context.bot.send_message.assert_called_once_with(
            chat_id=self.update.effective_chat.id,
            text=Messages.get_help_message(),
            parse_mode="Markdown"
        )
        
    async def test_error_handler(self):
        """Testa o handler de erros."""
        # Arrange
        update = self.update
        context = self.context
        context.error = Exception("Test error")
        
        # Act
        await error_handler(update, context)
        
        # Assert
        self.context.bot.send_message.assert_called_once()
        
    @patch('src.bot.messages.Messages.get_random_motivation_message')
    async def test_motivation_command(self, mock_get_motivation):
        """Testa o comando /motivacao."""
        # Arrange
        mock_motivation = "💪 Teste de mensagem motivacional"
        mock_get_motivation.return_value = mock_motivation
        self.update.message.reply_to_message = None
        
        # Act
        await motivation_command(self.update, self.context)
        
        # Assert
        self.update.message.delete.assert_called_once()
        mock_get_motivation.assert_called_once()
        
        # Verifica se a mensagem enviada contém a motivação mockada
        call_args = self.context.bot.send_message.call_args[1]
        self.assertEqual(call_args['chat_id'], self.update.effective_chat.id)
        self.assertIn(mock_motivation, call_args['text'])
        
    @patch('src.bot.messages.Messages.get_motivation_message_async')
    async def test_motivation_command_with_reply(self, mock_get_motivation):
        """Testa o comando /motivacao quando usado como resposta a uma mensagem."""
        # Arrange
        mock_motivation = "💪 Teste de mensagem motivacional"
        mock_get_motivation.return_value = mock_motivation
        
        # Configura o update para simular uma resposta a uma mensagem
        replied_user = MagicMock(spec=User)
        replied_user.full_name = "Usuário Original"
        replied_user.id = 98765
        
        replied_message = MagicMock(spec=Message)
        replied_message.from_user = replied_user
        replied_message.text = "Estou sem motivação para treinar hoje"
        
        self.update.message.reply_to_message = replied_message
        
        # Act
        await motivation_command(self.update, self.context)
        
        # Assert
        self.update.message.delete.assert_called_once()
        # Verifica se a função foi chamada com o nome do usuário e o conteúdo da mensagem
        mock_get_motivation.assert_called_once_with("Usuário Original", "Estou sem motivação para treinar hoje")
        
        # Verifica se a mensagem foi enviada como resposta à mensagem original
        replied_message.reply_text.assert_called_once()
        
        # Verifica se a mensagem contém a motivação
        call_args = replied_message.reply_text.call_args[0]
        self.assertIn(mock_motivation, call_args[0])
        
    @patch('src.bot.messages.Messages.get_random_motivation_message')
    async def test_motivation_command_fallback(self, mock_get_motivation):
        """Testa o fallback do comando /motivacao quando a deleção falha."""
        # Arrange
        mock_motivation = "🔥 Outra mensagem motivacional de teste"
        mock_get_motivation.return_value = mock_motivation
        self.update.message.delete.side_effect = Exception("Test error")
        self.update.message.reply_to_message = None
        
        # Act
        await motivation_command(self.update, self.context)
        
        # Assert
        self.update.message.delete.assert_called_once()
        mock_get_motivation.assert_called_once()
        
        # Verifica se a mensagem de resposta contém a motivação mockada
        call_args = self.update.message.reply_text.call_args[0]
        self.assertIn(mock_motivation, call_args[0])
        
    @patch('src.bot.messages.Messages.get_motivation_message_async')
    async def test_motivation_command_with_reply_fallback(self, mock_get_motivation):
        """Testa o fallback do comando /motivacao com resposta quando a deleção falha."""
        # Arrange
        mock_motivation = "🔥 Mensagem motivacional personalizada"
        mock_get_motivation.return_value = mock_motivation
        self.update.message.delete.side_effect = Exception("Test error")
        
        # Configura o update para simular uma resposta a uma mensagem
        replied_user = MagicMock(spec=User)
        replied_user.full_name = "Usuário Original"
        replied_user.id = 98765
        
        replied_message = MagicMock(spec=Message)
        replied_message.from_user = replied_user
        replied_message.text = "Estou sem motivação para treinar hoje"
        
        self.update.message.reply_to_message = replied_message
        
        # Act
        await motivation_command(self.update, self.context)
        
        # Assert
        self.update.message.delete.assert_called_once()
        mock_get_motivation.assert_called_once_with("Usuário Original", "Estou sem motivação para treinar hoje")
        
        # Verifica se a mensagem temporária foi enviada
        self.context.bot.send_message.assert_called_once()
        
        # Verifica se a mensagem foi enviada como resposta à mensagem original
        replied_message.reply_text.assert_called_once()
        
        # Verifica se a mensagem contém a motivação
        call_args = replied_message.reply_text.call_args[0]
        self.assertIn(mock_motivation, call_args[0])
        
    @patch('src.bot.messages.Messages.get_presentation_response')
    @patch('src.bot.messages.Messages.get_random_positive_emoji')
    async def test_presentation_command_with_reply(self, mock_get_emoji, mock_get_presentation):
        """Testa o comando /apresentacao com resposta a uma mensagem."""
        # Arrange
        mock_get_presentation.return_value = "Resposta personalizada"
        mock_get_emoji.return_value = "👍"
        
        # Configura o update para simular uma resposta a uma mensagem
        replied_message = MagicMock(spec=Message)
        replied_message.text = "Olá, sou novo no grupo!"
        replied_message.message_id = 12345
        replied_message.photo = []  # Sem foto
        self.update.message.reply_to_message = replied_message
        
        # Act
        await presentation_command(self.update, self.context)
        
        # Assert
        self.update.message.delete.assert_called_once()
        mock_get_emoji.assert_called_once()
        self.context.bot.set_message_reaction.assert_called_once_with(
            chat_id=self.update.effective_chat.id,
            message_id=replied_message.message_id,
            reaction=[ReactionTypeEmoji("👍")]
        )
        mock_get_presentation.assert_called_once_with(
            message_content=replied_message.text,
            image_data=None,
            image_mime_type=None
        )
        replied_message.reply_text.assert_called_once_with("Resposta personalizada")
        
    @patch('src.bot.messages.Messages.get_presentation_response')
    @patch('src.bot.messages.Messages.get_random_positive_emoji')
    async def test_presentation_command_with_image(self, mock_get_emoji, mock_get_presentation):
        """Testa o comando /apresentacao com resposta a uma mensagem com imagem."""
        # Arrange
        mock_get_presentation.return_value = "Resposta personalizada com análise da imagem"
        mock_get_emoji.return_value = "👍"
        
        # Configura o update para simular uma resposta a uma mensagem com foto
        replied_message = MagicMock(spec=Message)
        replied_message.text = None
        replied_message.caption = "Olá, sou novo no grupo! Esta é minha foto na academia."
        replied_message.message_id = 12345
        
        # Simula uma foto na mensagem
        photo_size = MagicMock(spec=PhotoSize)
        photo_size.file_id = "test_file_id"
        replied_message.photo = [photo_size]  # Lista com uma foto
        
        # Simula o arquivo da foto
        photo_file = MagicMock(spec=File)
        photo_file.download_to_memory = AsyncMock()
        
        # Configura o bot para retornar o arquivo da foto
        self.context.bot.get_file = AsyncMock(return_value=photo_file)
        
        self.update.message.reply_to_message = replied_message
        
        # Act
        await presentation_command(self.update, self.context)
        
        # Assert
        self.update.message.delete.assert_called_once()
        mock_get_emoji.assert_called_once()
        self.context.bot.set_message_reaction.assert_called_once_with(
            chat_id=self.update.effective_chat.id,
            message_id=replied_message.message_id,
            reaction=[ReactionTypeEmoji("👍")]
        )
        self.context.bot.get_file.assert_called_once_with(photo_size.file_id)
        photo_file.download_to_memory.assert_called_once()
        
        # Verifica se a chamada para get_presentation_response inclui os parâmetros de imagem
        mock_get_presentation.assert_called_once()
        call_args = mock_get_presentation.call_args[1]
        self.assertEqual(call_args['message_content'], replied_message.caption)
        self.assertIsNotNone(call_args['image_data'])  # Não podemos verificar o valor exato, mas deve ser passado
        self.assertEqual(call_args['image_mime_type'], "image/jpeg")
        
        replied_message.reply_text.assert_called_once_with("Resposta personalizada com análise da imagem")
        
    @patch('src.bot.messages.Messages.get_presentation_response')
    @patch('src.bot.messages.Messages.get_random_positive_emoji')
    async def test_presentation_command_delete_error(self, mock_get_emoji, mock_get_presentation):
        """Testa o comando /apresentacao quando ocorre erro na deleção."""
        # Arrange
        mock_get_presentation.return_value = "Resposta personalizada"
        mock_get_emoji.return_value = "👍"
        
        # Configura o update para simular uma resposta a uma mensagem
        replied_message = MagicMock(spec=Message)
        replied_message.text = "Olá, sou novo no grupo!"
        replied_message.message_id = 12345
        replied_message.photo = []  # Sem foto
        self.update.message.reply_to_message = replied_message
        
        # Simula erro na deleção
        self.update.message.delete.side_effect = Exception("Erro ao deletar")
        
        # Act
        await presentation_command(self.update, self.context)
        
        # Assert
        self.update.message.delete.assert_called_once()
        mock_get_emoji.assert_called_once()  # Deve ser chamado mesmo se a deleção falhar
        self.context.bot.set_message_reaction.assert_called_once_with(
            chat_id=self.update.effective_chat.id,
            message_id=replied_message.message_id,
            reaction=[ReactionTypeEmoji("👍")]
        )
        mock_get_presentation.assert_called_once_with(
            message_content=replied_message.text,
            image_data=None,
            image_mime_type=None
        )
        replied_message.reply_text.assert_called_once_with("Resposta personalizada")
        
    async def test_presentation_command_without_reply(self):
        """Testa o comando /apresentacao sem resposta a uma mensagem."""
        # Arrange
        self.update.message.reply_to_message = None
        
        # Act
        await presentation_command(self.update, self.context)
        
        # Assert
        self.update.message.delete.assert_not_called()
        self.update.message.reply_text.assert_called_once_with(
            "Este comando deve ser usado respondendo a uma mensagem de apresentação."
        )
        
    @patch('src.bot.messages.Messages.get_presentation_response')
    @patch('src.bot.messages.Messages.get_random_positive_emoji')
    async def test_presentation_command_api_error(self, mock_get_emoji, mock_get_presentation):
        """Testa o comando /apresentacao quando ocorre erro na API."""
        # Arrange
        mock_get_presentation.side_effect = Exception("Erro na API")
        mock_get_emoji.return_value = "👍"
        
        # Configura o update para simular uma resposta a uma mensagem
        replied_message = MagicMock(spec=Message)
        replied_message.text = "Olá, sou novo no grupo!"
        replied_message.message_id = 12345
        replied_message.photo = []  # Sem foto
        self.update.message.reply_to_message = replied_message
        
        # Act
        await presentation_command(self.update, self.context)
        
        # Assert
        self.update.message.delete.assert_called_once()
        mock_get_emoji.assert_called_once()
        self.context.bot.set_message_reaction.assert_called_once_with(
            chat_id=self.update.effective_chat.id,
            message_id=replied_message.message_id,
            reaction=[ReactionTypeEmoji("👍")]
        )
        mock_get_presentation.assert_called_once_with(
            message_content=replied_message.text,
            image_data=None,
            image_mime_type=None
        )
        # Verifica que a mensagem genérica é enviada para a mensagem original
        replied_message.reply_text.assert_called_once_with(
            "Bem-vindo ao grupo! Obrigado por se apresentar."
        )

    @patch('src.bot.messages.Messages.get_presentation_response')
    @patch('src.bot.messages.Messages.get_random_positive_emoji')
    async def test_presentation_command_reaction_error(self, mock_get_emoji, mock_get_presentation):
        """Testa o comando /apresentacao quando ocorre erro ao adicionar reação."""
        # Arrange
        mock_get_presentation.return_value = "Resposta personalizada"
        mock_get_emoji.return_value = "👍"
        
        # Configura o update para simular uma resposta a uma mensagem
        replied_message = MagicMock(spec=Message)
        replied_message.text = "Olá, sou novo no grupo!"
        replied_message.message_id = 12345
        replied_message.photo = []  # Sem foto
        self.update.message.reply_to_message = replied_message
        
        # Simula erro ao adicionar reação
        self.context.bot.set_message_reaction.side_effect = Exception("Erro ao adicionar reação")
        
        # Act
        await presentation_command(self.update, self.context)
        
        # Assert
        self.update.message.delete.assert_called_once()
        mock_get_emoji.assert_called_once()
        self.context.bot.set_message_reaction.assert_called_once_with(
            chat_id=self.update.effective_chat.id,
            message_id=replied_message.message_id,
            reaction=[ReactionTypeEmoji("👍")]
        )
        # Verifica que a resposta ainda é enviada mesmo se a reação falhar
        mock_get_presentation.assert_called_once_with(
            message_content=replied_message.text,
            image_data=None,
            image_mime_type=None
        )
        replied_message.reply_text.assert_called_once_with("Resposta personalizada")
        
    @patch('src.bot.messages.Messages.get_presentation_response')
    @patch('src.bot.messages.Messages.get_random_positive_emoji')
    async def test_presentation_command_image_download_error(self, mock_get_emoji, mock_get_presentation):
        """Testa o comando /apresentacao quando ocorre erro ao baixar a imagem."""
        # Arrange
        mock_get_presentation.return_value = "Resposta personalizada sem análise da imagem"
        mock_get_emoji.return_value = "👍"
        
        # Configura o update para simular uma resposta a uma mensagem com foto
        replied_message = MagicMock(spec=Message)
        replied_message.text = None
        replied_message.caption = "Olá, sou novo no grupo! Esta é minha foto na academia."
        replied_message.message_id = 12345
        
        # Simula uma foto na mensagem
        photo_size = MagicMock(spec=PhotoSize)
        photo_size.file_id = "test_file_id"
        replied_message.photo = [photo_size]  # Lista com uma foto
        
        # Simula erro ao obter o arquivo da foto
        self.context.bot.get_file = AsyncMock(side_effect=Exception("Erro ao obter arquivo"))
        
        self.update.message.reply_to_message = replied_message
        
        # Act
        await presentation_command(self.update, self.context)
        
        # Assert
        self.update.message.delete.assert_called_once()
        mock_get_emoji.assert_called_once()
        self.context.bot.set_message_reaction.assert_called_once_with(
            chat_id=self.update.effective_chat.id,
            message_id=replied_message.message_id,
            reaction=[ReactionTypeEmoji("👍")]
        )
        self.context.bot.get_file.assert_called_once_with(photo_size.file_id)
        
        # Verifica que a chamada para get_presentation_response não inclui os parâmetros de imagem
        mock_get_presentation.assert_called_once_with(
            message_content=replied_message.caption,
            image_data=None,
            image_mime_type=None
        )
        
        replied_message.reply_text.assert_called_once_with("Resposta personalizada sem análise da imagem")

    @patch('src.bot.messages.Messages.get_fecho_message_async')
    @patch('src.bot.handlers.is_admin')
    async def test_fecho_command(self, mock_is_admin, mock_get_fecho):
        """Testa o comando /fecho sem resposta a uma mensagem."""
        # Arrange
        mock_is_admin.return_value = True
        mock_fecho = "😂 Teste de tirada sarcástica"
        mock_get_fecho.return_value = mock_fecho
        self.update.message.reply_to_message = None
        
        # Act
        await fecho_command(self.update, self.context)
        
        # Assert
        self.update.message.delete.assert_called_once()
        mock_get_fecho.assert_called_once_with()
        
        # Verifica se a mensagem foi enviada para o chat
        self.context.bot.send_message.assert_called_once_with(
            chat_id=self.update.effective_chat.id,
            text=mock_fecho
        )
        
    @patch('src.bot.messages.Messages.get_fecho_message_async')
    @patch('src.bot.handlers.is_admin')
    async def test_fecho_command_with_reply(self, mock_is_admin, mock_get_fecho):
        """Testa o comando /fecho com resposta a uma mensagem."""
        # Arrange
        mock_is_admin.return_value = True
        mock_fecho = "🤣 Outra tirada sarcástica de teste"
        mock_get_fecho.return_value = mock_fecho
        
        # Configura o update para simular uma resposta a uma mensagem
        replied_user = MagicMock(spec=User)
        replied_user.full_name = "Usuário Original"
        replied_user.id = 98765
        
        replied_message = MagicMock(spec=Message)
        replied_message.from_user = replied_user
        replied_message.text = "Hoje eu fiz 10 repetições de supino"
        replied_message.reply_text = AsyncMock()
        
        self.update.message.reply_to_message = replied_message
        
        # Act
        await fecho_command(self.update, self.context)
        
        # Assert
        self.update.message.delete.assert_called_once()
        # Verifica se a função foi chamada com o nome do usuário e o conteúdo da mensagem
        mock_get_fecho.assert_called_once_with("Usuário Original", "Hoje eu fiz 10 repetições de supino")
        
        # Verifica se a mensagem foi enviada como resposta à mensagem original
        replied_message.reply_text.assert_called_once_with(mock_fecho)
        
    @patch('src.bot.messages.Messages.get_fecho_message_async')
    @patch('src.bot.handlers.is_admin')
    async def test_fecho_command_fallback(self, mock_is_admin, mock_get_fecho):
        """Testa o fallback do comando /fecho quando a deleção falha."""
        # Arrange
        mock_is_admin.return_value = True
        mock_fecho = "😂 Tirada sarcástica de fallback"
        mock_get_fecho.return_value = mock_fecho
        self.update.message.delete.side_effect = Exception("Test error")
        self.update.message.reply_to_message = None
        
        # Act
        await fecho_command(self.update, self.context)
        
        # Assert
        self.update.message.delete.assert_called_once()
        mock_get_fecho.assert_called_once()
        
        # Verifica se a mensagem de erro foi enviada
        self.update.message.reply_text.assert_called_once_with(
            "Não foi possível deletar o comando. Verifique as permissões do bot.",
            reply_to_message_id=self.update.message.message_id
        )
        
        # Verifica se a mensagem de resposta contém a tirada sarcástica mockada
        self.update.message.reply_text.assert_called_once()
        
    @patch('src.bot.messages.Messages.get_fecho_message_async')
    @patch('src.bot.handlers.is_admin')
    async def test_fecho_command_with_reply_fallback(self, mock_is_admin, mock_get_fecho):
        """Testa o fallback do comando /fecho com resposta quando a deleção falha."""
        # Arrange
        mock_is_admin.return_value = True
        mock_fecho = "🤣 Tirada sarcástica de fallback para resposta"
        mock_get_fecho.return_value = mock_fecho
        self.update.message.delete.side_effect = Exception("Test error")
        
        # Configura o update para simular uma resposta a uma mensagem
        replied_user = MagicMock(spec=User)
        replied_user.full_name = "Usuário Original"
        replied_user.id = 98765
        
        replied_message = MagicMock(spec=Message)
        replied_message.from_user = replied_user
        replied_message.text = "Hoje eu fiz 10 repetições de supino"
        replied_message.reply_text = AsyncMock()
        
        self.update.message.reply_to_message = replied_message
        
        # Act
        await fecho_command(self.update, self.context)
        
        # Assert
        self.update.message.delete.assert_called_once()
        
        # Verifica se a mensagem de erro foi enviada
        self.update.message.reply_text.assert_called_once_with(
            "Não foi possível deletar o comando. Verifique as permissões do bot.",
            reply_to_message_id=self.update.message.message_id
        )
        
        # Verifica se a função foi chamada com o nome do usuário e o conteúdo da mensagem
        mock_get_fecho.assert_called_once_with("Usuário Original", "Hoje eu fiz 10 repetições de supino")
        
        # Verifica se a mensagem foi enviada como resposta à mensagem original
        replied_message.reply_text.assert_called_once_with(mock_fecho)
        
    @patch('src.bot.handlers.is_admin')
    @pytest.mark.asyncio
    async def test_fecho_command_not_admin(self, mock_is_admin):
        """Testa o comando /fecho quando o usuário não é administrador."""
        # Arrange
        mock_is_admin.return_value = False
        
        # Act
        await fecho_command(self.update, self.context)
        
        # Assert
        mock_is_admin.assert_called_once()
        self.update.message.reply_text.assert_called_once_with(
            "Apenas administradores podem usar este comando.",
            reply_to_message_id=self.update.message.message_id
        )

    @patch('src.bot.handlers.is_admin')
    @pytest.mark.asyncio
    async def test_say_command(self, mock_is_admin):
        """Testa o comando /say."""
        # Arrange
        mock_is_admin.return_value = True
        self.update.message.text = "/say Esta é uma mensagem de teste da administração"
        
        # Act
        await say_command(self.update, self.context)
        
        # Assert
        self.update.message.delete.assert_called_once()
        
        # Verifica se a mensagem foi enviada para o chat
        self.context.bot.send_message.assert_called_once_with(
            chat_id=self.update.effective_chat.id,
            text="*🟢 MENSAGEM DA ADMINISTRAÇÃO 🟢*\n\nEsta é uma mensagem de teste da administração\n\n-------------------------------------",
            parse_mode="Markdown"
        )
    
    @patch('src.bot.handlers.is_admin')
    @pytest.mark.asyncio
    async def test_say_command_empty_message(self, mock_is_admin):
        """Testa o comando /say com mensagem vazia."""
        # Arrange
        mock_is_admin.return_value = True
        self.update.message.text = "/say"
        
        # Act
        await say_command(self.update, self.context)
        
        # Assert
        self.update.message.delete.assert_not_called()
        
        # Verifica se a mensagem de erro foi enviada
        self.update.message.reply_text.assert_called_once()
        
    @patch('src.bot.handlers.is_admin')
    @pytest.mark.asyncio
    async def test_say_command_not_admin(self, mock_is_admin):
        """Testa o comando /say quando o usuário não é administrador."""
        # Arrange
        mock_is_admin.return_value = False
        self.update.message.text = "/say Esta é uma mensagem de teste"
        
        # Act
        await say_command(self.update, self.context)
        
        # Assert
        self.update.message.delete.assert_not_called()
        self.context.bot.send_message.assert_not_called()
        
        # Verifica se a mensagem de erro foi enviada
        self.update.message.reply_text.assert_called_once()

    @patch('src.bot.handlers.is_admin')
    @patch('src.utils.recurring_messages_manager.recurring_messages_manager')
    @pytest.mark.asyncio
    async def test_sayrecurrent_command(self, mock_manager, mock_is_admin):
        """Testa o comando /sayrecurrent."""
        # Arrange
        mock_is_admin.return_value = True
        mock_manager.add_recurring_message.return_value = "test_message_id"
        self.update.message.text = "/sayrecurrent 12 Esta é uma mensagem recorrente de teste"
        
        # Act
        await sayrecurrent_command(self.update, self.context)
        
        # Assert
        self.update.message.delete.assert_called_once()
        mock_manager.add_recurring_message.assert_called_once_with(
            chat_id=self.update.effective_chat.id,
            message="Esta é uma mensagem recorrente de teste",
            interval_hours=12.0,
            added_by=self.update.effective_user.id,
            added_by_name=self.update.effective_user.full_name or f"@{self.update.effective_user.username}" or "Desconhecido"
        )
        
        # Verifica se a mensagem de confirmação foi enviada
        self.context.bot.send_message.assert_called_once()
        call_args = self.context.bot.send_message.call_args[1]
        self.assertEqual(call_args['chat_id'], self.update.effective_chat.id)
        self.assertIn("Mensagem recorrente configurada com sucesso", call_args['text'])
        self.assertIn("test_message_id", call_args['text'])
        self.assertEqual(call_args['parse_mode'], "Markdown")
    
    @patch('src.bot.handlers.is_admin')
    @patch('src.utils.recurring_messages_manager.recurring_messages_manager')
    @pytest.mark.asyncio
    async def test_sayrecurrent_command_invalid_interval(self, mock_manager, mock_is_admin):
        """Testa o comando /sayrecurrent com intervalo inválido."""
        # Arrange
        mock_is_admin.return_value = True
        self.update.message.text = "/sayrecurrent abc Esta é uma mensagem recorrente de teste"
        self.update.message.reply_text = AsyncMock()
        
        # Act
        await sayrecurrent_command(self.update, self.context)
        
        # Assert
        self.update.message.delete.assert_not_called()
        mock_manager.add_recurring_message.assert_not_called()
        
        # Verifica se a mensagem de erro foi enviada
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args[0]
        self.assertIn("O intervalo deve ser um número válido", call_args[0])
    
    @patch('src.bot.handlers.is_admin')
    @patch('src.utils.recurring_messages_manager.recurring_messages_manager')
    @pytest.mark.asyncio
    async def test_listrecurrent_command(self, mock_manager, mock_is_admin):
        """Testa o comando /listrecurrent."""
        # Arrange
        mock_is_admin.return_value = True
        
        # Cria uma lista de mensagens recorrentes de exemplo
        from datetime import datetime
        from bson.objectid import ObjectId
        
        mock_messages = [
            {
                "_id": ObjectId("123456789012345678901234"),
                "chat_id": self.update.effective_chat.id,
                "message": "Mensagem recorrente de teste 1",
                "interval_hours": 12.0,
                "added_by": 123456,
                "added_by_name": "Usuário Teste",
                "created_at": datetime.now(),
                "last_sent_at": datetime.now(),
                "active": True
            },
            {
                "_id": ObjectId("123456789012345678901235"),
                "chat_id": self.update.effective_chat.id,
                "message": "Mensagem recorrente de teste 2",
                "interval_hours": 24.0,
                "added_by": 123456,
                "added_by_name": "Usuário Teste",
                "created_at": datetime.now(),
                "last_sent_at": None,
                "active": True
            }
        ]
        
        mock_manager.get_recurring_messages.return_value = mock_messages
        
        # Act
        await listrecurrent_command(self.update, self.context)
        
        # Assert
        self.update.message.delete.assert_called_once()
        mock_manager.get_recurring_messages.assert_called_once_with(self.update.effective_chat.id)
        
        # Verifica se a lista de mensagens foi enviada
        self.context.bot.send_message.assert_called_once()
        call_args = self.context.bot.send_message.call_args[1]
        self.assertEqual(call_args['chat_id'], self.update.effective_chat.id)
        self.assertIn("Lista de Mensagens Recorrentes", call_args['text'])
        self.assertIn("123456789012345678901234", call_args['text'])
        self.assertIn("123456789012345678901235", call_args['text'])
        self.assertEqual(call_args['parse_mode'], "Markdown")
    
    @patch('src.bot.handlers.is_admin')
    @patch('src.utils.recurring_messages_manager.recurring_messages_manager')
    @pytest.mark.asyncio
    async def test_listrecurrent_command_empty(self, mock_manager, mock_is_admin):
        """Testa o comando /listrecurrent quando não há mensagens recorrentes."""
        # Arrange
        mock_is_admin.return_value = True
        mock_manager.get_recurring_messages.return_value = []
        self.update.message.reply_text = AsyncMock()
        
        # Act
        await listrecurrent_command(self.update, self.context)
        
        # Assert
        self.update.message.delete.assert_not_called()
        mock_manager.get_recurring_messages.assert_called_once_with(self.update.effective_chat.id)
        
        # Verifica se a mensagem de aviso foi enviada
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args[0]
        self.assertIn("Não há mensagens recorrentes", call_args[0])
    
    @patch('src.bot.handlers.is_admin')
    @patch('src.utils.recurring_messages_manager.recurring_messages_manager')
    @pytest.mark.asyncio
    async def test_delrecurrent_command(self, mock_manager, mock_is_admin):
        """Testa o comando /delrecurrent."""
        # Arrange
        mock_is_admin.return_value = True
        mock_manager.delete_recurring_message.return_value = True
        self.update.message.text = "/delrecurrent 123456789012345678901234"
        
        # Act
        await delrecurrent_command(self.update, self.context)
        
        # Assert
        self.update.message.delete.assert_called_once()
        mock_manager.delete_recurring_message.assert_called_once_with("123456789012345678901234")
        
        # Verifica se a mensagem de confirmação foi enviada
        self.context.bot.send_message.assert_called_once()
        call_args = self.context.bot.send_message.call_args[1]
        self.assertEqual(call_args['chat_id'], self.update.effective_chat.id)
        self.assertIn("Mensagem recorrente desativada com sucesso", call_args['text'])
        self.assertIn("123456789012345678901234", call_args['text'])
        self.assertEqual(call_args['parse_mode'], "Markdown")
    
    @patch('src.bot.handlers.is_admin')
    @patch('src.utils.recurring_messages_manager.recurring_messages_manager')
    @pytest.mark.asyncio
    async def test_delrecurrent_command_invalid_id(self, mock_manager, mock_is_admin):
        """Testa o comando /delrecurrent com ID inválido."""
        # Arrange
        mock_is_admin.return_value = True
        mock_manager.delete_recurring_message.return_value = False
        self.update.message.text = "/delrecurrent 123456789012345678901234"
        self.update.message.reply_text = AsyncMock()
        
        # Act
        await delrecurrent_command(self.update, self.context)
        
        # Assert
        self.update.message.delete.assert_not_called()
        mock_manager.delete_recurring_message.assert_called_once_with("123456789012345678901234")
        
        # Verifica se a mensagem de erro foi enviada
        self.update.message.reply_text.assert_called_once()
        call_args = self.update.message.reply_text.call_args[0]
        self.assertIn("Erro ao desativar mensagem recorrente", call_args[0])

if __name__ == "__main__":
    unittest.main() 