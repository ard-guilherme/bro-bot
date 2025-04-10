"""
Ponto de entrada principal para o GYM NATION Bot.
"""
import logging
import asyncio
import sys
import os
import httpx

# Adiciona o diretório raiz ao path para permitir imports relativos
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler
)
from telegram import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeDefault, BotCommandScopeAllChatAdministrators, Update
from telegram.request import HTTPXRequest

from src.utils.config import Config
from src.utils.filters import CustomFilters
from src.utils.mongodb_instance import mongodb_client, initialize_mongodb
from src.utils.anthropic_client import AnthropicClient
from src.bot.handlers import (
    start_command,
    help_command,
    motivation_command,
    presentation_command,
    macros_command,
    welcome_new_member,
    error_handler,
    setadmin_command,
    deladmin_command,
    listadmins_command,
    monitor_command,
    unmonitor_command,
    handle_monitored_message,
    fecho_command,
    say_command,
    sayrecurrent_command,
    listrecurrent_command,
    delrecurrent_command,
    rules_command
)
from src.bot.checkin_handlers import (
    checkin_command,
    checkinplus_command,
    endcheckin_command,
    handle_checkin_response,
    checkinscore_command,
    confirmcheckin_command
)
from src.bot.mention_handlers import (
    handle_mention,
    handle_qa_feedback
)
from src.bot.blacklist_handlers import (
    addblacklist_command,
    blacklist_command,
    rmblacklist_command,
    blacklist_button
)

# Configuração de logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

async def setup_commands(application: Application) -> None:
    """Configura os comandos do bot para aparecerem no menu de comandos do Telegram."""
    commands = [
        BotCommand("start", "Inicia o bot"),
        BotCommand("help", "Mostra a mensagem de ajuda"),
        BotCommand("motivacao", "Envia uma mensagem de motivação fitness"),
        BotCommand("fecho", "Envia uma tirada sarcástica e debochada com humor"),
        BotCommand("apresentacao", "Responde com uma apresentação personalizada"),
        BotCommand("macros", "Calcula macronutrientes de uma receita ou alimento"),
        BotCommand("checkinscore", "Mostra o ranking de check-ins dos usuários"),
        BotCommand("regras", "Mostra as regras do grupo GYM NATION")
    ]
    
    # Comandos apenas para administradores
    admin_commands = commands + [
        BotCommand("checkin", "Define uma mensagem como âncora de check-in (normal)"),
        BotCommand("checkinplus", "Define uma mensagem como âncora de check-in (PLUS x2)"),
        BotCommand("endcheckin", "Desativa o check-in atual"),
        BotCommand("confirmcheckin", "Confirma manualmente o check-in de um usuário"),
        BotCommand("addblacklist", "Adiciona uma mensagem à blacklist"),
        BotCommand("blacklist", "Lista mensagens na blacklist do chat"),
        BotCommand("rmblacklist", "Remove uma mensagem da blacklist pelo ID")
    ]
    
    # Comandos apenas para o proprietário
    owner_commands = admin_commands + [
        BotCommand("setadmin", "Adiciona um usuário como administrador do bot"),
        BotCommand("deladmin", "Remove um usuário da lista de administradores do bot"),
        BotCommand("listadmins", "Lista todos os administradores do bot")
    ]
    
    # Configura comandos para chats privados (proprietário)
    await application.bot.set_my_commands(owner_commands, scope=BotCommandScopeDefault())
    
    # Configura comandos apenas para administradores nos grupos
    await application.bot.set_my_commands(admin_commands, scope=BotCommandScopeAllChatAdministrators())
    
    # Remove comandos para membros comuns nos grupos
    await application.bot.delete_my_commands(scope=BotCommandScopeAllGroupChats())
    
    logger.info("Comandos do bot configurados com sucesso: visíveis em chats privados e apenas para administradores nos grupos")

