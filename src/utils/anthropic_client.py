"""
Cliente para a API da Anthropic.
"""
import os
import logging
import httpx
import base64
from typing import Optional, List, Dict, Any, Union

logger = logging.getLogger(__name__)

class AnthropicClient:
    """Cliente para a API da Anthropic."""
    
    BASE_URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa o cliente da Anthropic.
        
        Args:
            api_key (Optional[str]): Chave de API da Anthropic. Se não for fornecida,
                                    será buscada na variável de ambiente ANTHROPIC_API_KEY.
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            logger.error("API key da Anthropic não encontrada.")
            raise ValueError(
                "API key da Anthropic não encontrada. "
                "Defina a variável de ambiente ANTHROPIC_API_KEY ou forneça a chave ao inicializar o cliente."
            )
        # Log dos primeiros 5 caracteres da chave para verificação
        logger.debug(f"Anthropic API key inicializada (primeiros 5 caracteres): {self.api_key[:5]}...")
    
    async def generate_response(
        self, 
        prompt_template: str, 
        message_content: str, 
        image_data: Optional[bytes] = None,
        image_mime_type: Optional[str] = None,
        max_tokens: int = 1024
    ) -> str:
        """
        Gera uma resposta usando a API da Anthropic.
        
        Args:
            prompt_template (str): Template do prompt com placeholder para a mensagem.
            message_content (str): Conteúdo da mensagem a ser inserido no template.
            image_data (Optional[bytes]): Dados binários da imagem, se houver.
            image_mime_type (Optional[str]): Tipo MIME da imagem (ex: "image/jpeg").
            max_tokens (int): Número máximo de tokens na resposta.
            
        Returns:
            str: Resposta gerada pela API da Anthropic.
            
        Raises:
            Exception: Se ocorrer um erro na chamada da API.
        """
        # Substitui os placeholders pela mensagem real
        prompt = prompt_template.replace("{{mensagem_de_apresentacao_membro}}", message_content)
        prompt = prompt.replace("{{receita_ou_alimento}}", message_content)
        prompt = prompt.replace("{{duvida}}", message_content)
        
        logger.debug(f"Prompt para Anthropic API (primeiros 100 caracteres): {prompt[:100]}...")
        
        # Prepara os headers e o payload
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.API_VERSION,
            "content-type": "application/json"
        }
        
        # Verifica se a chave da API tem o formato correto
        if not self.api_key.startswith("sk-ant-"):
            logger.error("Formato da chave da API inválido. A chave deve começar com 'sk-ant-'")
            raise ValueError("Formato da chave da API inválido. A chave deve começar com 'sk-ant-'")
            
        # Log dos headers (sem expor a chave completa)
        safe_headers = headers.copy()
        if "x-api-key" in safe_headers:
            key_value = safe_headers["x-api-key"]
            safe_headers["x-api-key"] = f"{key_value[:8]}...{key_value[-4:]}" if len(key_value) > 12 else "***"
        logger.debug(f"Headers da requisição: {safe_headers}")
        
        # Prepara o conteúdo da mensagem
        message_content_list: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
        
        # Adiciona a imagem, se fornecida
        if image_data and image_mime_type:
            try:
                # Codifica a imagem em base64
                base64_image = base64.b64encode(image_data).decode("utf-8")
                
                # Adiciona a imagem ao conteúdo da mensagem
                message_content_list.insert(0, {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image_mime_type,
                        "data": base64_image
                    }
                })
                
                logger.info("Imagem adicionada ao prompt")
            except Exception as e:
                logger.error(f"Erro ao processar imagem: {e}")
        
        payload = {
            "model": "claude-3-7-sonnet-latest",
            "max_tokens": max_tokens,
            "messages": [
                {"role": "user", "content": message_content_list}
            ]
        }
        
        logger.debug(f"Fazendo chamada para a API Anthropic: {self.BASE_URL}")
        
        try:
            # Faz a chamada para a API
            async with httpx.AsyncClient() as client:
                logger.debug("Iniciando solicitação para API Anthropic...")
                response = await client.post(
                    self.BASE_URL,
                    headers=headers,
                    json=payload,
                    timeout=60.0  # Aumentando o timeout para 60 segundos
                )
                
                # Log da resposta HTTP
                logger.debug(f"Resposta HTTP da API Anthropic: {response.status_code}")
                
                # Verifica se a chamada foi bem-sucedida
                response.raise_for_status()
                
                # Processa a resposta
                response_data = response.json()
                logger.debug("Resposta da API recebida com sucesso")
                
                # Extrai o texto da resposta
                if response_data.get("content") and len(response_data["content"]) > 0:
                    response_text = response_data["content"][0]["text"].strip()
                    logger.debug(f"Resposta extraída (primeiros 100 caracteres): {response_text[:100]}...")
                    return response_text
                else:
                    logger.error(f"Resposta inesperada da API: {response_data}")
                    return "Desculpe, não consegui gerar uma resposta adequada."
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Erro HTTP ao chamar a API da Anthropic: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Erro HTTP ao gerar resposta: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Erro de requisição ao chamar a API da Anthropic: {e}")
            raise Exception(f"Erro de rede ao gerar resposta: {e}")
        except Exception as e:
            logger.error(f"Erro ao chamar a API da Anthropic: {e}")
            raise Exception(f"Erro ao gerar resposta: {e}") 