#!/usr/bin/env python3
"""
Cliente RTT usando Eclipse Cyclone DDS

Este cliente:
1. Envia requisições RTTRequest com diferentes tamanhos de payload
2. Mede o Round-Trip Time (RTT) localmente
3. Realiza aquecimento antes das medições
4. Salva resultados em arquivo CSV
"""

import time
import csv
import argparse
import sys
import uuid
from datetime import datetime
from typing import List, Tuple
from cyclonedds.domain import DomainParticipant
from cyclonedds.core import Qos, Policy
from cyclonedds.pub import DataWriter
from cyclonedds.sub import DataReader
from cyclonedds.topic import Topic
from cyclonedds.util import duration

from rtt_types import RTTRequest, RTTResponse, create_payload, validate_payload


class RTTClient:
    """
    Cliente para medição de RTT usando DDS.
    
    Envia requisições e mede o tempo de resposta para diferentes
    tamanhos de payload.
    """
    
    def __init__(self, client_id: str = "client1", domain_id: int = 0, timeout_ms: int = 5000):
        """
        Inicializa o cliente RTT.
        
        Args:
            client_id: Identificador único do cliente
            domain_id: ID do domínio DDS (padrão: 0)
            timeout_ms: Timeout para respostas em milissegundos
        """
        self.client_id = client_id
        self.domain_id = domain_id
        self.timeout_ms = timeout_ms
        self.request_id = 0
        
        # Tamanhos de payload em potências de dois (2^0 até 2^17)
        self.payload_sizes = [
            2**i for i in range(18)  # 2^0 até 2^17: 1, 2, 4, 8, ..., 131072
        ]
        
        # Configuração de QoS para baixa latência
        self.qos = Qos(
            Policy.Reliability.Reliable(duration(seconds=10)),
            Policy.Durability.Volatile,
            Policy.History.KeepLast(1),
            Policy.ResourceLimits(max_samples=1000),
            Policy.Deadline(duration(milliseconds=100))
        )
        
        self._setup_dds()
        self._setup_csv()
        
    def _setup_dds(self):
        """
        Configura participante DDS, tópicos, escritor e leitor.
        """
        print(f"Inicializando cliente {self.client_id} no domínio {self.domain_id}...")
        
        # Criação do participante DDS
        self.participant = DomainParticipant(self.domain_id)
        
        # Criação dos tópicos
        self.request_topic = Topic(self.participant, "RTTRequest", RTTRequest)
        self.response_topic = Topic(self.participant, "RTTResponse", RTTResponse)
        
        # Criação do escritor para requisições
        self.request_writer = DataWriter(self.participant, self.request_topic, qos=self.qos)
        
        # Criação do leitor para respostas
        self.response_reader = DataReader(self.participant, self.response_topic, qos=self.qos)
        
        print("Cliente configurado com sucesso!")
        
    def _setup_csv(self):
        """
        Configura arquivo CSV para salvar resultados.
        """
        # Usa timestamp com microssegundos e UUID para evitar conflitos em execução concorrente
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        microseconds = now.microsecond
        unique_id = str(uuid.uuid4())[:8]  # Primeiros 8 caracteres do UUID
        self.csv_filename = f"rtt_{self.client_id}_{timestamp}_{microseconds:06d}_{unique_id}.csv"
        
        # Cria arquivo CSV com cabeçalho
        with open(self.csv_filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['size', 'iteration', 'rtt_us'])
            
        print(f"Arquivo de resultados: {self.csv_filename}")
        
    def _get_next_request_id(self) -> int:
        """
        Gera próximo ID de requisição único.
        
        Returns:
            ID único para a requisição
        """
        self.request_id += 1
        return self.request_id
        
    def _send_request_and_measure(self, payload_size: int) -> float:
        """
        Envia uma requisição e mede o RTT.
        
        Args:
            payload_size: Tamanho do payload em bytes
            
        Returns:
            RTT em microssegundos, ou -1 em caso de timeout/erro
        """
        request_id = self._get_next_request_id()
        payload = create_payload(payload_size)
        
        # Cria requisição
        request = RTTRequest(id=request_id, data=payload)
        
        # Marca tempo antes do envio
        t0 = time.perf_counter()
        
        # Envia requisição
        self.request_writer.write(request)
        
        # Aguarda resposta com timeout
        timeout_start = time.time()
        while True:
            # Verifica timeout
            if (time.time() - timeout_start) * 1000 > self.timeout_ms:
                print(f"Timeout para requisição ID {request_id}")
                return -1
                
            # Lê respostas disponíveis
            samples = self.response_reader.take()
            
            for sample in samples:
                if hasattr(sample, 'sample_info') and sample.sample_info.valid_data:
                    response = sample
                    
                    # Verifica se é a resposta correta
                    if response.id == request_id:
                        # Marca tempo de recebimento
                        t1 = time.perf_counter()
                        
                        # Valida payload
                        if not validate_payload(payload, response.data):
                            print(f"Erro: Payload corrompido na resposta ID {request_id}")
                            return -1
                            
                        # Calcula RTT em microssegundos
                        rtt_us = (t1 - t0) * 1e6
                        return rtt_us
                        
            # Pequena pausa para evitar uso excessivo de CPU
            time.sleep(0.0001)  # 0.1ms
            
    def _warmup(self, payload_size: int, warmup_count: int = 50):
        """
        Realiza aquecimento enviando pacotes sem cronometrar.
        
        Args:
            payload_size: Tamanho do payload para aquecimento
            warmup_count: Número de pacotes de aquecimento
        """
        print(f"Aquecimento: {warmup_count} pacotes de {payload_size} bytes...")
        
        for i in range(warmup_count):
            self._send_request_and_measure(payload_size)
            
        print("Aquecimento concluído.")
        
    def _measure_rtt_series(self, payload_size: int, measurement_count: int = 1000) -> List[float]:
        """
        Realiza série de medições RTT para um tamanho de payload.
        
        Args:
            payload_size: Tamanho do payload em bytes
            measurement_count: Número de medições a realizar
            
        Returns:
            Lista de RTTs em microssegundos
        """
        print(f"Medindo RTT: {measurement_count} pacotes de {payload_size} bytes...")
        
        rtts = []
        successful_measurements = 0
        
        for i in range(measurement_count):
            rtt = self._send_request_and_measure(payload_size)
            
            if rtt > 0:  # Medição bem-sucedida
                rtts.append(rtt)
                successful_measurements += 1
                
                # Salva resultado no CSV imediatamente
                with open(self.csv_filename, 'a', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow([payload_size, i + 1, rtt])
                    
            # Progress feedback
            if (i + 1) % 100 == 0:
                success_rate = (successful_measurements / (i + 1)) * 100
                print(f"  Progresso: {i + 1}/{measurement_count} "
                      f"(Taxa de sucesso: {success_rate:.1f}%)")
                      
        print(f"Série concluída: {successful_measurements}/{measurement_count} "
              f"medições bem-sucedidas")
              
        return rtts
        
    def run_measurements(self):
        """
        Executa todas as medições RTT para diferentes tamanhos de payload.
        """
        print(f"\nIniciando medições RTT para cliente {self.client_id}")
        print(f"Tamanhos de payload: {self.payload_sizes}")
        print(f"Timeout: {self.timeout_ms}ms\n")
        
        total_measurements = 0
        
        for payload_size in self.payload_sizes:
            print(f"\n=== Payload Size: {payload_size} bytes ===")
            
            try:
                # Aquecimento
                self._warmup(payload_size)
                
                # Pequena pausa entre aquecimento e medições
                time.sleep(1)
                
                # Medições
                rtts = self._measure_rtt_series(payload_size)
                
                if rtts:
                    # Estatísticas básicas
                    min_rtt = min(rtts)
                    max_rtt = max(rtts)
                    avg_rtt = sum(rtts) / len(rtts)
                    
                    print(f"Estatísticas RTT:")
                    print(f"  Mínimo: {min_rtt:.2f} μs")
                    print(f"  Máximo: {max_rtt:.2f} μs")
                    print(f"  Média: {avg_rtt:.2f} μs")
                    
                    total_measurements += len(rtts)
                else:
                    print("Nenhuma medição bem-sucedida para este tamanho.")
                    
            except KeyboardInterrupt:
                print("\nInterrupção recebida. Parando medições...")
                break
            except Exception as e:
                print(f"Erro durante medições para payload {payload_size}: {e}")
                continue
                
        print(f"\nMedições concluídas. Total: {total_measurements} medições")
        print(f"Resultados salvos em: {self.csv_filename}")
        
    def cleanup(self):
        """
        Limpa recursos DDS adequadamente.
        """
        print("Limpando recursos DDS...")
        
        try:
            # No cyclonedds-nightly, os recursos são limpos automaticamente
            # quando o participante é destruído
            if hasattr(self, 'participant'):
                del self.participant
        except Exception as e:
            print(f"Erro durante limpeza: {e}")
            
        print("Cliente finalizado.")


def main():
    """
    Função principal do cliente.
    """
    parser = argparse.ArgumentParser(description="Cliente RTT usando Cyclone DDS")
    parser.add_argument("--client-id", default="client1", 
                       help="ID único do cliente (padrão: client1)")
    parser.add_argument("--domain-id", type=int, default=0,
                       help="ID do domínio DDS (padrão: 0)")
    parser.add_argument("--timeout", type=int, default=5000,
                       help="Timeout em milissegundos (padrão: 5000)")
    
    args = parser.parse_args()
    
    # Cria cliente
    client = RTTClient(
        client_id=args.client_id,
        domain_id=args.domain_id,
        timeout_ms=args.timeout
    )
    
    try:
        # Executa medições
        client.run_measurements()
    except KeyboardInterrupt:
        print("\nInterrupção recebida.")
    except Exception as e:
        print(f"Erro fatal no cliente: {e}")
    finally:
        client.cleanup()


if __name__ == "__main__":
    main()