"""
Handlers para os comandos de check-in.
"""
import logging
from typing import Optional, Dict, Any
from telegram import Update, ReactionTypeEmoji
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.error import TimedOut
from src.utils.mongodb_instance import mongodb_client
from src.bot.handlers import is_admin, send_temporary_message, delete_message_after
import asyncio
from datetime import datetime, timedelta
import random # Importa o módulo random

# Configuração de logging
logger = logging.getLogger(__name__)

async def checkin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /checkin (pontuação padrão = 1).
    Define uma mensagem como âncora de check-in.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    await set_anchor(update, context, points_value=1)

async def checkinplus_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /checkinplus (pontuação dobrada = 2).
    Define uma mensagem como âncora de check-in especial.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    await set_anchor(update, context, points_value=2)

async def set_anchor(update: Update, context: ContextTypes.DEFAULT_TYPE, points_value: int) -> None:
    """
    Lógica comum para definir uma mensagem como âncora de check-in com pontuação específica.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
        points_value (int): Valor da pontuação associada à âncora.
    """
    # Verifica se o usuário é administrador
    if not await is_admin(update, context):
        await send_temporary_message(
            update, 
            context, 
            "Apenas proprietário e administradores podem usar este comando."
        )
        return
    
    # Verifica se o comando foi usado como resposta a outra mensagem
    if not update.message.reply_to_message:
        await send_temporary_message(
            update, 
            context, 
            "Por favor, use este comando respondendo à mensagem que deseja definir como âncora de check-in."
        )
        return
    
    # Obtém os IDs do chat e da mensagem
    chat_id = update.effective_chat.id
    message_id = update.message.reply_to_message.message_id
    
    # Define a mensagem como âncora de check-in com a pontuação especificada
    success = await mongodb_client.set_checkin_anchor(chat_id, message_id, points_value)
    
    if success:
        # Tenta deletar a mensagem de comando
        try:
            await update.message.delete()
        except Exception as e:
            logger.error(f"Erro ao deletar mensagem de comando /checkin ou /checkinplus: {e}")
        
        # Envia mensagem de confirmação
        confirmation_text = (
            f"✅ Check-in PLUS ativado (pontos x{points_value})! Membros podem responder à mensagem marcada para registrar." 
            if points_value > 1 
            else "✅ Check-in padrão ativado! Membros podem responder à mensagem marcada para registrar."
        )
        await context.bot.send_message(
            chat_id=chat_id,
            text=confirmation_text,
            reply_to_message_id=message_id
        )
    else:
        await send_temporary_message(
            update, 
            context, 
            f"❌ Erro ao ativar o check-in (pontos x{points_value}). Por favor, tente novamente."
        )

async def endcheckin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /endcheckin.
    Desativa o check-in atual.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    # Verifica se o usuário é administrador
    if not await is_admin(update, context):
        await send_temporary_message(
            update, 
            context, 
            "Apenas proprietário e administradores podem usar este comando."
        )
        return
    
    # Obtém o ID do chat
    chat_id = update.effective_chat.id
    
    # Obtém o check-in ativo antes de desativá-lo
    active_checkin = await mongodb_client.get_active_checkin(chat_id)
    
    if not active_checkin:
        await send_temporary_message(
            update, 
            context, 
            "Não há check-in ativo para desativar."
        )
        return
    
    # Obtém a contagem de check-ins (número de participações) para a âncora ativa
    anchor_id = active_checkin["_id"]
    checkin_count = await mongodb_client.get_anchor_checkin_count(chat_id, anchor_id)
    points_value = active_checkin.get("points_value", 1)
    anchor_type = "PLUS" if points_value > 1 else "padrão"
    
    # Desativa o check-in atual
    success = await mongodb_client.end_checkin(chat_id)
    
    if success:
        # Tenta deletar a mensagem de comando
        try:
            await update.message.delete()
        except Exception as e:
            logger.error(f"Erro ao deletar mensagem de comando: {e}")
        
        # Envia mensagem de confirmação com a contagem de check-ins
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ Check-in {anchor_type} finalizado! Foram registrados {checkin_count} check-ins."
        )
    else:
        await send_temporary_message(
            update, 
            context, 
            "❌ Erro ao desativar o check-in. Por favor, tente novamente."
        )

