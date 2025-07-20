#!/usr/bin/env python3
"""
Script de configuração para sistema RTT Cyclone DDS

Este script automatiza a instalação e configuração inicial
do sistema de medição RTT.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def print_header(title):
    """
    Imprime cabeçalho formatado.
    
    Args:
        title: Título do cabeçalho
    """
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def run_command(command, description, check=True):
    """
    Executa comando do sistema com feedback.
    
    Args:
        command: Comando a executar (lista ou string)
        description: Descrição da operação
        check: Se deve verificar código de retorno
        
    Returns:
        bool: True se comando executou com sucesso
    """
    print(f"\n{description}...")
    
    try:
        if isinstance(command, str):
            command = command.split()
            
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=check
        )
        
        if result.returncode == 0:
            print(f"✓ {description} - Sucesso")
            if result.stdout.strip():
                print(f"  Saída: {result.stdout.strip()[:200]}...")
            return True
        else:
            print(f"✗ {description} - Falhou")
            if result.stderr.strip():
                print(f"  Erro: {result.stderr.strip()[:200]}...")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} - Falhou com código {e.returncode}")
        if e.stderr:
            print(f"  Erro: {e.stderr.strip()[:200]}...")
        return False
    except FileNotFoundError:
        print(f"✗ {description} - Comando não encontrado")
        return False
    except Exception as e:
        print(f"✗ {description} - Erro: {e}")
        return False


def check_python_version():
    """
    Verifica se a versão do Python é adequada.
    
    Returns:
        bool: True se versão é adequada
    """
    print_header("VERIFICAÇÃO DO PYTHON")
    
    version = sys.version_info
    print(f"Versão do Python: {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 7:
        print("✓ Versão do Python adequada (>= 3.7)")
        return True
    else:
        print("✗ Python 3.7+ é necessário")
        return False


def setup_virtual_environment():
    """
    Configura ambiente virtual Python.
    
    Returns:
        bool: True se configuração foi bem-sucedida
    """
    print_header("CONFIGURAÇÃO DO AMBIENTE VIRTUAL")
    
    venv_path = Path(".venv")
    
    if venv_path.exists():
        print("✓ Ambiente virtual já existe")
        return True
    
    # Tenta criar ambiente virtual com python3 primeiro (Linux)
    success = run_command(
        ["python3", "-m", "venv", ".venv"],
        "Criando ambiente virtual com python3",
        check=False
    )
    
    if not success:
        # Tenta com python (Windows/outros)
        success = run_command(
            [sys.executable, "-m", "venv", ".venv"],
            "Criando ambiente virtual com python"
        )
    
    if not success:
        print("\nTentando com virtualenv...")
        success = run_command(
            ["virtualenv", ".venv"],
            "Criando ambiente virtual com virtualenv",
            check=False
        )
    
    if not success:
        print("\n⚠️  Erro ao criar ambiente virtual.")
        print("Soluções possíveis:")
        print("1. Instale python3-venv: sudo apt install python3-venv")
        print("2. Instale virtualenv: pip install virtualenv")
        print("3. Use python3 -m venv .venv manualmente")
    
    return success


def get_activation_command():
    """
    Retorna comando de ativação do ambiente virtual.
    
    Returns:
        str: Comando de ativação
    """
    system = platform.system().lower()
    
    if system == "windows":
        return ".venv\\Scripts\\activate"
    else:
        return "source .venv/bin/activate"


def install_python_dependencies():
    """
    Instala dependências Python.
    
    Returns:
        bool: True se instalação foi bem-sucedida
    """
    print_header("INSTALAÇÃO DE DEPENDÊNCIAS PYTHON")
    
    # Determina executável pip no ambiente virtual
    system = platform.system().lower()
    if system == "windows":
        pip_path = ".venv\\Scripts\\pip"
        python_path = ".venv\\Scripts\\python"
    else:
        pip_path = ".venv/bin/pip"
        python_path = ".venv/bin/python"
    
    # Verifica se está no ambiente virtual
    if not Path(pip_path).exists():
        print("⚠️  Ambiente virtual não encontrado ou não ativado.")
        print("Certifique-se de que o ambiente virtual foi criado corretamente.")
        return False
    
    # Atualiza pip
    run_command(
        [pip_path, "install", "--upgrade", "pip"],
        "Atualizando pip",
        check=False
    )
    
    # Instala dependências básicas
    success = run_command(
        [pip_path, "install", "cyclonedds"],
        "Instalando Cyclone DDS Python bindings"
    )
    
    # Instala outras dependências
    if Path("requirements.txt").exists():
        run_command(
            [pip_path, "install", "-r", "requirements.txt"],
            "Instalando dependências do requirements.txt",
            check=False
        )
    
    if not success:
        print("\n⚠️  Falha na instalação. Possíveis soluções:")
        print("1. Certifique-se de estar no ambiente virtual:")
        print(f"   source .venv/bin/activate  # Linux/Mac")
        print(f"   .venv\\Scripts\\activate     # Windows")
        print("2. Use o pip do ambiente virtual diretamente:")
        print(f"   {pip_path} install cyclonedds")
        print("3. Se erro 'externally-managed-environment':")
        print("   sudo apt install python3-venv python3-full")
    
    return success


def test_cyclone_dds():
    """
    Testa se Cyclone DDS está funcionando.
    
    Returns:
        bool: True se teste passou
    """
    print_header("TESTE DO CYCLONE DDS")
    
    # Determina executável python no ambiente virtual
    system = platform.system().lower()
    if system == "windows":
        python_path = ".venv\\Scripts\\python"
    else:
        python_path = ".venv/bin/python"
    
    # Teste básico de importação
    test_code = """
