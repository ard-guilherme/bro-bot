"""
Testes para os filtros personalizados do bot.
"""
import unittest
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User
from src.utils.filters import CustomFilters

class TestFilters(unittest.TestCase):
    """Testes para os filtros personalizados do bot."""

    def setUp(self):
        """Configuração inicial para os testes."""
        # Mock para o objeto Update
        self.update = MagicMock(spec=Update)
        self.update.effective_user = MagicMock(spec=User)
        self.update.effective_user.id = 123456789  # ID de usuário de teste

    @patch('src.utils.config.Config.get_owner_id')
    def test_owner_filter_with_owner(self, mock_get_owner_id):
        """Testa o filtro de proprietário com o proprietário."""
        # Arrange
        mock_get_owner_id.return_value = 123456789  # Mesmo ID do usuário de teste
        owner_filter = CustomFilters.owner_filter()
        
        # Act
        result = owner_filter.filter(self.update)
        
        # Assert
        self.assertTrue(result)
        mock_get_owner_id.assert_called_once()

    @patch('src.utils.config.Config.get_owner_id')
    def test_owner_filter_with_non_owner(self, mock_get_owner_id):
        """Testa o filtro de proprietário com um usuário que não é o proprietário."""
        # Arrange
        mock_get_owner_id.return_value = 987654321  # ID diferente do usuário de teste
        owner_filter = CustomFilters.owner_filter()
        
        # Act
        result = owner_filter.filter(self.update)
        
        # Assert
        self.assertFalse(result)
        mock_get_owner_id.assert_called_once()

    @patch('src.utils.config.Config.get_owner_id')
    def test_owner_filter_with_exception(self, mock_get_owner_id):
        """Testa o filtro de proprietário quando ocorre uma exceção."""
        # Arrange
        mock_get_owner_id.side_effect = ValueError("Erro de teste")
        owner_filter = CustomFilters.owner_filter()
        
        # Act
        result = owner_filter.filter(self.update)
        
        # Assert
        self.assertFalse(result)
        mock_get_owner_id.assert_called_once()
        
    @patch('src.utils.config.Config.get_owner_id')
    def test_only_owner_filter_with_owner(self, mock_get_owner_id):
        """Testa o filtro de apenas proprietário com o proprietário."""
        # Arrange
        mock_get_owner_id.return_value = 123456789  # Mesmo ID do usuário de teste
        only_owner_filter = CustomFilters.only_owner_filter()
        
        # Act
        result = only_owner_filter.filter(self.update)
        
        # Assert
        self.assertTrue(result)
        mock_get_owner_id.assert_called_once()

    @patch('src.utils.config.Config.get_owner_id')
    def test_only_owner_filter_with_non_owner(self, mock_get_owner_id):
        """Testa o filtro de apenas proprietário com um usuário que não é o proprietário."""
        # Arrange
        mock_get_owner_id.return_value = 987654321  # ID diferente do usuário de teste
        only_owner_filter = CustomFilters.only_owner_filter()
        
        # Act
        result = only_owner_filter.filter(self.update)
        
        # Assert
        self.assertFalse(result)
        mock_get_owner_id.assert_called_once()

    @patch('src.utils.config.Config.get_owner_id')
    def test_only_owner_filter_with_exception(self, mock_get_owner_id):
        """Testa o filtro de apenas proprietário quando ocorre uma exceção."""
        # Arrange
        mock_get_owner_id.side_effect = ValueError("Erro de teste")
        only_owner_filter = CustomFilters.only_owner_filter()
        
        # Act
        result = only_owner_filter.filter(self.update)
        
        # Assert
        self.assertFalse(result)
        mock_get_owner_id.assert_called_once() 