async def handle_checkin_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para respostas a mensagens de check-in (com mídia).
    Processa check-ins normais e PLUS, calcula pontos e gera respostas.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    # Se a mensagem não for uma resposta, retorna
    if not update.message.reply_to_message:
        return
    
    # Verifica se a mensagem contém mídia (foto, vídeo, GIF, etc.)
    if not (update.message.photo or update.message.video or 
            update.message.animation or 
            (update.message.document and update.message.document.mime_type and 
             update.message.document.mime_type.startswith('image/'))):
        logger.debug(f"Mensagem de check-in sem mídia ignorada: {update.message.message_id}")
        return
    
    # Obtém o chat_id e o replied_message_id
    chat_id = update.effective_chat.id
    replied_message_id = update.message.reply_to_message.message_id
    
    # Obtém o check-in ativo
    active_checkin = await mongodb_client.get_active_checkin(chat_id)
    
    # Se não houver check-in ativo ou a resposta não for para a âncora, retorna
    if not active_checkin or active_checkin["message_id"] != replied_message_id:
        # Log a razão específica
        if not active_checkin:
            logger.debug(f"Ignorando resposta {update.message.message_id}: Nenhum check-in ativo no chat {chat_id}")
        else:
            logger.debug(f"Ignorando resposta {update.message.message_id}: Não é para a âncora ativa {active_checkin['message_id']}. Respondeu a {replied_message_id}")
        return
    
    logger.info(f"Check-in (resposta c/ mídia) detectado de {update.effective_user.full_name} ({update.effective_user.id}) no chat {chat_id} para âncora {active_checkin['_id']}")
    
    # Obtém informações do usuário
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name or "Usuário"
    username = update.effective_user.username  # Captura o username
    user_message_text = update.message.text or update.message.caption # Pega texto da mensagem ou legenda da mídia
    
    # Tenta registrar o check-in do usuário para esta âncora
    # Retorna o NOVO SCORE TOTAL do usuário se sucesso, None se já fez check-in para esta âncora
    new_total_score = await mongodb_client.record_user_checkin(chat_id, user_id, user_name, username)
    
    # Se o usuário já fez check-in para esta âncora específica, envia aviso e retorna
    if new_total_score is None:
        logger.debug(f"Usuário {user_id} já fez check-in para esta âncora {active_checkin['_id']}")
        display_name = f"@{username}" if username else user_name
        await send_temporary_message(
            update, 
            context, 
            f"Ei {display_name}, já contabilizamos seu check-in hoje 😉"
        )
        return
    
    # Check-in registrado com sucesso!
    logger.info(f"Check-in registrado com sucesso para {user_id}. Novo score total: {new_total_score}")
    
    # Determina a reação e prepara a mensagem de resposta
    points_value = active_checkin.get("points_value", 1)
    is_plus_checkin = points_value > 1
    llm_response_text = None
    reaction = "🔥" # Reação padrão
    
    # Obter cliente Anthropic do contexto
    anthropic_client = context.bot_data.get("anthropic_client")
    
    if is_plus_checkin:
        reaction = "🔥" # Reação para check-in plus (Testando com polegar)
        # Tenta gerar resposta da LLM se houver texto e o cliente existir
        if user_message_text and anthropic_client:
            try:
                # Passa o texto da mensagem do usuário para a LLM
                llm_response_text = await anthropic_client.generate_checkin_response(user_message_text, user_name)
                if not llm_response_text:
                    logger.warning(f"LLM não retornou resposta para check-in plus de {user_id}")
            except Exception as e:
                logger.error(f"Erro ao gerar resposta da LLM para check-in plus: {e}")
                # Continua sem a resposta da LLM em caso de erro
        elif user_message_text and not anthropic_client:
            logger.warning("Cliente Anthropic não encontrado no bot_data. Não é possível gerar resposta LLM para check-in plus.")

    # Adiciona a reação apropriada
    try:
        # Garante que a reação é uma string válida antes de enviar
        if reaction not in ["🔥"]:
            logger.error(f"Tentativa de usar reação inválida: {reaction}. Usando padrão 🔥.")
            reaction = "🔥"
            
        # Cria o objeto ReactionTypeEmoji explicitamente
        reaction_object = ReactionTypeEmoji(emoji=reaction)
        
        logger.debug(f"Tentando definir reação '{reaction}' (como objeto ReactionTypeEmoji) para mensagem {update.message.message_id} no chat {chat_id}")
        await context.bot.set_message_reaction(
            chat_id=chat_id,
            message_id=update.message.message_id,
            reaction=[reaction_object] # Passando o objeto explícito
        )
    except Exception as e:
        logger.error(f"Erro ao adicionar reação {reaction} à mensagem {update.message.message_id}: {e}")
    
    # Monta a mensagem de resposta final
    display_name = f"@{username}" if username else user_name
    base_response = f"Check-in {'PLUS' if is_plus_checkin else ''} confirmado, {display_name}! {reaction}" 
    score_info = f"Você tem <b>{new_total_score}</b> pontos no total!"
    
    # Adiciona a resposta da LLM se for check-in plus e a resposta foi gerada
    if is_plus_checkin and llm_response_text:
        final_response = f"{llm_response_text}\n\n{base_response} {score_info}"
    else:
        # Para check-in normal ou plus sem texto/erro LLM, usa a resposta padrão antiga (mas com score)
        # A função generate_checkin_response_static é a antiga generate_checkin_response renomeada
        static_part = generate_checkin_response_static(display_name, new_total_score) # Usa o score atualizado
        # Extrai a parte inicial da mensagem estática (antes da pontuação)
        static_base = static_part.split("Você tem")[0].strip()
        final_response = f"{static_base}"
        
    # Responde ao usuário com a mensagem final
    await update.message.reply_text(final_response, parse_mode=ParseMode.HTML)

