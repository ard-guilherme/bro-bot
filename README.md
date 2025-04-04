# BRO BOT

Um bot para Telegram desenvolvido para a comunidade GYM NATION de academia e fitness. O bot dá boas-vindas aos novos membros do grupo, incentiva apresentações, fornece mensagens motivacionais e gerencia um sistema de check-in para os membros.

## Funcionalidades

- Detecção automática de novos membros no grupo
- Mensagens de boas-vindas personalizadas
- Incentivo a apresentações dos novos membros
- Comando `/motivacao` para receber frases motivacionais geradas por IA
- Reações automáticas a mensagens de apresentação
- Sistema de check-in para membros do grupo
- Ranking de check-ins dos usuários
- Cálculo de macronutrientes para receitas e alimentos
- Assistente de Dúvidas Fitness por Menção (responde a dúvidas quando mencionado)
- Sistema de blacklist para gerenciamento de usuários
- Sistema de mensagens recorrentes automáticas
- Integração com MongoDB para armazenamento de dados
- Suporte a Docker para fácil implantação
- Sistema de administradores para permitir que outros usuários utilizem o bot
- Restrição de uso apenas para o proprietário e administradores do bot

## Requisitos

- Python 3.8+
- python-telegram-bot 20.7+
- python-dotenv 1.0.0+
- pytest 8.3.4+ (para testes)
- anthropic (para geração de mensagens motivacionais)
- motor 3.7.0+ (cliente MongoDB assíncrono)
- pymongo 4.11.1+
- MongoDB (local ou remoto)

## Instalação

1. Clone o repositório:

