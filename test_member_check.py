#!/usr/bin/env python3
"""
Script de teste para investigar problemas de verificação de membros do grupo.
"""

import asyncio
import sys
from telegram import Bot
from telegram.error import TelegramError

# Configurações
TELEGRAM_TOKEN = "7947196058:AAEFtvIB8oVOHEHfFE-PO85M3gT2mrhbgvM"
GYM_NATION_CHAT_ID = -1002399443702
TEST_USERNAME = "jeffwindsor"
JEFFWINDSOR_USER_ID = 5072326494

async def test_member_verification():
    """Testa diferentes métodos de verificação de membro."""
    
    bot = Bot(token=TELEGRAM_TOKEN)
    
    print(f"🔍 Testando verificação de membro para @{TEST_USERNAME}")
    print(f"📍 Grupo: {GYM_NATION_CHAT_ID}")
    print("-" * 50)
    
    # Teste 1: Com @
    print(f"1️⃣ Testando com '@{TEST_USERNAME}':")
    try:
        member = await bot.get_chat_member(GYM_NATION_CHAT_ID, f"@{TEST_USERNAME}")
        print(f"   ✅ Sucesso! Status: {member.status}")
        print(f"   👤 User ID: {member.user.id}")
        print(f"   📛 Nome: {member.user.full_name}")
        print(f"   🔗 Username: @{member.user.username}")
    except TelegramError as e:
        print(f"   ❌ Erro: {e}")
    
    print()
    
    # Teste 2: Sem @
    print(f"2️⃣ Testando sem '@' (apenas '{TEST_USERNAME}'):")
    try:
        member = await bot.get_chat_member(GYM_NATION_CHAT_ID, TEST_USERNAME)
        print(f"   ✅ Sucesso! Status: {member.status}")
        print(f"   👤 User ID: {member.user.id}")
        print(f"   📛 Nome: {member.user.full_name}")
        print(f"   🔗 Username: @{member.user.username}")
    except TelegramError as e:
        print(f"   ❌ Erro: {e}")
    
    print()
    
    # Teste 3: Maiúscula
    print(f"3️⃣ Testando com maiúscula '@{TEST_USERNAME.capitalize()}':")
    try:
        member = await bot.get_chat_member(GYM_NATION_CHAT_ID, f"@{TEST_USERNAME.capitalize()}")
        print(f"   ✅ Sucesso! Status: {member.status}")
        print(f"   👤 User ID: {member.user.id}")
        print(f"   📛 Nome: {member.user.full_name}")
        print(f"   🔗 Username: @{member.user.username}")
    except TelegramError as e:
        print(f"   ❌ Erro: {e}")
    
    print()
    
    # Teste 4: Informações do chat
    print("4️⃣ Testando informações do chat:")
    try:
        chat = await bot.get_chat(GYM_NATION_CHAT_ID)
        print(f"   ✅ Chat encontrado!")
        print(f"   📛 Título: {chat.title}")
        print(f"   🔗 Username: @{chat.username if chat.username else 'Sem username'}")
        print(f"   👥 Tipo: {chat.type}")
        print(f"   👨‍💼 Descrição: {chat.description[:100] if chat.description else 'Sem descrição'}...")
    except TelegramError as e:
        print(f"   ❌ Erro: {e}")
    
    print()
    
    # Teste 5: Informações do bot
    print("5️⃣ Testando informações do bot:")
    try:
        await bot.initialize()
        bot_id = bot.id
        print(f"   🤖 Bot ID: {bot_id}")
        
        bot_member = await bot.get_chat_member(GYM_NATION_CHAT_ID, bot_id)
        print(f"   ✅ Bot encontrado! Status: {bot_member.status}")
        if hasattr(bot_member, 'can_restrict_members'):
            print(f"   🔒 Pode restringir membros: {bot_member.can_restrict_members}")
        if hasattr(bot_member, 'can_promote_members'):
            print(f"   👑 Pode promover membros: {bot_member.can_promote_members}")
    except TelegramError as e:
        print(f"   ❌ Erro: {e}")
    
    print()
    
    # Teste 6: Testar com o User ID do @jeffwindsor
    print("6️⃣ Testando com o User ID do @jeffwindsor:")
    try:
        member = await bot.get_chat_member(GYM_NATION_CHAT_ID, JEFFWINDSOR_USER_ID)
        print(f"   ✅ Sucesso! Status: {member.status}")
        print(f"   👤 User ID: {member.user.id}")
        print(f"   📛 Nome: {member.user.full_name}")
        print(f"   🔗 Username: @{member.user.username if member.user.username else 'Sem username'}")
    except TelegramError as e:
        print(f"   ❌ Erro: {e}")
    
    print()
    
    # Teste 7: Testar com o User ID do proprietário do bot (@gggcmx)
    print("7️⃣ Testando com o User ID do proprietário do bot (@gggcmx):")
    owner_id = 1277961359  # Seu User ID do .env
    try:
        member = await bot.get_chat_member(GYM_NATION_CHAT_ID, owner_id)
        print(f"   ✅ Sucesso! Status: {member.status}")
        print(f"   👤 User ID: {member.user.id}")
        print(f"   📛 Nome: {member.user.full_name}")
        print(f"   🔗 Username: @{member.user.username if member.user.username else 'Sem username'}")
    except TelegramError as e:
        print(f"   ❌ Erro: {e}")
    
    print()
    print("💡 **Conclusão:**")
    print("   O username @jeffwindsor existe, mas a API falha ao buscá-lo.")
    print("   Isso pode ser devido a configurações de privacidade específicas.")
    print("   User ID funciona melhor que username para validação.")
    print("   Recomendação: implementar fallback para User ID ou permitir bypass.")

if __name__ == "__main__":
    asyncio.run(test_member_verification()) 