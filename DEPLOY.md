# 🚀 Guia de Deploy - Gym Nation Bot

Este guia explica como fazer o deploy do bot em Docker e migrar os dados para MongoDB Atlas.

## 📋 Pré-requisitos

### 1. Docker
- Docker Engine instalado e rodando
- Docker Compose (ou `docker compose`)

### 2. MongoDB Atlas
- Cluster MongoDB Atlas configurado
- String de conexão do Atlas disponível
- Usuário com permissões de leitura/escrita

### 3. Variáveis de Ambiente
- Arquivo `.env` configurado com todas as variáveis necessárias

## 🔧 Configuração Inicial

### 1. Configurar Variáveis de Ambiente

Copie o arquivo de exemplo e configure suas variáveis:

```bash
cp .env.example .env
```

Edite o arquivo `.env` e configure:

```bash
# Configurações do Bot
TELEGRAM_API_TOKEN=seu_token_do_botfather
OWNER_ID=seu_id_telegram
BOT_USERNAME=seu_bot_username
ANTHROPIC_API_KEY=sua_chave_anthropic

# MongoDB Atlas (Produção)
MONGODB_CONNECTION_STRING=mongodb+srv://username:password@cluster.mongodb.net/gym_nation_bot?retryWrites=true&w=majority

# Para migração (se necessário)
MONGODB_LOCAL_CONNECTION_STRING=mongodb://admin:password@localhost:27017
MONGODB_ATLAS_CONNECTION_STRING=mongodb+srv://username:password@cluster.mongodb.net/gym_nation_bot?retryWrites=true&w=majority

# Configurações opcionais
QA_DAILY_LIMIT=2
LOG_LEVEL=INFO
```

### 2. Verificar Configuração

Teste se suas configurações estão corretas:

```bash
python scripts/deploy.py --status
```

## 📦 Migração de Dados

Se você tem dados no MongoDB local que precisam ser migrados para o Atlas:

### 1. Migração Automática (Recomendado)

```bash
# Migração + Deploy em produção
python scripts/deploy.py --prod --migrate --build

# Ou apenas migração
python scripts/migrate_to_atlas.py
```

### 2. Migração Manual

```bash
# 1. Certifique-se que o MongoDB local está rodando
docker-compose up -d mongodb

# 2. Execute o script de migração
python scripts/migrate_to_atlas.py

# 3. Verifique se os dados foram migrados corretamente
```

## 🚀 Deploy

### Desenvolvimento (com MongoDB local)

```bash
# Deploy simples
python scripts/deploy.py

# Deploy com rebuild
python scripts/deploy.py --build

# Deploy e mostrar logs
python scripts/deploy.py --build --logs
```

### Produção (apenas MongoDB Atlas)

```bash
# Deploy em produção
python scripts/deploy.py --prod --build

# Deploy com migração
python scripts/deploy.py --prod --migrate --build

# Deploy e mostrar logs
python scripts/deploy.py --prod --build --logs
```

### Comandos Docker Manuais

Se preferir usar Docker diretamente:

```bash
# Desenvolvimento
docker-compose up -d --build

# Produção
docker-compose -f docker-compose.prod.yml up -d --build
```

## 📊 Monitoramento

### Verificar Status

```bash
# Via script
python scripts/deploy.py --status

# Via Docker
docker-compose ps
# ou
docker-compose -f docker-compose.prod.yml ps
```

### Ver Logs

```bash
# Via script
python scripts/deploy.py --logs

# Via Docker
docker-compose logs -f gym-nation-bot
# ou
docker-compose -f docker-compose.prod.yml logs -f gym-nation-bot
```

### Health Check

O container em produção inclui um health check que verifica:
- Conectividade com MongoDB
- Status do bot

```bash
# Verificar health
docker inspect gym-nation-bot-prod | grep -A 10 Health
```

## 🔄 Atualizações

### Atualizar o Bot

```bash
# 1. Parar o serviço
docker-compose down

# 2. Atualizar código (git pull, etc.)

# 3. Rebuild e restart
python scripts/deploy.py --build
```

### Rollback

```bash
# Parar serviços
docker-compose down

# Voltar para versão anterior do código
git checkout <commit-anterior>

# Deploy da versão anterior
python scripts/deploy.py --build
```

## 🛠️ Troubleshooting

### Problemas Comuns

#### 1. Erro de Conexão com MongoDB Atlas

```bash
# Verificar string de conexão
echo $MONGODB_CONNECTION_STRING

# Testar conexão
python -c "
import motor.motor_asyncio
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
async def test():
    client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv('MONGODB_CONNECTION_STRING'))
    await client.admin.command('ping')
    print('✅ Conexão OK')
    client.close()

asyncio.run(test())
"
```

#### 2. Container não inicia

```bash
# Ver logs detalhados
docker-compose logs gym-nation-bot

# Verificar configuração
docker-compose config
```

#### 3. Problemas de permissão

```bash
# Verificar se o usuário botuser tem permissões
docker-compose exec gym-nation-bot ls -la /app
```

#### 4. Migração falha

```bash
# Verificar logs de migração
cat migration.log

# Verificar conectividade com ambos os bancos
python scripts/migrate_to_atlas.py --dry-run  # (se implementado)
```

### Logs Úteis

```bash
# Logs do bot
docker-compose logs -f gym-nation-bot

# Logs do MongoDB (desenvolvimento)
docker-compose logs -f mongodb

# Logs de sistema do container
docker-compose exec gym-nation-bot tail -f /var/log/syslog
```

## 📁 Estrutura de Arquivos

```
projeto/
├── Dockerfile                 # Imagem do bot
├── docker-compose.yml         # Desenvolvimento
├── docker-compose.prod.yml    # Produção
├── .dockerignore              # Arquivos ignorados
├── .env                       # Variáveis de ambiente
├── .env.example               # Exemplo de configuração
├── scripts/
│   ├── deploy.py              # Script de deploy
│   └── migrate_to_atlas.py    # Script de migração
└── src/                       # Código do bot
```

## 🔒 Segurança

### Boas Práticas

1. **Nunca commitar o arquivo `.env`**
2. **Usar usuário não-root no container**
3. **Configurar firewall adequadamente**
4. **Usar HTTPS para webhooks (se aplicável)**
5. **Rotacionar tokens periodicamente**

### Variáveis Sensíveis

Mantenha estas variáveis seguras:
- `TELEGRAM_API_TOKEN`
- `ANTHROPIC_API_KEY`
- `MONGODB_CONNECTION_STRING`

## 📞 Suporte

Em caso de problemas:

1. Verificar logs: `python scripts/deploy.py --logs`
2. Verificar status: `python scripts/deploy.py --status`
3. Consultar este guia
4. Verificar documentação do Docker/MongoDB Atlas 