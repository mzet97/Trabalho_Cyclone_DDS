#!/usr/bin/env python3
# traffic_monitor.py - Monitor de tráfego para receber dados dos veículos

import time
import threading
from collections import defaultdict, deque
from cyclonedds.domain import DomainParticipant, Topic
from cyclonedds.sub import DataReader
from cyclonedds.core import Qos, Policy
from cyclonedds.util import duration
from cyclonedds.idl import IdlStruct
from dataclasses import dataclass
from typing import Optional

# Definição da estrutura de dados do veículo (mesma do publisher)
@dataclass
class Position(IdlStruct):
    latitude: float = 0.0
    longitude: float = 0.0
    altitude: float = 0.0

@dataclass
class VehicleData(IdlStruct):
    vehicle_id: str = ""
    position: Position = None
    speed: float = 0.0
    fuel_level: float = 100.0
    status: str = "OK"
    timestamp: int = 0
    
    def __post_init__(self):
        if self.position is None:
            self.position = Position()

class TrafficMonitor:
    def __init__(self):
        # Criar participante DDS
        self.participant = DomainParticipant()
        
        # Criar tópico
        self.topic = Topic(self.participant, "VehicleData", VehicleData)
        
        # Criar reader
        self.reader = DataReader(self.participant, self.topic)
        
        # Armazenamento de dados dos veículos
        self.vehicle_data = defaultdict(lambda: deque(maxlen=100))  # Últimas 100 leituras por veículo
        self.vehicle_last_seen = {}
        self.alerts = deque(maxlen=1000)  # Últimos 1000 alertas
        
        # Controle de execução
        self.running = False
        self.monitor_thread = None
        
        print("Monitor de Tráfego iniciado")
    
    def process_vehicle_data(self, data):
        """Processa dados recebidos de um veículo"""
        vehicle_id = data.vehicle_id
        current_time = time.time()
        
        # Armazenar dados
        self.vehicle_data[vehicle_id].append(data)
        self.vehicle_last_seen[vehicle_id] = current_time
        
        # Verificar alertas
        self.check_alerts(data)
        
        # Log dos dados recebidos
        print(f"[RECEBIDO] {vehicle_id}: Pos({data.position.latitude:.6f}, {data.position.longitude:.6f}), "
              f"Velocidade: {data.speed:.1f} km/h, Combustível: {data.fuel_level:.1f}%, Status: {data.status}")
    
    def check_alerts(self, data):
        """Verifica condições de alerta"""
        alerts = []
        
        # Alerta de combustível baixo
        if data.fuel_level < 15:
            alert = f"ALERTA: Veículo {data.vehicle_id} com combustível baixo ({data.fuel_level:.1f}%)"
            alerts.append(alert)
        
        # Alerta de velocidade excessiva
        if data.speed > 90:
            alert = f"ALERTA: Veículo {data.vehicle_id} em alta velocidade ({data.speed:.1f} km/h)"
            alerts.append(alert)
        
        # Alerta de status crítico
        if data.status in ["LOW_FUEL", "EMERGENCY", "BREAKDOWN"]:
            alert = f"ALERTA: Veículo {data.vehicle_id} com status crítico: {data.status}"
            alerts.append(alert)
        
        # Armazenar e exibir alertas
        for alert in alerts:
            self.alerts.append((time.time(), alert))
            print(f"ALERTA: {alert}")
    
    def check_offline_vehicles(self):
        """Verifica veículos que não enviam dados há muito tempo"""
        current_time = time.time()
        offline_threshold = 30  # 30 segundos
        
        for vehicle_id, last_seen in list(self.vehicle_last_seen.items()):
            if current_time - last_seen > offline_threshold:
                alert = f"ALERTA: Veículo {vehicle_id} offline há {int(current_time - last_seen)} segundos"
                self.alerts.append((current_time, alert))
                print(f"OFFLINE: {alert}")
                # Remove da lista para evitar spam de alertas
                del self.vehicle_last_seen[vehicle_id]
    
    def get_fleet_statistics(self):
        """Calcula estatísticas da frota"""
        if not self.vehicle_data:
            return None
        
        total_vehicles = len(self.vehicle_data)
        active_vehicles = len(self.vehicle_last_seen)
        
        # Calcular médias dos veículos ativos
        speeds = []
        fuel_levels = []
        status_counts = defaultdict(int)
        
        for vehicle_id, data_history in self.vehicle_data.items():
            if data_history and vehicle_id in self.vehicle_last_seen:
                latest_data = data_history[-1]
                speeds.append(latest_data.speed)
                fuel_levels.append(latest_data.fuel_level)
                status_counts[latest_data.status] += 1
        
        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        avg_fuel = sum(fuel_levels) / len(fuel_levels) if fuel_levels else 0
        
        return {
            'total_vehicles': total_vehicles,
            'active_vehicles': active_vehicles,
            'avg_speed': avg_speed,
            'avg_fuel': avg_fuel,
            'status_distribution': dict(status_counts)
        }
    
    def print_statistics(self):
        """Imprime estatísticas da frota"""
        stats = self.get_fleet_statistics()
        if stats:
            print("\n" + "="*60)
            print("ESTATÍSTICAS DA FROTA")
            print("="*60)
            print(f"Total de veículos registrados: {stats['total_vehicles']}")
            print(f"Veículos ativos: {stats['active_vehicles']}")
            print(f"Velocidade média: {stats['avg_speed']:.1f} km/h")
            print(f"Nível médio de combustível: {stats['avg_fuel']:.1f}%")
            print("Distribuição de status:")
            for status, count in stats['status_distribution'].items():
                print(f"  {status}: {count} veículos")
            print(f"Total de alertas: {len(self.alerts)}")
            print("="*60 + "\n")
    
    def monitor_loop(self):
        """Loop principal de monitoramento"""
        last_stats_time = time.time()
        last_offline_check = time.time()
        
        while self.running:
            try:
                # Ler dados disponíveis
                samples = self.reader.take()
                
                for sample in samples:
                    if sample is not None:
                        self.process_vehicle_data(sample)
                
                # Verificar veículos offline periodicamente
                current_time = time.time()
                if current_time - last_offline_check > 15:  # A cada 15 segundos
                    self.check_offline_vehicles()
                    last_offline_check = current_time
                
                # Imprimir estatísticas periodicamente
                if current_time - last_stats_time > 30:  # A cada 30 segundos
                    self.print_statistics()
                    last_stats_time = current_time
                
                time.sleep(0.1)  # Pequena pausa para evitar uso excessivo de CPU
                
            except Exception as e:
                print(f"Erro no loop de monitoramento: {e}")
                time.sleep(1)
    
    def start_monitoring(self):
        """Inicia o monitoramento em thread separada"""
        if not self.running:
            self.running = True
            self.monitor_thread = threading.Thread(target=self.monitor_loop)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            print("Monitoramento iniciado...")
    
    def stop_monitoring(self):
        """Para o monitoramento"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("Monitoramento parado")
    
    def cleanup(self):
        """Limpa recursos DDS"""
        self.stop_monitoring()

def main():
    monitor = TrafficMonitor()
    
    try:
        monitor.start_monitoring()
        
        print("Monitor de Tráfego ativo. Pressione Ctrl+C para parar...")
        print("Aguardando dados dos veículos...\n")
        
        # Manter o programa rodando
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nParando monitor de tráfego...")
    finally:
        monitor.cleanup()
        print("Monitor de tráfego finalizado")

if __name__ == "__main__":
    main()