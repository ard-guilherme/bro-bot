# Use uma imagem Python oficial como base
FROM python:3.11-slim

# Define variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Cria um usuário não-root para segurança
RUN groupadd -r botuser && useradd -r -g botuser botuser

# Define o diretório de trabalho
WORKDIR /app

# Copia apenas o requirements.txt primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instala as dependências Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia todo o código da aplicação
COPY . .

# Muda a propriedade dos arquivos para o usuário botuser
RUN chown -R botuser:botuser /app

# Muda para o usuário não-root
USER botuser

# Expõe a porta (caso seja necessário para webhooks futuramente)
EXPOSE 8080

# Define o comando padrão para executar o bot
CMD ["python", "-m", "src.main"] 