async def main_async():
    """Função principal assíncrona para iniciar o bot."""
    # Inicializa a conexão com o MongoDB
    try:
        logger.info("Conectando ao MongoDB...")
        await initialize_mongodb()
        logger.info("Conexão com o MongoDB estabelecida com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao conectar ao MongoDB: {e}")
        logger.warning("O bot será iniciado sem conexão com o MongoDB. Alguns recursos podem não funcionar corretamente.")
    
    # Obtém o token da API do Telegram
    token = Config.get_token()
    
    # Criação da aplicação com configurações melhoradas para estabilidade
    # Configurações ajustadas para melhorar a estabilidade em conexões instáveis
    # Aumenta o timeout de conexão e adiciona retries automáticos
    # Define um sistema de retry para inicialização do bot
    max_retries = 5
    initial_retry_delay = 2  # segundos
    
    # Tenta inicializar o bot com retries
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Tentativa {attempt}/{max_retries} de inicializar o bot...")
            
            # Configura HTTPX com retries para problemas temporários de rede
            # Define a política de retry para o cliente HTTPX que é usado pelo python-telegram-bot
            # Cria o request personalizado para o python-telegram-bot com configurações compatíveis
            request = HTTPXRequest(
                connection_pool_size=8,  # Aumenta o tamanho do pool de conexões
                connect_timeout=20.0,  # Timeout de conexão em segundos
                read_timeout=20.0,  # Timeout de leitura em segundos
                write_timeout=20.0  # Timeout de escrita em segundos
            )
            
            # Cria a aplicação com timeout ajustado e o request personalizado
            application = Application.builder().token(token).request(request).build()
            
            # Instanciar e armazenar o cliente Anthropic no bot_data
            try:
                anthropic_api_key = Config.get_anthropic_api_key()
                if anthropic_api_key:
                    anthropic_client_instance = AnthropicClient(api_key=anthropic_api_key)
                    application.bot_data["anthropic_client"] = anthropic_client_instance
                    logger.info("Cliente Anthropic inicializado e armazenado em bot_data.")
                else:
                    logger.warning("Chave API da Anthropic não configurada. Funcionalidades LLM estarão desativadas.")
            except Exception as e:
                logger.error(f"Erro ao inicializar o cliente Anthropic: {e}")
            
            # Cria o filtro de proprietário
            owner_filter = CustomFilters.owner_filter()
            only_owner_filter = CustomFilters.only_owner_filter()
            
            # Adiciona handlers para comandos (apenas para o proprietário)
            application.add_handler(CommandHandler("start", start_command, filters=owner_filter))
            application.add_handler(CommandHandler("help", help_command, filters=owner_filter))
            application.add_handler(CommandHandler("motivacao", motivation_command, filters=owner_filter))
            application.add_handler(CommandHandler("fecho", fecho_command, filters=owner_filter))
            application.add_handler(CommandHandler("apresentacao", presentation_command, filters=owner_filter))
            application.add_handler(CommandHandler("macros", macros_command, filters=owner_filter))
            application.add_handler(CommandHandler("say", say_command, filters=owner_filter))
            application.add_handler(CommandHandler("sayrecurrent", sayrecurrent_command, filters=owner_filter))
            application.add_handler(CommandHandler("listrecurrent", listrecurrent_command, filters=owner_filter))
            application.add_handler(CommandHandler("delrecurrent", delrecurrent_command, filters=owner_filter))
            application.add_handler(CommandHandler("regras", rules_command, filters=owner_filter))
            
            # Adiciona handlers para comandos de check-in (apenas para o proprietário)
            application.add_handler(CommandHandler("checkin", checkin_command, filters=owner_filter))
            application.add_handler(CommandHandler("checkinplus", checkinplus_command, filters=owner_filter))
            application.add_handler(CommandHandler("endcheckin", endcheckin_command, filters=owner_filter))
            application.add_handler(CommandHandler("checkinscore", checkinscore_command, filters=owner_filter))
            application.add_handler(CommandHandler("confirmcheckin", confirmcheckin_command, filters=owner_filter))
            
            # Adiciona handlers para comandos de blacklist (apenas para o proprietário)
            application.add_handler(CommandHandler("addblacklist", addblacklist_command, filters=owner_filter))
            application.add_handler(CommandHandler("blacklist", blacklist_command, filters=owner_filter))
            application.add_handler(CommandHandler("rmblacklist", rmblacklist_command, filters=owner_filter))
            
            # Adiciona handler para os botões da blacklist
            application.add_handler(CallbackQueryHandler(
                blacklist_button,
                pattern=r'^rmblacklist_'
            ))
            
            # Adiciona handlers para comandos de administração (apenas para o proprietário do bot)
            application.add_handler(CommandHandler("setadmin", setadmin_command, filters=only_owner_filter))
            application.add_handler(CommandHandler("deladmin", deladmin_command, filters=only_owner_filter))
            application.add_handler(CommandHandler("listadmins", listadmins_command, filters=only_owner_filter))
            
            # Adiciona handlers para monitoramento de mensagens (apenas para o proprietário do bot)
            application.add_handler(CommandHandler("monitor", monitor_command, filters=only_owner_filter))
            application.add_handler(CommandHandler("unmonitor", unmonitor_command, filters=only_owner_filter))
            
            # Adiciona handler para menções ao bot (sem restrição de usuário)
            application.add_handler(MessageHandler(
                (filters.TEXT & ~filters.COMMAND & (filters.Entity("mention") | filters.REPLY)),
                handle_mention
            ))
            
            # Adiciona handler para processamento de feedback de Q&A
            application.add_handler(CallbackQueryHandler(
                handle_qa_feedback,
                pattern=r'^qa_'
            ))
            
            # Adiciona handler para processar todas as mensagens (para check-ins) (apenas para o proprietário)
            # Importante: este handler deve ser adicionado por último para não interferir com outros handlers
            application.add_handler(
                MessageHandler(
                    # Filtro para capturar NOVAS mensagens com mídias (fotos, vídeos, animações, documentos) 
                    # que são respostas, não são comandos, e vêm do proprietário (se owner_filter ativo).
                    filters.UpdateType.MESSAGE # Garante que é uma nova mensagem
                    & (filters.PHOTO | filters.VIDEO | filters.ANIMATION | filters.Document.ALL)
                    & filters.REPLY
                    & ~filters.COMMAND
                    & owner_filter,
                    handle_checkin_response
                )
            )
            
            # Adiciona handler para monitorar mensagens de texto
            application.add_handler(
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & owner_filter,
                    handle_monitored_message
                )
            )
            
            # Adiciona handler para mensagens não autorizadas
            application.add_handler(
                MessageHandler(~owner_filter, unauthorized_message_handler)
            )
            
            # Adiciona handler para erros
            application.add_error_handler(error_handler)
            
            # Configura os comandos do bot para aparecerem no menu
            # Configuramos os comandos diretamente em vez de usar post_init
            logger.info("Iniciando o GYM NATION Bot...")
            
            # Inicializa o gerenciador de mensagens recorrentes
            from src.utils.recurring_messages_manager import initialize_recurring_messages_manager
            recurring_messages_manager = initialize_recurring_messages_manager(application)
            await recurring_messages_manager.start()
            
            # Inicia o polling
            try:
                # Define um timeout para a inicialização
                init_task = asyncio.create_task(application.initialize())
                await asyncio.wait_for(init_task, timeout=15.0)  # 15 segundos de timeout para inicialização
                
                # Configura os comandos
                await setup_commands(application)
                
                # Inicia o bot com timeout
                start_task = asyncio.create_task(application.start())
                await asyncio.wait_for(start_task, timeout=15.0)  # 15 segundos de timeout para start
                
                # Inicia o polling com timeout e opções de reconnect
                polling_task = asyncio.create_task(
                    application.updater.start_polling(
                        poll_interval=2.0,  # Intervalo de polling de 2 segundos (mais suave para a API)
                        timeout=10.0,  # Timeout de 10 segundos para requests de polling
                        bootstrap_retries=5,  # Número de retries para bootstrap
                        read_timeout=7.0,  # Timeout de leitura (mais longo)
                        write_timeout=7.0  # Timeout de escrita (mais longo)
                    )
                )
                await asyncio.wait_for(polling_task, timeout=20.0)  # 20 segundos de timeout para polling
                
                logger.info("Bot inicializado com sucesso!")
                
                # Inicialização bem-sucedida, sai do loop de retry
                break
                
            except asyncio.TimeoutError:
                logger.error(f"Timeout durante a inicialização do bot na tentativa {attempt}/{max_retries}")
                # Tenta limpar recursos antes de tentar novamente
                try:
                    await application.stop()
                except Exception as cleanup_error:
                    logger.error(f"Erro ao limpar recursos após timeout: {cleanup_error}")
                # Continua para a próxima tentativa
        
        except Exception as e:
            logger.error(f"Erro ao inicializar o bot na tentativa {attempt}/{max_retries}: {e}")
            
            # Se não for a última tentativa, aguarda e tenta novamente
            if attempt < max_retries:
                retry_delay = initial_retry_delay * (2 ** (attempt - 1))  # Backoff exponencial
                logger.info(f"Aguardando {retry_delay} segundos antes de tentar novamente...")
                await asyncio.sleep(retry_delay)
            else:
                logger.critical(f"Falha ao inicializar o bot após {max_retries} tentativas.")
                raise  # Re-levanta a exceção para encerrar o programa
    
    # Mantém o bot rodando até ser interrompido
    try:
        # Aguarda indefinidamente
        await asyncio.Event().wait()
    finally:
        # Encerra o bot quando for interrompido
        await application.stop()

def main() -> None:
    """Função principal para iniciar o bot."""
    asyncio.run(main_async())

async def unauthorized_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para mensagens de usuários não autorizados.
    Simplesmente ignora a mensagem sem responder.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    logger.warning(
        f"Mensagem não autorizada ignorada. "
        f"Usuário: {user_id}, Chat: {chat_id}, Tipo de chat: {chat_type}"
    )
    # Não responde à mensagem para não revelar que o bot está ativo
    
if __name__ == "__main__":
    main() 