async def checkinscore_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /checkinscore.
    Envia um scoreboard com os scores de check-ins dos usuários, agrupado por pontuação e com estatísticas.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    # Determina o chat para o qual exibir o scoreboard
    chat_id = update.effective_chat.id
    chat_title = "Check-ins"
    
    # Verifica se um nome de grupo foi fornecido como argumento
    if context.args and len(context.args) > 0:
        target_group_name = ' '.join(context.args)
        target_chat_info = await mongodb_client.get_chat_info_by_title(target_group_name)
        
        if target_chat_info:
            chat_id = target_chat_info["chat_id"]
            # Usa o título encontrado no DB para o cabeçalho
            chat_title = target_chat_info.get("title", target_group_name) 
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Não foi possível encontrar informações do grupo '{target_group_name}'. Verifique o nome ou se o bot está no grupo."
            )
            return
    elif update.effective_chat.type != "private":
        # Se for em grupo, usa o título do grupo atual
        chat_title = update.effective_chat.title
    else:
        # Se for privado sem args, não podemos mostrar scoreboard
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Use /checkinscore <nome_do_grupo> para ver o placar de um grupo específico."
        )
        return

    # Tenta deletar a mensagem de comando
    try:
        await update.message.delete()
    except Exception as e:
        logger.error(f"Erro ao deletar mensagem de comando /checkinscore: {e}")
    
    # --- Obtenção e Processamento dos Dados ---
    
    # 1. Obtém o scoreboard de check-ins (ordenado por score)
    scoreboard_data = await mongodb_client.get_checkin_scoreboard(chat_id)
    
    if not scoreboard_data or len(scoreboard_data) == 0:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Ainda não há check-ins registrados {f'no grupo {chat_title}' if chat_title else 'neste chat'}. 😢"
        )
        return
        
    # 2. Busca estatísticas adicionais
    total_participants = await mongodb_client.get_total_checkin_participants(chat_id)
    first_checkin_date_obj = await mongodb_client.get_first_checkin_date(chat_id)
    
    # Calcula há quantos dias foi o primeiro check-in
    days_since_first = "N/A"
    if first_checkin_date_obj:
        # Garante que ambos são offset-naive ou offset-aware antes de subtrair
        now_naive = datetime.now() 
        if first_checkin_date_obj.tzinfo:
             first_checkin_naive = first_checkin_date_obj.replace(tzinfo=None)
        else:
             first_checkin_naive = first_checkin_date_obj
        
        delta = now_naive - first_checkin_naive
        days_since_first = f"{delta.days} dias atrás" if delta.days > 0 else ("Hoje" if delta.days == 0 else "Data futura?")
    
    # 3. Calcula o total de pontos do grupo
    total_group_score = sum(entry.get("score", 0) for entry in scoreboard_data)

    # 4. Agrupa usuários por score
    grouped_scores = {}
    for entry in scoreboard_data:
        score = entry.get("score", 0)
        if score not in grouped_scores:
            grouped_scores[score] = []
        # Armazena nome e username para exibição
        user_info = {
            "name": entry.get("user_name", f"User {entry['user_id']}"),
            "username": entry.get("username")
        }
        grouped_scores[score].append(user_info)
        
    # --- Montagem da Mensagem --- 
    
    scoreboard_lines = []
    # Adiciona título
    scoreboard_lines.append(f"🏆 <b>{chat_title.upper()} CHECK-INS</b> 🏆\n") 
    
    rank_icons = {1: "🥇", 2: "🥈", 3: "🥉"}
    current_rank_pos = 0 # Posição no ranking (1, 2, 3...)
    processed_users_count = 0 # Conta usuários já exibidos
    max_users_to_show = 20 # Limite de usuários para exibir

    # Itera sobre os scores únicos ordenados
    for score_value in sorted(grouped_scores.keys(), reverse=True):
        if processed_users_count >= max_users_to_show:
            break # Sai se já exibiu o máximo de usuários
            
        users_at_this_score = grouped_scores[score_value]
        current_rank_pos += 1
        
        rank_display = rank_icons.get(current_rank_pos, f"🔹 {current_rank_pos}.")
        plural = "s" if score_value != 1 else ""
        
        # Linha do Rank e Pontuação
        scoreboard_lines.append(f"{rank_display} (<b>{score_value}</b> check-in{plural})")
        
        # Lista usuários neste rank
        for user_info in users_at_this_score:
            if processed_users_count >= max_users_to_show:
                scoreboard_lines.append("   ...") # Indica que há mais usuários não listados
                break # Sai do loop interno também
                
            # Formata nome/username
            name = user_info['name']
            username = user_info['username']
            # Limita o tamanho do nome para evitar quebra de linha (ajuste conforme necessário)
            max_name_len = 25 
            display_name = f"@{username}" if username else name
            if len(display_name) > max_name_len:
                display_name = display_name[:max_name_len-1] + "…"
                
            scoreboard_lines.append(f"   👤 {display_name}")
            processed_users_count += 1
            
        if processed_users_count >= max_users_to_show and current_rank_pos < len(grouped_scores):
             if not scoreboard_lines[-1].strip().endswith("..."):
                  scoreboard_lines.append("   ...") # Garante que o ... apareça se cortou no meio de um rank
             break # Sai do loop externo se atingiu o limite

        scoreboard_lines.append("") # Linha em branco entre os ranks

    # Remove a última linha em branco se existir
    if scoreboard_lines and scoreboard_lines[-1] == "":
        scoreboard_lines.pop()
        
    # Adiciona linha motivacional
    scoreboard_lines.append("\n💪 Continue mantendo a consistência! 🔥")
    
    # Adiciona seção de estatísticas
    scoreboard_lines.append("\n📊 <b>Estatísticas:</b>")
    scoreboard_lines.append(f"• {total_participants} pessoas já participaram")
    plural_stats = "s" if total_group_score != 1 else ""
    scoreboard_lines.append(f"• {total_group_score} check-in{plural_stats} no total")
    scoreboard_lines.append(f"• Primeiro check-in: {days_since_first}")

    # Junta tudo em uma única string
    scoreboard_message = "\n".join(scoreboard_lines)

    # --- Envio da Mensagem --- 
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=scoreboard_message, 
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True # Evita preview de links em usernames
        )
    except TimedOut:
        logger.warning(f"Timeout ao enviar scoreboard para o chat {chat_id}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="Ocorreu um timeout ao gerar o placar. Tente novamente mais tarde.",
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Erro ao enviar scoreboard para chat {chat_id}: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="Ocorreu um erro ao gerar o placar. Tente novamente mais tarde.",
            disable_web_page_preview=True
        )

