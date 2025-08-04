#!/usr/bin/env python3
# test_basic.py - Teste básico do sistema DDS

import time
import threading
from vehicle_publisher import VehiclePublisher
from traffic_monitor import TrafficMonitor

def test_basic_communication():
    """Teste básico de comunicação entre um veículo e o monitor"""
    print("Iniciando teste básico do sistema DDS...")
    
    # Criar monitor
    print("Criando monitor de tráfego...")
    monitor = TrafficMonitor()
    monitor.start_monitoring()
    
    # Aguardar monitor se estabelecer
    time.sleep(2)
    
    # Criar veículo de teste
    print("Criando veículo de teste...")
    vehicle = VehiclePublisher("TEST_VEHICLE_001")
    
    # Aguardar descoberta DDS
    time.sleep(2)
    
    print("Enviando dados de teste...")
    
    # Enviar alguns dados de teste
    for i in range(10):
        vehicle.publish_data()
        time.sleep(1)
        print(f"   Dados enviados: {i+1}/10")
    
    print("Teste básico concluído")
    
    # Aguardar processamento final
    time.sleep(2)
    
    # Mostrar estatísticas finais
    monitor.print_statistics()
    
    # Limpeza
    print("Limpando recursos...")
    vehicle.cleanup()
    monitor.cleanup()
    
    print("Teste básico finalizado com sucesso!")

def test_installation():
    """Testa se todas as dependências estão instaladas corretamente"""
    print("Verificando instalação...")
    
    try:
        import cyclonedds
        print("OK - Cyclone DDS Python: OK")
    except ImportError:
        print("ERRO - Cyclone DDS Python: NÃO INSTALADO")
        print("   Execute: pip install cyclonedds-nightly")
        return False
    
    try:
        from cyclonedds.domain import DomainParticipant
        print("OK - Cyclone DDS Core: OK")
    except ImportError:
        print("ERRO - Cyclone DDS Core: ERRO")
        return False
    
    try:
        # Teste básico de criação de participante
        participant = DomainParticipant()
        print("OK - DDS Domain Participant: OK")
    except Exception as e:
        print(f"ERRO - DDS Domain Participant: ERRO - {e}")
        return False
    
    print("OK - Todas as dependências estão instaladas corretamente!")
    return True

def main():
    print("=" * 60)
    print("TESTE BÁSICO DO SISTEMA DE MONITORAMENTO DE FROTA")
    print("=" * 60)
    
    # Verificar instalação
    if not test_installation():
        print("\nERRO - Falha na verificação de instalação. Corrija os problemas antes de continuar.")
        return
    
    print("\n" + "=" * 60)
    
    try:
        # Executar teste básico
        test_basic_communication()
        
    except KeyboardInterrupt:
        print("\nTeste interrompido pelo usuário")
    except Exception as e:
        print(f"\nERRO - Erro durante o teste: {e}")
        print("\nVerifique se:")
        print("- O Cyclone DDS está instalado corretamente")
        print("- Não há outros processos DDS conflitantes")
        print("- Você tem permissões adequadas")
    
    print("\n" + "=" * 60)
    print("TESTE FINALIZADO")
    print("=" * 60)

if __name__ == "__main__":
    main()