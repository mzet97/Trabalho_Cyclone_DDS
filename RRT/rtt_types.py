#!/usr/bin/env python3
"""
Definições de tipos para medição de RTT usando Eclipse Cyclone DDS

Este módulo define as estruturas de dados RTTRequest e RTTResponse
usando IdlStruct do cyclonedds para serialização automática.
"""

from cyclonedds.idl import IdlStruct
from cyclonedds.idl.annotations import key
from cyclonedds.idl.types import sequence, uint8
from dataclasses import dataclass


@dataclass
class RTTRequest(IdlStruct, typename="RTTTypes::RTTRequest"):
    """
    Estrutura de dados para requisição RTT.
    
    Attributes:
        id: Identificador único para correlacionar pedido e resposta
        data: Payload de dados variável (sequência de octets)
    """
    id: int
    data: sequence[uint8]  # sequence<octet> em IDL


@dataclass
class RTTResponse(IdlStruct, typename="RTTTypes::RTTResponse"):
    """
    Estrutura de dados para resposta RTT.
    
    Attributes:
        id: Identificador correspondente ao pedido
        data: Mesmo payload retornado pelo servidor
    """
    id: int
    data: sequence[uint8]  # sequence<octet> em IDL


def create_payload(size: int) -> list:
    """
    Cria um payload de dados com tamanho específico.
    
    Args:
        size: Tamanho do payload em bytes
        
    Returns:
        Lista de inteiros representando os bytes do payload
    """
    return [i % 256 for i in range(size)]


def validate_payload(original: list, received: list) -> bool:
    """
    Valida se o payload recebido é idêntico ao original.
    
    Args:
        original: Payload original enviado
        received: Payload recebido na resposta
        
    Returns:
        True se os payloads são idênticos, False caso contrário
    """
    return original == received