# --- Novas Listas de Respostas por Faixa ---

responses_1_3 = [
    "Bem-vindo à jornada, {user_name}! Seu primeiro check-in é o início de algo grande! 💪",
    "É isso aí, {user_name}! O primeiro passo foi dado. Bora construir esse shape! 🔥",
    "Check-in na área, {user_name}! Feliz em te ver começando com a gente! ✨",
    "Boa, {user_name}! Que este seja o primeiro de muitos check-ins! 🚀",
    "Começou com o pé direito, {user_name}! Check-in registrado! ✅",
    "Aí sim, {user_name}! Pontapé inicial dado. Estamos juntos nessa! 🤝",
    "Primeiro check-in? Show, {user_name}! A disciplina começa agora! 💯",
    "Mandou bem, {user_name}! Check-in confirmado. O caminho é esse! 👉",
    "Que legal te ver por aqui, {user_name}! Primeiro check-in feito! 🎉",
    "Registro feito, {user_name}! Continue assim e os resultados virão! 😉",
]

responses_4_7 = [
    "Olha só, {user_name} pegando o ritmo! Check-in firme! 🔥",
    "Já tá virando rotina, {user_name}? Boa! Check-in na conta! 💪",
    "A consistência tá começando a aparecer, {user_name}! Check-in! ✨",
    "Mandou bem de novo, {user_name}! Continue assim! ✅",
    "Check-in registrado! {user_name} mostrando que veio pra ficar! 😎",
    "É isso, {user_name}! Engrenou na jornada! Check-in! 🚀",
    "Não tá pra brincadeira! Boa, {user_name}! Check-in feito! 👍",
    "Mais um pra conta, {user_name}! O shape agradece! 😉",
    "A cada check-in, mais perto do objetivo! Dale, {user_name}! 🎯",
    "Foco total, {user_name}! Check-in confirmado! 💯",
]

