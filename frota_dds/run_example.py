#!/usr/bin/env python3
# run_example.py - Script de inicialização do exemplo de frota

import os
import sys
import subprocess
import time

def check_python_version():
    """Verifica se a versão do Python é adequada"""
    if sys.version_info < (3, 8):
        print("ERRO - Python 3.8+ é necessário")
        print(f"   Versão atual: {sys.version}")
        return False
    print(f"OK - Python {sys.version.split()[0]} - OK")
    return True

def check_dependencies():
    """Verifica se as dependências estão instaladas"""
    dependencies = [
        ('cyclonedds', 'Cyclone DDS Python'),
        ('numpy', 'NumPy'),
        ('matplotlib', 'Matplotlib'),
        ('pandas', 'Pandas')
    ]
    
    missing = []
    
    for module, name in dependencies:
        try:
            __import__(module)
            print(f"OK - {name} - OK")
        except ImportError:
            print(f"ERRO - {name} - NÃO INSTALADO")
            missing.append(module)
    
    return missing

def install_dependencies(missing):
    """Instala dependências faltantes"""
    if not missing:
        return True
    
    print(f"\nInstalando {len(missing)} dependências faltantes...")
    
    try:
        cmd = [sys.executable, '-m', 'pip', 'install'] + missing
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Dependências instaladas com sucesso!")
            return True
        else:
            print(f"ERRO na instalação: {result.stderr}")
            return False
    except Exception as e:
        print(f"ERRO ao instalar dependências: {e}")
        return False

def setup_environment():
    """Configura o ambiente DDS"""
    # Definir variável de ambiente para configuração do Cyclone DDS
    config_file = os.path.join(os.path.dirname(__file__), 'cyclonedds_config.xml')
    if os.path.exists(config_file):
        os.environ['CYCLONEDDS_URI'] = f'file://{config_file}'
        print(f"Configuração DDS carregada: {config_file}")
    else:
        print("AVISO - Arquivo de configuração DDS não encontrado, usando padrões")

def test_dds_functionality():
    """Testa funcionalidade básica do DDS"""
    try:
        from cyclonedds.domain import DomainParticipant
        
        # Teste básico de criação de participante
        participant = DomainParticipant()
        
        print("Funcionalidade DDS - OK")
        return True
    except Exception as e:
        print(f"ERRO no DDS: {e}")
        return False

def show_menu():
    """Mostra menu de opções"""
    print("\n" + "=" * 60)
    print("SISTEMA DE MONITORAMENTO DE FROTA - CYCLONE DDS")
    print("=" * 60)
    print("1. Executar teste básico")
    print("2. Simulação completa (interativa)")
    print("3. Executar apenas um veículo")
    print("4. Executar apenas o monitor")
    print("5. Verificar instalação")
    print("6. Instalar/atualizar dependências")
    print("7. Mostrar ajuda")
    print("8. Sair")
    print("=" * 60)

def run_test():
    """Executa teste básico"""
    print("\nExecutando teste básico...")
    try:
        import test_basic
        test_basic.main()
    except Exception as e:
        print(f"ERRO no teste: {e}")

def run_simulation():
    """Executa simulação completa"""
    print("\nIniciando simulação completa...")
    try:
        import fleet_simulation
        fleet_simulation.main()
    except Exception as e:
        print(f"ERRO na simulação: {e}")

def run_vehicle():
    """Executa apenas um veículo"""
    vehicle_id = input("\nDigite o ID do veículo (ex: TRUCK_001): ").strip()
    if not vehicle_id:
        vehicle_id = "TEST_VEHICLE"
    
    print(f"Iniciando veículo {vehicle_id}...")
    try:
        from vehicle_publisher import VehiclePublisher
        vehicle = VehiclePublisher(vehicle_id)
        vehicle.run(duration_seconds=300, publish_interval=2)
        vehicle.cleanup()
    except Exception as e:
        print(f"ERRO no veículo: {e}")

