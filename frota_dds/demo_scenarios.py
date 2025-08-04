#!/usr/bin/env python3
# demo_scenarios.py - Cenários de demonstração específicos

import time
import random
import threading
from vehicle_publisher import VehiclePublisher
from traffic_monitor import TrafficMonitor

class DemoScenarios:
    def __init__(self):
        self.monitor = None
        self.vehicles = []
        self.running = False
    
    def setup_monitor(self):
        """Configura e inicia o monitor"""
        self.monitor = TrafficMonitor()
        self.monitor.start_monitoring()
        time.sleep(2)  # Aguardar inicialização
    
    def cleanup(self):
        """Limpa recursos"""
        self.running = False
        
        for vehicle in self.vehicles:
            try:
                vehicle.cleanup()
            except:
                pass
        
        if self.monitor:
            self.monitor.cleanup()
        
        self.vehicles = []
    
    def scenario_emergency_response(self):
        """Cenário: Resposta a emergência"""
        print("\nCENÁRIO: RESPOSTA A EMERGÊNCIA")
        print("=" * 50)
        print("Simulando situação de emergência com múltiplos veículos")
        print("Veículos de emergência se dirigem ao local do incidente")
        
        self.setup_monitor()
        
        # Criar veículos de emergência
        emergency_vehicles = [
            ("AMBULANCE_001", -23.5505, -46.6333, 80),
            ("FIRE_TRUCK_001", -23.5515, -46.6343, 70),
            ("POLICE_001", -23.5495, -46.6323, 90),
            ("RESCUE_001", -23.5525, -46.6353, 75)
        ]
        
        # Local da emergência
        emergency_lat, emergency_lon = -23.5500, -46.6330
        
        for vehicle_id, start_lat, start_lon, speed in emergency_vehicles:
            vehicle = VehiclePublisher(vehicle_id)
            vehicle.current_lat = start_lat
            vehicle.current_lon = start_lon
            vehicle.current_speed = speed
            vehicle.fuel_level = random.uniform(70, 100)
            self.vehicles.append(vehicle)
        
        print(f"\nLocal da emergência: ({emergency_lat}, {emergency_lon})")
        print("Veículos de emergência despachados")
        
        # Simular convergência para o local da emergência
        for step in range(30):
            for vehicle in self.vehicles:
                # Mover em direção à emergência
                lat_diff = emergency_lat - vehicle.current_lat
                lon_diff = emergency_lon - vehicle.current_lon
                
                # Movimento gradual em direção ao destino
                vehicle.current_lat += lat_diff * 0.1
                vehicle.current_lon += lon_diff * 0.1
                
                # Ajustar velocidade baseado na distância
                distance = abs(lat_diff) + abs(lon_diff)
                if distance < 0.001:
                    vehicle.current_speed = 0  # Chegou ao destino
                    vehicle.status = "ARRIVED"
                else:
                    vehicle.current_speed = min(100, vehicle.current_speed + random.uniform(-5, 5))
                
                vehicle.publish_data()
            
            time.sleep(1)
            
            if step % 10 == 0:
                print(f"Tempo decorrido: {step} segundos")
        
        print("\nCenário de emergência concluído")
        self.monitor.print_statistics()
    
    def scenario_traffic_jam(self):
        """Cenário: Congestionamento de tráfego"""
        print("\nCENÁRIO: CONGESTIONAMENTO DE TRÁFEGO")
        print("=" * 50)
        print("Simulando congestionamento com redução gradual de velocidade")
        
        self.setup_monitor()
        
        # Criar veículos em uma via congestionada
        for i in range(8):
            vehicle_id = f"CAR_{i+1:03d}"
            vehicle = VehiclePublisher(vehicle_id)
            
            # Posicionar veículos em linha
            vehicle.current_lat = -23.5500 + (i * 0.001)
            vehicle.current_lon = -46.6330
            vehicle.current_speed = random.uniform(60, 80)
            vehicle.fuel_level = random.uniform(40, 90)
            
            self.vehicles.append(vehicle)
        
        print("8 veículos posicionados na via")
        print("Simulando formação de congestionamento...")
        
        # Simular congestionamento progressivo
        for step in range(60):
            congestion_factor = min(1.0, step / 30.0)  # Congestionamento aumenta gradualmente
            
            for i, vehicle in enumerate(self.vehicles):
                # Veículos da frente param primeiro
                if i < 3:  # Primeiros veículos
                    target_speed = 80 * (1 - congestion_factor)
                elif i < 6:  # Veículos do meio
                    target_speed = 60 * (1 - congestion_factor * 0.8)
                else:  # Últimos veículos
                    target_speed = 40 * (1 - congestion_factor * 0.6)
                
                # Ajustar velocidade gradualmente
                speed_diff = target_speed - vehicle.current_speed
                vehicle.current_speed += speed_diff * 0.1
                vehicle.current_speed = max(0, vehicle.current_speed)
                
                # Movimento baseado na velocidade
                if vehicle.current_speed > 0:
                    vehicle.current_lat += (vehicle.current_speed / 111000) * 0.01
                
                vehicle.publish_data()
            
            time.sleep(0.5)
            
            if step % 15 == 0:
                avg_speed = sum(v.current_speed for v in self.vehicles) / len(self.vehicles)
                print(f"Tempo {step//2}s - Velocidade média: {avg_speed:.1f} km/h")
        
        print("\nCenário de congestionamento concluído")
        self.monitor.print_statistics()
    
    def scenario_fuel_crisis(self):
        """Cenário: Crise de combustível"""
        print("\nCENÁRIO: CRISE DE COMBUSTÍVEL")
        print("=" * 50)
        print("Simulando veículos com baixo combustível buscando postos")
        
        self.setup_monitor()
        
        # Criar veículos com combustível baixo
        vehicle_configs = [
            ("DELIVERY_001", 15.0),
            ("TAXI_001", 8.0),
            ("BUS_001", 12.0),
            ("TRUCK_001", 5.0),
            ("VAN_001", 18.0)
        ]
        
        # Posições de postos de combustível
        gas_stations = [
            (-23.5510, -46.6340),
            (-23.5490, -46.6320),
            (-23.5520, -46.6350)
        ]
        
        for vehicle_id, fuel_level in vehicle_configs:
            vehicle = VehiclePublisher(vehicle_id)
            vehicle.current_lat = -23.5500 + random.uniform(-0.01, 0.01)
            vehicle.current_lon = -46.6330 + random.uniform(-0.01, 0.01)
            vehicle.current_speed = random.uniform(30, 60)
            vehicle.fuel_level = fuel_level
            self.vehicles.append(vehicle)
        
        print(f"{len(self.vehicles)} veículos com combustível baixo")
        print(f"{len(gas_stations)} postos de combustível disponíveis")
        
        # Simular busca por combustível
        for step in range(90):
            for vehicle in self.vehicles:
                # Se combustível muito baixo, ir para posto mais próximo
                if vehicle.fuel_level < 20:
                    # Encontrar posto mais próximo
                    closest_station = min(gas_stations, 
                        key=lambda station: abs(station[0] - vehicle.current_lat) + 
                                          abs(station[1] - vehicle.current_lon))
                    
                    # Mover em direção ao posto
                    lat_diff = closest_station[0] - vehicle.current_lat
                    lon_diff = closest_station[1] - vehicle.current_lon
                    
                    vehicle.current_lat += lat_diff * 0.05
                    vehicle.current_lon += lon_diff * 0.05
                    
                    # Verificar se chegou ao posto
                    distance = abs(lat_diff) + abs(lon_diff)
                    if distance < 0.0005:
                        vehicle.fuel_level = min(100, vehicle.fuel_level + 10)  # Abastecer
                        if vehicle.fuel_level > 80:
                            print(f"{vehicle.vehicle_id} abasteceu com sucesso!")
                else:
                    # Movimento normal
                    vehicle.simulate_movement()
                
                vehicle.publish_data()
            
            time.sleep(0.3)
            
            if step % 20 == 0:
                low_fuel_count = sum(1 for v in self.vehicles if v.fuel_level < 20)
                print(f"Tempo {step//3}s - Veículos com combustível baixo: {low_fuel_count}")
        
        print("\nCenário de crise de combustível concluído")
        self.monitor.print_statistics()
    
    def scenario_rush_hour(self):
        """Cenário: Hora do rush"""
        print("\nCENÁRIO: HORA DO RUSH")
        print("=" * 50)
        print("Simulando tráfego intenso durante horário de pico")
        
        self.setup_monitor()
        
        # Criar muitos veículos para simular hora do rush
        vehicle_types = ["CAR", "BUS", "MOTORCYCLE", "VAN", "TRUCK"]
        
        for i in range(15):
            vehicle_type = random.choice(vehicle_types)
            vehicle_id = f"{vehicle_type}_{i+1:03d}"
            
            vehicle = VehiclePublisher(vehicle_id)
            
            # Distribuir veículos em área metropolitana
            vehicle.current_lat = -23.5500 + random.uniform(-0.02, 0.02)
            vehicle.current_lon = -46.6330 + random.uniform(-0.02, 0.02)
            
            # Velocidades típicas de hora do rush
            if vehicle_type == "MOTORCYCLE":
                vehicle.current_speed = random.uniform(20, 70)  # Mais ágeis
            elif vehicle_type == "BUS":
                vehicle.current_speed = random.uniform(15, 40)  # Mais lentos
            else:
                vehicle.current_speed = random.uniform(10, 50)  # Tráfego lento
            
            vehicle.fuel_level = random.uniform(30, 95)
            self.vehicles.append(vehicle)
        
        print(f"{len(self.vehicles)} veículos no tráfego")
        print("Monitorando padrões de tráfego...")
        
        # Simular padrões de hora do rush
        for step in range(120):
            # Simular ondas de tráfego
            wave_factor = abs(math.sin(step * 0.1)) * 0.5 + 0.5
            
            for vehicle in self.vehicles:
                # Ajustar velocidade baseado na "onda" de tráfego
                base_speed = 30 if "BUS" in vehicle.vehicle_id else 45
                target_speed = base_speed * wave_factor
                
                # Variação aleatória
                target_speed += random.uniform(-10, 10)
                target_speed = max(0, min(80, target_speed))
                
                # Ajuste gradual de velocidade
                speed_diff = target_speed - vehicle.current_speed
                vehicle.current_speed += speed_diff * 0.2
                
                # Movimento e consumo de combustível
                vehicle.simulate_movement()
                vehicle.publish_data()
            
            time.sleep(0.2)
            
            if step % 30 == 0:
                avg_speed = sum(v.current_speed for v in self.vehicles) / len(self.vehicles)
                print(f"Tempo {step//5}s - Velocidade média: {avg_speed:.1f} km/h")
        
        print("\nCenário de hora do rush concluído")
        self.monitor.print_statistics()