responses_8_15 = [
    "Presença confirmada! {user_name} não falha! Check-in! 🔑",
    "Isso que é frequência, {user_name}! Check-in pra conta! 😎",
    "Já é parte da mobília da academia! Boa, {user_name}! Check-in! 😂",
    "A regularidade é a chave, {user_name}! Check-in! 💯",
    "Mais um dia, mais um check-in! {user_name} no comando! 💪",
    "Firme e forte, {user_name}! Check-in com sucesso! ✅",
    "O sofá tá sentindo sua falta, {user_name}! Check-in! 😉",
    "Que orgulho ver essa dedicação, {user_name}! Check-in! ✨",
    "Exemplo de constância! Parabéns, {user_name}! Check-in! 👏",
    "{user_name} on fire! 🔥 Check-in registrado!",
]

responses_16_25 = [
    "Disciplina em pessoa! Aí sim, {user_name}! Check-in! 👊",
    "Isso já é hábito, {user_name}! Mandou bem demais! Check-in! 💥",
    "Comprovando a cada dia! Que disciplina, {user_name}! Check-in! ✨",
    "Você inspira, {user_name}! Check-in nível disciplina máxima! ✈️",
    "Já virou estilo de vida pra {user_name}! Check-in monstro! 🏆",
    "O resultado tá vindo! Foco admirável, {user_name}! Check-in! 💪",
    "Check-in feito! {user_name}, sua dedicação é notável! 💯",
    "Nada abala {user_name}! Check-in com raça! ✅",
    "A meta tá cada vez mais perto! Boa, {user_name}! Check-in! 🎯",
    "Que performance, {user_name}! Check-in registrado! 🔥",
]

