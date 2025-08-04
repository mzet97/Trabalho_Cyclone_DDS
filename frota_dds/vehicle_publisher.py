#!/usr/bin/env python3
# vehicle_publisher.py - Publicador de dados de veículos

import time
import random
import math
from cyclonedds.domain import DomainParticipant, Topic
from cyclonedds.pub import DataWriter
from cyclonedds.core import Qos, Policy
from cyclonedds.util import duration
from cyclonedds.idl import IdlStruct
from dataclasses import dataclass
from typing import Optional

# Definição da estrutura de dados do veículo usando IdlStruct
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

class VehiclePublisher:
    def __init__(self, vehicle_id):
        self.vehicle_id = vehicle_id
        
        # Criar participante DDS
        self.participant = DomainParticipant()
        
        # Criar tópico
        self.topic = Topic(self.participant, "VehicleData", VehicleData)
        
        # Criar writer
        self.writer = DataWriter(self.participant, self.topic)
        
        # Posição inicial (simulada)
        self.current_lat = -23.5505 + random.uniform(-0.1, 0.1)  # São Paulo
        self.current_lon = -46.6333 + random.uniform(-0.1, 0.1)
        self.current_speed = 0.0
        self.fuel_level = 100.0
        
        print(f"Veículo {self.vehicle_id} iniciado")
    
    def simulate_movement(self):
        """Simula movimento do veículo"""
        # Simular mudança de velocidade
        speed_change = random.uniform(-5, 5)
        self.current_speed = max(0, min(120, self.current_speed + speed_change))
        
        # Simular movimento baseado na velocidade
        if self.current_speed > 0:
            # Converter velocidade para mudança de coordenadas (aproximação simples)
            lat_change = (self.current_speed / 111000) * random.uniform(-1, 1) * 0.01
            lon_change = (self.current_speed / 111000) * random.uniform(-1, 1) * 0.01
            
            self.current_lat += lat_change
            self.current_lon += lon_change
        
        # Simular consumo de combustível
        fuel_consumption = self.current_speed * 0.001 + random.uniform(0, 0.1)
        self.fuel_level = max(0, self.fuel_level - fuel_consumption)
    
    def get_status(self):
        """Determina o status do veículo"""
        if self.fuel_level < 10:
            return "LOW_FUEL"
        elif self.current_speed > 100:
            return "SPEEDING"
        elif self.current_speed == 0:
            return "STOPPED"
        else:
            return "OK"
    
    def publish_data(self):
        """Publica dados do veículo"""
        # Simular movimento
        self.simulate_movement()
        
        # Criar dados do veículo
        position = Position(self.current_lat, self.current_lon, 0.0)
        
        vehicle_data = VehicleData(
            vehicle_id=self.vehicle_id,
            position=position,
            speed=self.current_speed,
            fuel_level=self.fuel_level,
            status=self.get_status(),
            timestamp=int(time.time() * 1000)  # timestamp em milissegundos
        )
        
        # Publicar dados
        self.writer.write(vehicle_data)
        
        print(f"[{self.vehicle_id}] Pos: ({position.latitude:.6f}, {position.longitude:.6f}), "
              f"Velocidade: {self.current_speed:.1f} km/h, Combustível: {self.fuel_level:.1f}%, "
              f"Status: {vehicle_data.status}")
    
    def run(self, duration_seconds=60, publish_interval=2):
        """Executa a simulação por um período determinado"""
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration_seconds:
                self.publish_data()
                time.sleep(publish_interval)
        except KeyboardInterrupt:
            print(f"\nSimulação do veículo {self.vehicle_id} interrompida")
        
        print(f"Simulação do veículo {self.vehicle_id} finalizada")
    
    def cleanup(self):
        """Limpa recursos DDS"""
        pass

def main():
    import sys
    
    # Obter ID do veículo dos argumentos ou usar padrão
    vehicle_id = sys.argv[1] if len(sys.argv) > 1 else f"VEHICLE_{random.randint(1000, 9999)}"
    
    # Criar e executar publicador
    publisher = VehiclePublisher(vehicle_id)
    
    try:
        publisher.run(duration_seconds=300, publish_interval=1)  # 5 minutos, 1 segundo de intervalo
    finally:
        publisher.cleanup()

if __name__ == "__main__":
    main()