def main():
    import math
    
    demo = DemoScenarios()
    
    scenarios = {
        '1': ('Resposta a Emergência', demo.scenario_emergency_response),
        '2': ('Congestionamento de Tráfego', demo.scenario_traffic_jam),
        '3': ('Crise de Combustível', demo.scenario_fuel_crisis),
        '4': ('Hora do Rush', demo.scenario_rush_hour)
    }
    
    print("CENÁRIOS DE DEMONSTRAÇÃO - CYCLONE DDS")
    print("=" * 60)
    
    while True:
        print("\nCenários disponíveis:")
        for key, (name, _) in scenarios.items():
            print(f"{key}. {name}")
        print("5. Executar todos os cenários")
        print("6. Sair")
        
        choice = input("\nEscolha um cenário (1-6): ").strip()
        
        try:
            if choice in scenarios:
                name, func = scenarios[choice]
                print(f"\nExecutando: {name}")
                func()
                demo.cleanup()
                input("\nPressione Enter para continuar...")
            
            elif choice == '5':
                print("\nExecutando todos os cenários...")
                for key in sorted(scenarios.keys()):
                    name, func = scenarios[key]
                    print(f"\nExecutando: {name}")
                    func()
                    demo.cleanup()
                    time.sleep(2)
                print("\nTodos os cenários concluídos!")
            
            elif choice == '6':
                print("\nEncerrando demonstração...")
                break
            
            else:
                print("Opção inválida")
        
        except KeyboardInterrupt:
            print("\nCenário interrompido")
            demo.cleanup()
        except Exception as e:
            print(f"Erro no cenário: {e}")
            demo.cleanup()
    
    demo.cleanup()
    print("Demonstração finalizada")

if __name__ == "__main__":
    main()