responses_26_40 = [
    "Veterano {user_name} na área! Respeito máximo! Check-in! 🏛️",
    "Experiência e constância! {user_name} é referência! Check-in! 🔥",
    "Tá pegando fogo, {user_name}! Nível veterano ativado! Check-in! 🚒",
    "Não é pra qualquer um! {user_name} mostrando como se faz! Check-in! 🦾",
    "Até o espelho aplaude, {user_name}! Dedicação de veterano! Check-in! 👏",
    "Check-in nível PRO! Boa, {user_name}! Continua inspirando! ✨",
    "A GYM NATION se orgulha de você, {user_name}! Check-in! 💪",
    "Essa jornada é longa, e {user_name} tá trilhando como mestre! Check-in! 🏆",
    "Check-in de quem sabe o caminho! Dale, {user_name}! ✅",
    "{user_name}, a personificação da disciplina! Check-in! 💯",
]

responses_41_60 = [
    "MONSTRO! {user_name} não treina, distribui motivação! Check-in! 💪🔥",
    "Nível absurdo! {user_name}, você é imparável! Check-in! 💥",
    "Isso não é suor, é poder escorrendo! Check-in MONSTRO, {user_name}! ✨⚡️",
    "Se check-in fosse campeonato, {user_name} já era campeão invicto! Check-in! 🏆🥇",
    "A gravidade te respeita, {user_name}! Check-in nível Saiyajin! 🔥",
    "Que máquina! {user_name}, sua dedicação é sobrenatural! Check-in! 🦾",
    "Check-in brutal! {user_name}, você redefine limites! 🚀",
    "O shape do {user_name} tá trincando até a tela do celular! Check-in!📱💥",
    "Alguém avisa a NASA que achamos uma nova força da natureza: {user_name}! Check-in! ☄️",
    "Check-in nível DEUS GREGO! Boa, {user_name}! 🏛️💪",
]

responses_61_plus = [
    "LENDA! {user_name}, seu nome será cantado pelos poetas da maromba! Check-in! 📜💪",
    "Mais de 60?! {user_name}, você não fez check-in, você transcendeu! Check-in LENDÁRIO! ✨👑",
    "O Olimpo está te convocando, {user_name}! Check-in nível DIVINDADE! ⚡️🏛️",
    "Hall da Fama é pouco! {user_name} merece uma constelação! Check-in ESTELAR! 🌌🗿",
    "Check-in registrado! {user_name}, sua disciplina é um MITO! Mufasa curtiu isso! 🦁🔥",
    "O cara não posta check-in, ele deixa rastro de motivação e testosterona no grupo! LENDA, {user_name}! 💪🚀",
    "Check-in nível Thor descendo o martelo! {user_name}, você é ÉPICO! 🔨⚡️",
    "Seus check-ins deveriam vir com aviso de impacto sísmico! Que poder, {user_name}! Check-in! 🌍💥",
    "{user_name}, você não segue o plano, você É o plano! Check-in MAGISTRAL! 👑✨",
    "Imparável, Imbatível, Inigualável! {user_name} é LENDA! Check-in! 🥇🏆🔥",
]

def generate_checkin_response_static(user_name: str, checkin_count: int) -> str:
    """
    Gera uma mensagem de resposta ESTÁTICA e ALEATÓRIA para check-in, baseada na faixa de score total.
    (Renomeada da antiga generate_checkin_response para clareza).
    NOTA: checkin_count aqui é o SCORE TOTAL atual do usuário.
    """
    # Garante que checkin_count é um inteiro >= 0
    safe_checkin_count = max(0, int(checkin_count))

    chosen_response = ""

    # Seleciona a lista apropriada e escolhe uma resposta aleatoriamente
    if 1 <= safe_checkin_count <= 3:
        chosen_response = random.choice(responses_1_3).format(user_name=user_name)
    elif 4 <= safe_checkin_count <= 7:
        chosen_response = random.choice(responses_4_7).format(user_name=user_name)
    elif 8 <= safe_checkin_count <= 15:
        chosen_response = random.choice(responses_8_15).format(user_name=user_name)
    elif 16 <= safe_checkin_count <= 25:
        chosen_response = random.choice(responses_16_25).format(user_name=user_name)
    elif 26 <= safe_checkin_count <= 40:
        chosen_response = random.choice(responses_26_40).format(user_name=user_name)
    elif 41 <= safe_checkin_count <= 60:
        chosen_response = random.choice(responses_41_60).format(user_name=user_name)
    elif safe_checkin_count >= 61:
        chosen_response = random.choice(responses_61_plus).format(user_name=user_name)
    else: # Fallback para score 0 (ou caso inesperado)
        # Usa uma mensagem de boas-vindas padrão
        chosen_response = f"Bem-vindo à jornada, {user_name}! Check-in registrado! 💪"

    # Adiciona a contagem de pontos no final
    # Remove a antiga lógica de seleção baseada em módulo
    # chosen_response = responses[safe_checkin_count % len(responses)]
    # return f"{chosen_response}\nSeu score total é <b>{checkin_count}</b>!"
    return f"{chosen_response}\nSeu score total é <b>{safe_checkin_count}</b>!"

