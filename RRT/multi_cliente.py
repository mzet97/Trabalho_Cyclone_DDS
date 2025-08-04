#!/usr/bin/env python3
"""
Executor de múltiplos clientes RTT concorrentes

Este script permite executar N clientes RTT em paralelo usando
concurrent.futures.ThreadPoolExecutor para testar carga e concorrência.
"""

import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
import sys

from cliente import RTTClient


def run_single_client(client_config: dict) -> dict:
    """
    Executa um único cliente RTT.
    
    Args:
        client_config: Configuração do cliente contendo:
            - client_id: ID único do cliente
            - domain_id: ID do domínio DDS
            - timeout_ms: Timeout em milissegundos
            
    Returns:
        Dicionário com resultados da execução
    """
    client_id = client_config['client_id']
    domain_id = client_config['domain_id']
    timeout_ms = client_config['timeout_ms']
    
    print(f"Iniciando cliente {client_id}...")
    
    start_time = time.time()
    
    try:
        # Cria e executa cliente
        client = RTTClient(
            client_id=client_id,
            domain_id=domain_id,
            timeout_ms=timeout_ms
        )
        
        # Executa medições
        client.run_measurements()
        
        # Limpa recursos
        client.cleanup()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        result = {
            'client_id': client_id,
            'status': 'success',
            'execution_time': execution_time,
            'csv_file': client.csv_filename,
            'error': None
        }
        
        print(f"Cliente {client_id} concluído com sucesso em {execution_time:.2f}s")
        return result
        
    except Exception as e:
        end_time = time.time()
        execution_time = end_time - start_time
        
        result = {
            'client_id': client_id,
            'status': 'error',
            'execution_time': execution_time,
            'csv_file': None,
            'error': str(e)
        }
        
        print(f"Cliente {client_id} falhou após {execution_time:.2f}s: {e}")
        return result


def create_client_configs(num_clients: int, domain_id: int, timeout_ms: int) -> List[dict]:
    """
    Cria configurações para múltiplos clientes.
    
    Args:
        num_clients: Número de clientes a criar
        domain_id: ID do domínio DDS
        timeout_ms: Timeout em milissegundos
        
    Returns:
        Lista de configurações de clientes
    """
    configs = []
    
    for i in range(num_clients):
        config = {
            'client_id': f"client_{i+1:03d}",
            'domain_id': domain_id,
            'timeout_ms': timeout_ms
        }
        configs.append(config)
        
    return configs


def run_concurrent_clients(num_clients: int, domain_id: int = 0, 
                          timeout_ms: int = 5000, max_workers: int = None) -> List[dict]:
    """
    Executa múltiplos clientes RTT concorrentemente.
    
    Args:
        num_clients: Número de clientes a executar
        domain_id: ID do domínio DDS
        timeout_ms: Timeout em milissegundos
        max_workers: Número máximo de threads (None = automático)
        
    Returns:
        Lista de resultados de execução
    """
    print(f"\nIniciando {num_clients} clientes concorrentes...")
    print(f"Domínio DDS: {domain_id}")
    print(f"Timeout: {timeout_ms}ms")
    print(f"Max workers: {max_workers or 'automático'}\n")
    
    # Cria configurações dos clientes
    client_configs = create_client_configs(num_clients, domain_id, timeout_ms)
    
    # Executa clientes concorrentemente
    results = []
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submete todas as tarefas
        future_to_config = {
            executor.submit(run_single_client, config): config 
            for config in client_configs
        }
        
        # Coleta resultados conforme completam
        for future in as_completed(future_to_config):
            config = future_to_config[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                # Fallback para erros não capturados
                result = {
                    'client_id': config['client_id'],
                    'status': 'error',
                    'execution_time': 0,
                    'csv_file': None,
                    'error': f"Erro não capturado: {e}"
                }
                results.append(result)
                print(f"Erro não capturado no cliente {config['client_id']}: {e}")
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Relatório final
    print(f"\n=== RELATÓRIO FINAL ===")
    print(f"Tempo total de execução: {total_time:.2f}s")
    print(f"Clientes executados: {len(results)}")
    
    successful = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] == 'error']
    
    print(f"Sucessos: {len(successful)}")
    print(f"Falhas: {len(failed)}")
    
    if successful:
        avg_time = sum(r['execution_time'] for r in successful) / len(successful)
        print(f"Tempo médio de execução (sucessos): {avg_time:.2f}s")
        
        print("\nArquivos CSV gerados:")
        for result in successful:
            print(f"  {result['client_id']}: {result['csv_file']}")
    
    if failed:
        print("\nErros encontrados:")
        for result in failed:
            print(f"  {result['client_id']}: {result['error']}")
    
    return results


def main():
    """
    Função principal do executor de múltiplos clientes.
    """
    parser = argparse.ArgumentParser(
        description="Executor de múltiplos clientes RTT concorrentes"
    )
    parser.add_argument("num_clients", type=int,
                       help="Número de clientes a executar")
    parser.add_argument("--domain-id", type=int, default=0,
                       help="ID do domínio DDS (padrão: 0)")
    parser.add_argument("--timeout", type=int, default=5000,
                       help="Timeout em milissegundos (padrão: 5000)")
    parser.add_argument("--max-workers", type=int, default=None,
                       help="Número máximo de threads (padrão: automático)")
    
    args = parser.parse_args()
    
    # Validações
    if args.num_clients <= 0:
        print("Erro: Número de clientes deve ser maior que zero.")
        sys.exit(1)
        
    if args.max_workers is not None and args.max_workers <= 0:
        print("Erro: Número máximo de workers deve ser maior que zero.")
        sys.exit(1)
    
    try:
        # Executa clientes concorrentes
        results = run_concurrent_clients(
            num_clients=args.num_clients,
            domain_id=args.domain_id,
            timeout_ms=args.timeout,
            max_workers=args.max_workers
        )
        
        # Código de saída baseado nos resultados
        failed_count = len([r for r in results if r['status'] == 'error'])
        if failed_count > 0:
            print(f"\nAviso: {failed_count} clientes falharam.")
            sys.exit(1)
        else:
            print("\nTodos os clientes executaram com sucesso!")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\nInterrupção recebida. Parando execução...")
        sys.exit(130)
    except Exception as e:
        print(f"Erro fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()