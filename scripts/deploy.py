#!/usr/bin/env python3
"""
Script para facilitar o deploy do bot em Docker.

Uso:
    python scripts/deploy.py [--prod] [--build] [--migrate]

Opções:
    --prod     Usa o docker-compose.prod.yml (apenas Atlas)
    --build    Força rebuild da imagem Docker
    --migrate  Executa migração dos dados antes do deploy
"""

import os
import sys
import subprocess
import argparse
from typing import List

def run_command(command: List[str], description: str = None) -> bool:
    """
    Executa um comando e retorna se foi bem-sucedido.
    
    Args:
        command: Lista com o comando a ser executado
        description: Descrição do que o comando faz
        
    Returns:
        bool: True se o comando foi bem-sucedido
    """
    if description:
        print(f"\n🔄 {description}...")
    
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERRO - Erro ao executar comando: {' '.join(command)}")
        print(f"Código de saída: {e.returncode}")
        if e.stderr:
            print(f"Erro: {e.stderr}")
        return False

def check_env_file():
    """Verifica se o arquivo .env existe."""
    if not os.path.exists('.env'):
        print("ERRO - Arquivo .env não encontrado!")
        print("Copie o .env.example e configure suas variáveis:")
        print("   cp .env.example .env")
        return False
    return True

def check_docker():
    """Verifica se o Docker está instalado e rodando."""
    if not run_command(['docker', '--version'], "Verificando Docker"):
        print("❌ Docker não está instalado ou disponível")
        return False
    
    if not run_command(['docker', 'info'], "Verificando se Docker está rodando"):
        print("❌ Docker não está rodando")
        return False
    
    return True

def check_docker_compose():
    """Verifica se o docker-compose está disponível."""
    # Tenta primeiro docker compose (novo)
    if run_command(['docker', 'compose', 'version'], "Verificando Docker Compose"):
        return 'docker compose'
    
    # Tenta docker-compose (legado)
    if run_command(['docker-compose', '--version'], "Verificando docker-compose"):
        return 'docker-compose'
    
    print("❌ Docker Compose não está disponível")
    return None

def migrate_data():
    """Executa a migração dos dados."""
    print("\n📦 Executando migração dos dados...")
    
    # Verifica se as variáveis de migração estão definidas
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.getenv("MONGODB_LOCAL_CONNECTION_STRING"):
        print("❌ MONGODB_LOCAL_CONNECTION_STRING não definida no .env")
        return False
    
    if not os.getenv("MONGODB_ATLAS_CONNECTION_STRING"):
        print("❌ MONGODB_ATLAS_CONNECTION_STRING não definida no .env")
        return False
    
    # Executa a migração
    return run_command([
        sys.executable, 'scripts/migrate_to_atlas.py'
    ], "Migrando dados para MongoDB Atlas")

def build_image(compose_cmd: str, compose_file: str = None):
    """Constrói a imagem Docker."""
    cmd = compose_cmd.split()
    if compose_file:
        cmd.extend(['-f', compose_file])
    cmd.append('build')
    
    return run_command(cmd, "Construindo imagem Docker")

def deploy_bot(compose_cmd: str, compose_file: str = None, build: bool = False):
    """Faz o deploy do bot."""
    cmd_base = compose_cmd.split()
    if compose_file:
        cmd_base.extend(['-f', compose_file])
    
    # Para o serviço se estiver rodando
    print("\n🛑 Parando serviços existentes...")
    run_command(cmd_base + ['down'], "Parando serviços")
    
    # Constrói se solicitado
    if build:
        if not build_image(compose_cmd, compose_file):
            return False
    
    # Inicia os serviços
    return run_command(cmd_base + ['up', '-d'], "Iniciando serviços")

def show_status(compose_cmd: str, compose_file: str = None):
    """Mostra o status dos containers."""
    cmd = compose_cmd.split()
    if compose_file:
        cmd.extend(['-f', compose_file])
    cmd.append('ps')
    
    run_command(cmd, "Status dos containers")

def show_logs(compose_cmd: str, compose_file: str = None):
    """Mostra os logs do bot."""
    cmd = compose_cmd.split()
    if compose_file:
        cmd.extend(['-f', compose_file])
    cmd.extend(['logs', '-f', '--tail=50', 'gym-nation-bot'])
    
    print("\n📋 Logs do bot (Ctrl+C para sair):")
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n✋ Logs interrompidos")

def main():
    """Função principal."""
    parser = argparse.ArgumentParser(description="Deploy do Gym Nation Bot")
    parser.add_argument('--prod', action='store_true', 
                       help='Usa configuração de produção (apenas Atlas)')
    parser.add_argument('--build', action='store_true',
                       help='Força rebuild da imagem Docker')
    parser.add_argument('--migrate', action='store_true',
                       help='Executa migração dos dados antes do deploy')
    parser.add_argument('--logs', action='store_true',
                       help='Mostra os logs após o deploy')
    parser.add_argument('--status', action='store_true',
                       help='Apenas mostra o status dos containers')
    
    args = parser.parse_args()
    
    print("🤖 Deploy do Gym Nation Bot")
    print("=" * 40)
    
    # Verificações preliminares
    if not check_env_file():
        sys.exit(1)
    
    if not check_docker():
        sys.exit(1)
    
    compose_cmd = check_docker_compose()
    if not compose_cmd:
        sys.exit(1)
    
    # Define arquivo de compose
    compose_file = 'docker-compose.prod.yml' if args.prod else 'docker-compose.yml'
    
    print(f"\n📋 Configuração:")
    print(f"   Modo: {'Produção' if args.prod else 'Desenvolvimento'}")
    print(f"   Arquivo: {compose_file}")
    print(f"   Build: {'Sim' if args.build else 'Não'}")
    print(f"   Migração: {'Sim' if args.migrate else 'Não'}")
    
    # Apenas status
    if args.status:
        show_status(compose_cmd, compose_file)
        return
    
    # Executa migração se solicitado
    if args.migrate:
        if not migrate_data():
            print("❌ Migração falhou!")
            sys.exit(1)
        print("✅ Migração concluída com sucesso!")
    
    # Faz o deploy
    if not deploy_bot(compose_cmd, compose_file, args.build):
        print("❌ Deploy falhou!")
        sys.exit(1)
    
    print("\n✅ Deploy concluído com sucesso!")
    
    # Mostra status
    show_status(compose_cmd, compose_file)
    
    # Mostra logs se solicitado
    if args.logs:
        show_logs(compose_cmd, compose_file)
    else:
        print(f"\n💡 Para ver os logs: python scripts/deploy.py --logs")
        print(f"💡 Para verificar status: python scripts/deploy.py --status")

if __name__ == "__main__":
    main() 