async def confirmcheckin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /confirmcheckin.
    Confirma manualmente o check-in de um usuário na âncora ativa.
    
    Args:
        update (Update): Objeto de atualização do Telegram.
        context (ContextTypes.DEFAULT_TYPE): Contexto do callback.
    """
    # Verifica se o usuário é administrador
    if not await is_admin(update, context):
        await send_temporary_message(
            update, 
            context, 
            "Apenas proprietário e administradores podem usar este comando."
        )
        return

    chat_id = update.effective_chat.id
    target_user_id = None
    target_user_name = "Usuário"
    target_username = None

    # Verifica se o comando foi usado em resposta a uma mensagem
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        target_user_id = target_user.id
        target_user_name = target_user.full_name
        target_username = target_user.username
    # Verifica se um ID de usuário foi fornecido como argumento
    elif context.args and len(context.args) >= 1 and context.args[0].isdigit():
        target_user_id = int(context.args[0])
        # Tenta obter informações do usuário pelo ID (pode falhar se o bot não viu o usuário recentemente)
        try:
            member = await context.bot.get_chat_member(chat_id, target_user_id)
            target_user_name = member.user.full_name
            target_username = member.user.username
        except Exception as e:
            logger.warning(f"Não foi possível obter info para user_id {target_user_id} em confirmcheckin: {e}")
            target_user_name = f"Usuário {target_user_id}" # Usa ID se nome não encontrado
    else:
        await send_temporary_message(
            update,
            context,
            "Use /confirmcheckin respondendo a uma mensagem do usuário ou com o ID do usuário. Ex: /confirmcheckin 123456789"
        )
        return

    if target_user_id:
        # Tenta confirmar o check-in manualmente
        new_total_score = await mongodb_client.confirm_manual_checkin(
            chat_id, target_user_id, target_user_name, target_username
        )

        # Tenta deletar a mensagem de comando
        try:
            await update.message.delete()
        except Exception as e:
            logger.error(f"Erro ao deletar mensagem de comando /confirmcheckin: {e}")

        if new_total_score is not None:
            display_name = f"@{target_username}" if target_username else target_user_name
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ Check-in manual confirmado para {display_name}! Novo score total: <b>{new_total_score}</b> pontos.",
                parse_mode=ParseMode.HTML
            )
        else:
            # Mensagem se já fez check-in ou erro
            display_name = f"@{target_username}" if target_username else target_user_name
            active_checkin = await mongodb_client.get_active_checkin(chat_id)
            if active_checkin:
                # Verifica se o erro foi por já ter feito check-in
                existing = await mongodb_client.db.user_checkins.find_one({
                    "chat_id": chat_id,
                    "user_id": target_user_id,
                    "anchor_id": active_checkin['_id']
                })
                if existing:
                    msg = f"⚠️ {display_name} já possui check-in registrado para a âncora atual."
                else:
                    msg = f"❌ Ocorreu um erro ao tentar confirmar o check-in para {display_name}."
                await context.bot.send_message(chat_id=chat_id, text=msg)
            else:
                 await context.bot.send_message(
                     chat_id=chat_id,
                     text=f"❌ Não há check-in ativo para confirmar manualmente."
                 ) 