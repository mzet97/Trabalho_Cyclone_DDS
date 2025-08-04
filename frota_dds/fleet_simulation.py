#!/usr/bin/env python3
# fleet_simulation.py - Simulação completa da frota com múltiplos veículos

import time
import threading
import random
import signal
import sys
from concurrent.futures import ThreadPoolExecutor

# Importar classes dos outros módulos
from vehicle_publisher import VehiclePublisher
from traffic_monitor import TrafficMonitor

class FleetSimulation:
    def __init__(self, num_vehicles=5):
        self.num_vehicles = num_vehicles
        self.vehicles = []
        self.monitor = None
        self.running = False
        self.executor = None
        
        # Configurar handler para interrupção
        signal.signal(signal.SIGINT, self.signal_handler)
        
        print(f"Iniciando simulação com {num_vehicles} veículos")
    
    def signal_handler(self, signum, frame):
        """Handler para interrupção do programa"""
        print("\nRecebido sinal de interrupção. Parando simulação...")
        self.stop_simulation()
        sys.exit(0)
    
    def create_vehicles(self):
        """Cria instâncias dos veículos"""
        vehicle_types = ["TRUCK", "VAN", "CAR", "BUS", "MOTORCYCLE"]
        
        for i in range(self.num_vehicles):
            vehicle_type = random.choice(vehicle_types)
            vehicle_id = f"{vehicle_type}_{i+1:03d}"
            
            vehicle = VehiclePublisher(vehicle_id)
            
            # Personalizar características do veículo baseado no tipo
            if vehicle_type == "TRUCK":
                vehicle.current_speed = random.uniform(40, 80)
                vehicle.fuel_level = random.uniform(60, 100)
            elif vehicle_type == "BUS":
                vehicle.current_speed = random.uniform(30, 60)
                vehicle.fuel_level = random.uniform(50, 90)
            elif vehicle_type == "MOTORCYCLE":
                vehicle.current_speed = random.uniform(20, 100)
                vehicle.fuel_level = random.uniform(30, 80)
            else:  # CAR, VAN
                vehicle.current_speed = random.uniform(30, 90)
                vehicle.fuel_level = random.uniform(40, 95)
            
            self.vehicles.append(vehicle)
            print(f"Veículo criado: {vehicle_id}")
    
    def vehicle_worker(self, vehicle, duration):
        """Worker function para executar um veículo em thread separada"""
        try:
            # Intervalo de publicação aleatório para cada veículo
            publish_interval = random.uniform(0.5, 2.0)
            vehicle.run(duration_seconds=duration, publish_interval=publish_interval)
        except Exception as e:
            print(f"Erro no veículo {vehicle.vehicle_id}: {e}")
        finally:
            vehicle.cleanup()
    
    def start_simulation(self, duration_minutes=10):
        """Inicia a simulação completa"""
        duration_seconds = duration_minutes * 60
        
        print(f"\nIniciando simulação por {duration_minutes} minutos...")
        
        # Criar veículos
        self.create_vehicles()
        
        # Aguardar um pouco para os veículos se estabelecerem
        time.sleep(2)
        
        # Iniciar monitor de tráfego
        self.monitor = TrafficMonitor()
        self.monitor.start_monitoring()
        
        # Aguardar um pouco para o monitor se estabelecer
        time.sleep(2)
        
        print("\nSimulação iniciada!")
        print("Monitor de tráfego ativo")
        print(f"{len(self.vehicles)} veículos em operação")
        print("\nPressione Ctrl+C para parar a simulação\n")
        
        # Iniciar veículos em threads separadas
        self.running = True
        self.executor = ThreadPoolExecutor(max_workers=self.num_vehicles)
        
        # Submeter tarefas dos veículos
        futures = []
        for vehicle in self.vehicles:
            future = self.executor.submit(self.vehicle_worker, vehicle, duration_seconds)
            futures.append(future)
        
        try:
            # Aguardar conclusão ou interrupção
            start_time = time.time()
            while self.running and time.time() - start_time < duration_seconds:
                time.sleep(1)
                
                # Verificar se algum veículo terminou prematuramente
                active_vehicles = sum(1 for f in futures if not f.done())
                if active_vehicles == 0:
                    print("\nTodos os veículos finalizaram")
                    break
            
            if time.time() - start_time >= duration_seconds:
                print(f"\nSimulação completada após {duration_minutes} minutos")
            
        except KeyboardInterrupt:
            print("\nSimulação interrompida pelo usuário")
        
        finally:
            self.stop_simulation()
    
    def stop_simulation(self):
        """Para a simulação e limpa recursos"""
        if not self.running:
            return
        
        print("\nParando simulação...")
        self.running = False
        
        # Parar executor
        if self.executor:
            self.executor.shutdown(wait=False)
        
        # Parar monitor
        if self.monitor:
            self.monitor.cleanup()
        
        # Limpar veículos
        for vehicle in self.vehicles:
            try:
                vehicle.cleanup()
            except:
                pass
        
        print("Simulação finalizada")
    
    def run_demo_scenarios(self):
        """Executa cenários de demonstração"""
        scenarios = [
            {
                'name': 'Frota Pequena',
                'vehicles': 3,
                'duration': 2
            },
            {
                'name': 'Frota Média',
                'vehicles': 7,
                'duration': 3
            },
            {
                'name': 'Frota Grande',
                'vehicles': 15,
                'duration': 5
            }
        ]
        
        print("=" * 60)
        print("DEMONSTRAÇÃO DE CENÁRIOS DE FROTA")
        print("=" * 60)
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\nCenário {i}: {scenario['name']}")
            print(f"   Veículos: {scenario['vehicles']}")
            print(f"   Duração: {scenario['duration']} minutos")
            
            input("\nPressione Enter para iniciar este cenário...")
            
            # Recriar simulação para o cenário
            self.num_vehicles = scenario['vehicles']
            self.vehicles = []
            
            self.start_simulation(duration_minutes=scenario['duration'])
            
            if i < len(scenarios):
                print(f"\nCenário {i} concluído")
                time.sleep(2)
        
        print("\nTodos os cenários de demonstração concluídos!")