try:
    from cyclonedds.domain import DomainParticipant
    participant = DomainParticipant(0)
    participant.close()
    print("SUCCESS: Cyclone DDS funcionando")
except Exception as e:
    print(f"ERROR: {e}")
    exit(1)
"""
    
    success = run_command(
        [python_path, "-c", test_code],
        "Testando Cyclone DDS"
    )
    
    return success


def create_example_config():
    """
    Cria arquivos de configuração de exemplo.
    
    Returns:
        bool: True se criação foi bem-sucedida
    """
    print_header("CRIAÇÃO DE ARQUIVOS DE EXEMPLO")
    
    try:
        # Cria script de execução rápida
        quick_start_content = f"""#!/bin/bash
# Script de execução rápida

echo "Ativando ambiente virtual..."
{get_activation_command()}

echo "Iniciando servidor RTT..."
python servidor.py &
SERVER_PID=$!

echo "Aguardando servidor inicializar..."
sleep 3

echo "Executando cliente de teste..."
python cliente.py --client-id teste_rapido

echo "Parando servidor..."
kill $SERVER_PID

echo "Analisando resultados..."
python analisar_resultados.py

echo "Teste concluído!"
"""
        
        with open("quick_start.sh", "w") as f:
            f.write(quick_start_content)
        
        # Torna executável no Unix
        if platform.system().lower() != "windows":
            os.chmod("quick_start.sh", 0o755)
        
        print("✓ Script quick_start.sh criado")
        
        # Cria script Windows
        if platform.system().lower() == "windows":
            quick_start_bat = """@echo off
echo Ativando ambiente virtual...
call .venv\\Scripts\\activate

echo Iniciando servidor RTT...
start /B python servidor.py

echo Aguardando servidor inicializar...
timeout /t 3 /nobreak

echo Executando cliente de teste...
python cliente.py --client-id teste_rapido

echo Analisando resultados...
python analisar_resultados.py

echo Teste concluído!
pause
"""
            
            with open("quick_start.bat", "w") as f:
                f.write(quick_start_bat)
            
            print("✓ Script quick_start.bat criado")
        
        return True
        
    except Exception as e:
        print(f"✗ Erro ao criar arquivos de exemplo: {e}")
        return False


def show_next_steps():
    """
    Mostra próximos passos após configuração.
    """
    print_header("CONFIGURAÇÃO CONCLUÍDA")
    
    activation_cmd = get_activation_command()
    
    print("\n🎉 Sistema configurado com sucesso!")
    print("\nPróximos passos:")
    print(f"\n1. Ative o ambiente virtual:")
    print(f"   {activation_cmd}")
    
    print(f"\n2. Execute o exemplo de uso:")
    print(f"   python exemplo_uso.py")
    
    print(f"\n3. Ou execute teste completo:")
    if platform.system().lower() == "windows":
        print(f"   quick_start.bat")
    else:
        print(f"   ./quick_start.sh")
    
    print(f"\n4. Para uso manual:")
    print(f"   Terminal 1: python servidor.py")
    print(f"   Terminal 2: python cliente.py")
    
    print(f"\n5. Para múltiplos clientes:")
    print(f"   python multi_cliente.py 5")
    
    print(f"\n6. Para análise de resultados:")
    print(f"   python analisar_resultados.py")
    
    print(f"\nConsulte README.md para instruções detalhadas.")


def main():
    """
    Função principal do script de configuração.
    """
    print("Sistema de Medição RTT - Configuração Automática")
    print("Eclipse Cyclone DDS + Python")
    
    # Verifica versão do Python
    if not check_python_version():
        sys.exit(1)
    
    # Configura ambiente virtual
    if not setup_virtual_environment():
        print("\n✗ Falha ao configurar ambiente virtual")
        sys.exit(1)
    
    # Instala dependências
    if not install_python_dependencies():
        print("\n✗ Falha ao instalar dependências Python")
        print("\nTente instalar manualmente:")
        print("  pip install cyclonedds")
        sys.exit(1)
    
    # Testa Cyclone DDS
    if not test_cyclone_dds():
        print("\n✗ Cyclone DDS não está funcionando")
        print("\nPossíveis soluções:")
        print("1. Instale Cyclone DDS C library")
        print("2. Configure LD_LIBRARY_PATH (Linux/Mac)")
        print("3. Use cyclonedds: pip install cyclonedds")
        sys.exit(1)
    
    # Cria arquivos de exemplo
    create_example_config()
    
    # Mostra próximos passos
    show_next_steps()


if __name__ == "__main__":
    main()