#!/usr/bin/env python3
"""
Servidor Echo RTT usando Eclipse Cyclone DDS

Este servidor atua como um echo server que:
1. Recebe pacotes RTTRequest
2. Responde imediatamente com RTTResponse contendo o mesmo payload
3. Usa arquitetura publish/subscribe do DDS
"""

import time
import signal
import sys
import argparse
from cyclonedds.domain import DomainParticipant
from cyclonedds.core import Qos, Policy
from cyclonedds.pub import DataWriter
from cyclonedds.sub import DataReader
from cyclonedds.topic import Topic
from cyclonedds.util import duration

from rtt_types import RTTRequest, RTTResponse


class RTTEchoServer:
    """
    Servidor Echo para medição de RTT.
    
    Recebe mensagens RTTRequest e responde com RTTResponse
    contendo o mesmo payload e ID.
    """
    
    def __init__(self, domain_id: int = 0):
        """
        Inicializa o servidor echo.
        
        Args:
            domain_id: ID do domínio DDS (padrão: 0)
        """
        self.domain_id = domain_id
        self.running = True
        
        # Configuração de QoS para baixa latência e confiabilidade
        self.qos = Qos(
            Policy.Reliability.Reliable(duration(seconds=10)),
            Policy.Durability.Volatile,
            Policy.History.KeepLast(1),
            Policy.ResourceLimits(max_samples=1000),
            Policy.Deadline(duration(milliseconds=100))
        )
        
        self._setup_dds()
        
    def _setup_dds(self):
        """
        Configura participante DDS, tópicos, escritor e leitor.
        """
        print(f"Inicializando servidor echo no domínio {self.domain_id}...")
        
        # Criação do participante DDS
        self.participant = DomainParticipant(self.domain_id)
        
        # Criação dos tópicos
        self.request_topic = Topic(self.participant, "RTTRequest", RTTRequest)
        self.response_topic = Topic(self.participant, "RTTResponse", RTTResponse)
        
        # Criação do leitor para requisições
        self.request_reader = DataReader(self.participant, self.request_topic, qos=self.qos)
        
        # Criação do escritor para respostas
        self.response_writer = DataWriter(self.participant, self.response_topic, qos=self.qos)
        
        print("Servidor echo configurado com sucesso!")
        print("Tópicos:")
        print(f"  - Requisições: {self.request_topic.name}")
        print(f"  - Respostas: {self.response_topic.name}")
        
    def run(self):
        """
        Loop principal do servidor echo.
        
        Processa requisições e envia respostas continuamente.
        """
        print("Servidor echo iniciado. Aguardando requisições...")
        print("Pressione Ctrl+C para parar.\n")
        
        request_count = 0
        
        try:
            while self.running:
                # Lê requisições disponíveis
                samples = self.request_reader.take()
                
                for sample in samples:
                    if hasattr(sample, 'sample_info') and sample.sample_info.valid_data:
                        request = sample
                        request_count += 1
                        
                        # Log da requisição recebida
                        print(f"Requisição {request_count}: ID={request.id}, "
                              f"Payload={len(request.data)} bytes")
                        
                        # Cria resposta com mesmo ID e payload
                        response = RTTResponse(
                            id=request.id,
                            data=request.data
                        )
                        
                        # Envia resposta imediatamente
                        self.response_writer.write(response)
                        
                        # Log da resposta enviada
                        print(f"Resposta {request_count}: ID={response.id}, "
                              f"Payload={len(response.data)} bytes")
                
                # Pequena pausa para evitar uso excessivo de CPU
                time.sleep(0.001)  # 1ms
                
        except KeyboardInterrupt:
            print("\nInterrupção recebida. Parando servidor...")
        except Exception as e:
            print(f"Erro no servidor: {e}")
        finally:
            self.cleanup()
            
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
            
        print("Servidor echo finalizado.")
        
    def stop(self):
        """
        Para o servidor graciosamente.
        """
        self.running = False


def signal_handler(signum, frame):
    """
    Manipulador de sinal para parada graciosa.
    """
    print("\nSinal de interrupção recebido. Parando servidor...")
    sys.exit(0)


def main():
    """
    Função principal do servidor.
    """
    # Configura argumentos de linha de comando
    parser = argparse.ArgumentParser(description="Servidor Echo RTT usando Cyclone DDS")
    parser.add_argument("--domain-id", type=int, default=0,
                        help="ID do domínio DDS (padrão: 0)")
    
    args = parser.parse_args()
    
    # Configura manipulador de sinal
    signal.signal(signal.SIGINT, signal_handler)
    
    # Cria e executa servidor
    server = RTTEchoServer(domain_id=args.domain_id)
    
    try:
        server.run()
    except Exception as e:
        print(f"Erro fatal no servidor: {e}")
        server.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()