def print_menu():
    """Imprime o menu de opções"""
    print("\n" + "=" * 50)
    print("SIMULAÇÃO DE FROTA COM CYCLONE DDS")
    print("=" * 50)
    print("1. Simulação rápida (3 veículos, 2 minutos)")
    print("2. Simulação padrão (5 veículos, 5 minutos)")
    print("3. Simulação extendida (10 veículos, 10 minutos)")
    print("4. Simulação personalizada")
    print("5. Demonstração de cenários")
    print("6. Sair")
    print("=" * 50)

def main():
    print("Sistema de Monitoramento de Frota com Cyclone DDS")
    print("Implementação prática do trabalho acadêmico\n")
    
    while True:
        print_menu()
        
        try:
            choice = input("Escolha uma opção (1-6): ").strip()
            
            if choice == '1':
                simulation = FleetSimulation(num_vehicles=3)
                simulation.start_simulation(duration_minutes=2)
            
            elif choice == '2':
                simulation = FleetSimulation(num_vehicles=5)
                simulation.start_simulation(duration_minutes=5)
            
            elif choice == '3':
                simulation = FleetSimulation(num_vehicles=10)
                simulation.start_simulation(duration_minutes=10)
            
            elif choice == '4':
                num_vehicles = int(input("Número de veículos (1-20): "))
                duration = int(input("Duração em minutos (1-30): "))
                
                if 1 <= num_vehicles <= 20 and 1 <= duration <= 30:
                    simulation = FleetSimulation(num_vehicles=num_vehicles)
                    simulation.start_simulation(duration_minutes=duration)
                else:
                    print("ERRO - Valores inválidos. Tente novamente.")
            
            elif choice == '5':
                simulation = FleetSimulation()
                simulation.run_demo_scenarios()
            
            elif choice == '6':
                print("Encerrando programa...")
                break
            
            else:
                print("ERRO - Opção inválida. Tente novamente.")
        
        except ValueError:
            print("ERRO - Entrada inválida. Digite um número.")
        except KeyboardInterrupt:
            print("\nPrograma interrompido pelo usuário")
            break
        except Exception as e:
            print(f"ERRO - Erro inesperado: {e}")
    
    print("Programa finalizado")

if __name__ == "__main__":
    main()