```bash
git clone https://github.com/seu-usuario/gym-nation-bot.git
cd gym-nation-bot
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Configure as variáveis de ambiente:
   - Crie um arquivo `.env` na raiz do projeto baseado no `.env.example`
   - Adicione suas chaves API e configurações:

```
TELEGRAM_API_TOKEN=seu_token_aqui
ANTHROPIC_API_KEY=sua_chave_anthropic_aqui
MONGODB_CONNECTION_STRING=sua_string_de_conexao_mongodb
OWNER_ID=seu_id_do_telegram
BOT_USERNAME=Nations_bro_bot
```

## Restrição de Uso

O bot está configurado para ser usado pelo proprietário e administradores designados. Isso significa que:

1. O proprietário (definido pela variável `OWNER_ID`) pode:

   - Adicionar o bot a grupos
   - Interagir com o bot em chats privados
   - Usar todos os comandos do bot em grupos
   - Adicionar ou remover administradores do bot

2. Administradores (adicionados pelo proprietário) podem:

   - Interagir com o bot em chats privados
   - Usar a maioria dos comandos do bot em grupos

3. Mensagens de outros usuários são silenciosamente ignoradas, sem qualquer resposta.

4. No entanto, todos os membros do grupo podem usar o Assistente de Dúvidas Fitness mencionando o bot em resposta a uma mensagem com uma dúvida.

Para obter seu ID do Telegram, envie uma mensagem para [@userinfobot](https://t.me/userinfobot).

## Uso

### Método 1: Execução direta

Execute o bot com:

```bash
python -m src.main
```

### Método 2: Usando Docker

1. Inicie o MongoDB e o bot com Docker Compose:

```bash
docker-compose up -d
```

2. Para parar os serviços:

```bash
docker-compose down
```

## Comandos do Bot

### Comandos para todos os usuários

- `/start` - Inicia o bot
- `/help` - Mostra a mensagem de ajuda
- `/motivacao` - Envia uma mensagem de motivação fitness
- `/apresentacao` - Responde com uma apresentação personalizada
- `/macros` - Calcula macronutrientes de uma receita ou alimento
- `/checkinscore` - Mostra o ranking de check-ins dos usuários

### Comandos apenas para administradores

- `/checkin` - Define uma mensagem como âncora de check-in
- `/endcheckin` - Desativa o check-in atual

### Comandos apenas para o proprietário

- `/setadmin` - Adiciona um usuário como administrador do bot
- `/deladmin` - Remove um usuário da lista de administradores do bot
- `/listadmins` - Lista todos os administradores do bot

## Sistema de Administradores

O bot inclui um sistema de administradores que permite:

1. O proprietário adicionar outros usuários como administradores usando `/setadmin`
2. O proprietário remover administradores usando `/deladmin`
3. O proprietário visualizar a lista de administradores usando `/listadmins`

Para adicionar um administrador, o proprietário pode:

- Responder a uma mensagem do usuário com `/setadmin`
- Usar o comando com o ID do usuário: `/setadmin 123456789 [Nome do Usuário]`

Para remover um administrador:

- Responder a uma mensagem do usuário com `/deladmin`
- Usar o comando com o ID do usuário: `/deladmin 123456789`

## Sistema de Check-in

O bot inclui um sistema de check-in que permite:

1. Administradores definirem uma mensagem como âncora de check-in
2. Membros registrarem sua presença respondendo à mensagem de check-in
3. Visualização de um ranking de check-ins dos membros

## Assistente de Dúvidas Fitness por Menção

O bot inclui um sistema que permite qualquer membro do grupo obter respostas para dúvidas relacionadas a fitness:

1. O membro responde a uma mensagem que contém uma dúvida fitness mencionando o bot (ex: "@Nations_bro_bot")
2. O bot analisa a pergunta e responde com informações relevantes e baseadas em ciência
3. A resposta é categorizada automaticamente em uma das seguintes áreas:
   - 🏋️ Treino e Exercícios
   - 🥦 Nutrição e Dieta
   - 💊 Suplementação
   - 🧠 Motivação e Mentalidade
   - 📊 Progresso e Métricas
4. O sistema inclui:
   - Botões de feedback (👍 Útil / 👎 Impreciso) para avaliar a qualidade das respostas
   - Modo Especialista que fornece respostas mais detalhadas enviadas por mensagem privada
   - Limite diário de consultas por usuário (10 por dia) para evitar sobrecarga
   - Armazenamento e análise das interações para melhoria contínua

Exemplo de uso:
1. Usuário A: "Alguém sabe se agachamento livre é melhor que leg press?"
2. Usuário B: "@Nations_bro_bot"
3. Bot responde com informações relevantes sobre os exercícios

## Testes

Execute os testes com:

```bash
pytest
```

## Estrutura do Projeto

```
gym-nation-bot/
├── .env                      # Variáveis de ambiente (não versionado)
├── .env.example             # Exemplo de variáveis de ambiente
├── requirements.txt         # Dependências do projeto
├── docker-compose.yml       # Configuração do Docker
├── src/                     # Código fonte
│   ├── __init__.py
│   ├── main.py              # Ponto de entrada
│   ├── bot/                 # Lógica do bot
│   │   ├── __init__.py
│   │   ├── handlers.py      # Manipuladores principais
│   │   ├── blacklist_handlers.py # Gerenciamento de blacklist
│   │   ├── checkin_handlers.py   # Sistema de check-in
│   │   ├── mention_handlers.py   # Respostas a menções
│   │   ├── messages.py      # Mensagens do bot
│   │   ├── motivation.py    # Mensagens motivacionais
│   │   └── fitness_qa.py    # Sistema de Q&A fitness
│   └── utils/              # Utilitários
│       ├── __init__.py
│       ├── config.py       # Configurações
│       ├── filters.py      # Filtros de mensagens
│       ├── mongodb_client.py # Cliente MongoDB
│       ├── mongodb_instance.py # Instância MongoDB
│       ├── anthropic_client.py # Cliente Anthropic
│       └── recurring_messages_manager.py # Gerenciador de mensagens recorrentes
├── tests/                  # Testes
│   ├── __init__.py
│   ├── test_qa_functions.py
│   ├── test_recurring_messages.py
│   ├── test_recurring_commands.py
│   └── test_edited_messages.py
├── scripts/               # Scripts utilitários
│   ├── check_recurring_messages.py
│   ├── clean_recurring_messages.py
│   ├── create_test_recurring_message.py
│   ├── fix_db.py
│   └── check_db.py
└── docs/                  # Documentação adicional
```

## Novas Funcionalidades

### Sistema de Blacklist

O bot agora inclui um sistema de blacklist que permite:
- Adicionar usuários à blacklist
- Remover usuários da blacklist
- Verificar se um usuário está na blacklist
- Gerenciar automaticamente usuários problemáticos

### Sistema de Mensagens Recorrentes

O bot possui um sistema de mensagens recorrentes que:
- Permite configurar mensagens para serem enviadas periodicamente
- Suporta diferentes intervalos de tempo
- Permite edição e remoção de mensagens recorrentes
- Inclui scripts de manutenção para gerenciamento

## Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou enviar pull requests.

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo LICENSE para mais detalhes. 

## Mensagens Recorrentes

O bot permite configurar mensagens que serão enviadas automaticamente em intervalos regulares.

### Como usar

1. **Configurar uma mensagem recorrente**:
   ```
   /sayrecurrent <intervalo> <mensagem>
   ```
   
   Exemplos de intervalo:
   - `30m` - 30 minutos
   - `1h` - 1 hora
   - `1h30m` - 1 hora e 30 minutos
   - `30` - 30 minutos (sem unidade assume minutos)

   Exemplo completo:
   ```
   /sayrecurrent 30m Lembrete para beber água!
   ```

2. **Listar mensagens recorrentes**:
   ```
   /listrecurrent
   ```
   
   Isso mostrará todas as mensagens recorrentes configuradas para o chat, incluindo:
   - ID da mensagem
   - Texto da mensagem
   - Intervalo
   - Quem adicionou
   - Data de criação
   - Data do último envio

3. **Desativar uma mensagem recorrente**:
   ```
   /delrecurrent <id_da_mensagem>
   ```
   
   O ID da mensagem pode ser obtido com o comando `/listrecurrent`.

### Comportamento

- As mensagens recorrentes são enviadas automaticamente nos intervalos configurados
- A primeira mensagem será enviada após o intervalo completo a partir do momento da configuração
- As mensagens são enviadas com o formato "🟢 MENSAGEM RECORRENTE 🟢" seguido do texto configurado
- Se o bot for reiniciado, as mensagens recorrentes serão retomadas automaticamente 