def run_monitor():
    """Executa apenas o monitor"""
    print("\nIniciando monitor de tráfego...")
    try:
        from traffic_monitor import TrafficMonitor
        monitor = TrafficMonitor()
        monitor.start_monitoring()
        
        print("Monitor ativo. Pressione Ctrl+C para parar...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nParando monitor...")
    except Exception as e:
        print(f"ERRO no monitor: {e}")
    finally:
        try:
            monitor.cleanup()
        except:
            pass

def show_help():
    """Mostra informações de ajuda"""
    print("\n" + "=" * 60)
    print("AJUDA - SISTEMA DE MONITORAMENTO DE FROTA")
    print("=" * 60)
    print("\nDESCRIÇÃO:")
    print("Este sistema demonstra o uso do Cyclone DDS para monitoramento")
    print("de frota de veículos em tempo real.")
    
    print("\nCOMPONENTES:")
    print("• vehicle_publisher.py - Simula veículos individuais")
    print("• traffic_monitor.py - Monitor central de tráfego")
    print("• fleet_simulation.py - Simulação completa coordenada")
    print("• test_basic.py - Teste básico de funcionalidade")
    
    print("\nEXECUÇÃO RECOMENDADA:")
    print("1. Execute primeiro o 'Teste básico' para verificar funcionamento")
    print("2. Use a 'Simulação completa' para demonstração interativa")
    print("3. Para entender melhor, execute monitor e veículos separadamente")
    
    print("\nSOLUÇÃO DE PROBLEMAS:")
    print("• Se houver erros de importação, use 'Instalar dependências'")
    print("• Para problemas de DDS, verifique firewall e permissões")
    print("• Consulte o README.md para informações detalhadas")
    
    print("\nARQUIVOS IMPORTANTES:")
    print("• README.md - Documentação completa")
    print("• requirements.txt - Lista de dependências")
    print("• cyclonedds_config.xml - Configuração DDS")
    print("=" * 60)

def main():
    """Função principal"""
    print("Inicializando Sistema de Monitoramento de Frota...")
    
    # Verificações iniciais
    if not check_python_version():
        return
    
    # Configurar ambiente
    setup_environment()
    
    # Verificar dependências
    missing = check_dependencies()
    
    if missing:
        print(f"\nAVISO - {len(missing)} dependências faltantes detectadas")
        install = input("Deseja instalar automaticamente? (s/n): ").lower().strip()
        
        if install in ['s', 'sim', 'y', 'yes']:
            if not install_dependencies(missing):
                print("ERRO - Falha na instalação. Execute manualmente:")
                print(f"pip install {' '.join(missing)}")
                return
        else:
            print("ERRO - Dependências necessárias não instaladas")
            return
    
    # Testar funcionalidade DDS
    if not test_dds_functionality():
        print("ERRO - Problema com Cyclone DDS. Verifique a instalação.")
        return
    
    print("\nSistema pronto para uso!")
    
    # Menu principal
    while True:
        show_menu()
        
        try:
            choice = input("\nEscolha uma opção (1-8): ").strip()
            
            if choice == '1':
                run_test()
            elif choice == '2':
                run_simulation()
            elif choice == '3':
                run_vehicle()
            elif choice == '4':
                run_monitor()
            elif choice == '5':
                print("\nVerificando instalação...")
                check_python_version()
                missing = check_dependencies()
                test_dds_functionality()
                if not missing:
                    print("Tudo OK!")
            elif choice == '6':
                print("\nInstalando/atualizando dependências...")
                subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
            elif choice == '7':
                show_help()
            elif choice == '8':
                print("\nEncerrando...")
                break
            else:
                print("ERRO - Opção inválida")
        
        except KeyboardInterrupt:
            print("\n\nPrograma interrompido")
            break
        except Exception as e:
            print(f"ERRO inesperado: {e}")
    
    print("Programa finalizado")

if __name__ == "__main__":
    main()