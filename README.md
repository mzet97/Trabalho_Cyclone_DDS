# Trabalho Eclipse Cyclone DDS

Este repositório contém dois projetos completos demonstrando o uso do Eclipse Cyclone DDS em Python para diferentes cenários de comunicação distribuída.

## 📋 Visão Geral

O Eclipse Cyclone DDS é uma implementação open-source do padrão Data Distribution Service (DDS) da OMG, oferecendo comunicação publish/subscribe de alta performance para sistemas distribuídos. Este trabalho explora suas capacidades através de duas aplicações práticas:

1. **Sistema de Medição RTT** - Avaliação de performance de rede
2. **Sistema de Monitoramento de Frota** - Rastreamento de veículos em tempo real

## 🚀 Projetos

### 1. Sistema de Medição RTT (`RRT/`)

**Objetivo**: Medir Round-Trip Time (RTT) entre cliente e servidor usando DDS

**Características**:
- Arquitetura cliente-servidor com echo
- Medições de latência de alta precisão
- Suporte a múltiplos tamanhos de payload (1 byte a 131KB)
- Análise estatística e visualização de dados
- Suporte a múltiplos clientes concorrentes

**Casos de Uso**:
- Avaliação de performance de rede
- Benchmarking de sistemas DDS
- Análise de latência em diferentes condições

[📖 Documentação Completa](./RRT/README.md)

### 2. Sistema de Monitoramento de Frota (`frota_dds/`)

**Objetivo**: Monitorar frota de veículos em tempo real usando DDS

**Características**:
- Simulação realística de veículos
- Monitor central com sistema de alertas
- Múltiplos tipos de veículos (caminhão, carro, van, ônibus, motocicleta)
- Interface interativa de simulação
- Estatísticas da frota em tempo real

**Casos de Uso**:
- Sistemas de gestão de frotas
- Monitoramento de transporte público
- Logística e rastreamento de veículos

[📖 Documentação Completa](./frota_dds/README.md)

## 🏗️ Arquitetura DDS Demonstrada

Ambos os projetos demonstram conceitos fundamentais do DDS:

### Componentes DDS
- **DomainParticipant**: Ponto de entrada para comunicação DDS
- **Topic**: Canal de comunicação tipado
- **DataWriter**: Publicador de dados
- **DataReader**: Subscritor de dados
- **QoS Policies**: Configurações de qualidade de serviço

### Padrões de Comunicação
- **Publish/Subscribe**: Desacoplamento entre produtores e consumidores
- **Request/Reply**: Comunicação bidirecional (RTT)
- **Descoberta Automática**: Participantes se encontram automaticamente
- **Multicast**: Distribuição eficiente de dados

## 📊 Comparação dos Projetos

| Aspecto | Sistema RTT | Sistema de Frota |
|---------|-------------|------------------|
| **Padrão** | Request/Reply | Publish/Subscribe |
| **Foco** | Performance/Latência | Monitoramento em Tempo Real |
| **Dados** | Payloads de teste | Dados de telemetria |
| **QoS** | Baixa latência | Confiabilidade |
| **Escalabilidade** | Múltiplos clientes | Múltiplos veículos |
| **Análise** | Estatísticas RTT | Alertas e dashboards |

## 🛠️ Instalação Geral

### Pré-requisitos

1. **Eclipse Cyclone DDS C** (biblioteca nativa)
2. **Python 3.8+**
3. **Ambiente virtual** (recomendado)

### Instalação Rápida

```bash
# Clone o repositório
git clone <url-do-repositorio>
cd Trabalho_Cyclone_DDS

# Crie ambiente virtual
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate     # Windows

# Instale dependências para ambos os projetos
pip install -r RRT/requirements.txt
pip install -r frota_dds/requirements.txt
```

### Verificação

```bash
# Teste se Cyclone DDS está funcionando
python -c "from cyclonedx.domain import DomainParticipant; print('Cyclone DDS OK')"
```

## 🚀 Execução Rápida

### Sistema RTT

```bash
cd RRT

# Terminal 1: Servidor
python servidor.py

# Terminal 2: Cliente
python cliente.py

# Análise dos resultados
python analisar_resultados.py
```

### Sistema de Frota

```bash
cd frota_dds

# Simulação completa (recomendado)
python fleet_simulation.py

# Ou execução manual:
# Terminal 1: Monitor
python traffic_monitor.py

# Terminal 2: Veículo
python vehicle_publisher.py TRUCK_001
```

## 📈 Resultados e Análises

### Sistema RTT
- Gráficos de latência vs tamanho de payload
- Estatísticas detalhadas (média, percentis, outliers)
- Análise de performance em diferentes condições
- Comparação entre múltiplos clientes

### Sistema de Frota
- Monitoramento em tempo real de veículos
- Sistema de alertas (combustível baixo, velocidade excessiva)
- Estatísticas da frota (velocidade média, distribuição de status)
- Histórico de dados dos veículos

## 🔧 Configurações Avançadas

### QoS Policies

Ambos os projetos permitem personalização de QoS:

```python
# Exemplo: Configuração para baixa latência
low_latency_qos = Qos(
    Policy.Reliability.BestEffort,
    Policy.History.KeepLast(1),
    Policy.Durability.Volatile
)

# Exemplo: Configuração para alta confiabilidade
high_reliability_qos = Qos(
    Policy.Reliability.Reliable(duration(seconds=10)),
    Policy.History.KeepAll,
    Policy.Durability.TransientLocal
)
```

### Descoberta de Rede

```bash
# Para redes com multicast limitado
export CYCLONEDDS_URI="<dds><discovery><peers><peer address='192.168.1.100'/></peers></discovery></dds>"
```

## 🐛 Solução de Problemas Comuns

### Erro: "Could not locate cyclonedds"

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y libddsc0 cyclonedx-dev

# Depois reinstale o pacote Python
pip install --force-reinstall cyclonedx
```

### Erro: "externally-managed-environment"

```bash
# Use sempre ambiente virtual
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Problemas de Descoberta

1. Verifique se todas as máquinas estão na mesma rede
2. Configure firewall para permitir tráfego UDP (portas 7400-7500)
3. Use o mesmo domain_id em todos os participantes
4. Aguarde 5-10 segundos para descoberta automática

## 📚 Recursos de Aprendizado

### Conceitos DDS Demonstrados

1. **Publish/Subscribe**: Desacoplamento temporal e espacial
2. **Quality of Service**: Configuração de comportamento de comunicação
3. **Descoberta Automática**: Zero-configuration networking
4. **Tipos de Dados**: Serialização automática com IDL
5. **Domínios**: Isolamento de aplicações
6. **Tópicos**: Organização semântica de dados

### Padrões de Design

1. **Producer/Consumer**: Sistema de frota
2. **Request/Reply**: Sistema RTT
3. **Event Notification**: Alertas da frota
4. **Data Distribution**: Telemetria de veículos

## 🎯 Casos de Uso Reais

### Sistema RTT
- **Telecomunicações**: Medição de latência de rede
- **Gaming**: Análise de lag em jogos online
- **IoT**: Avaliação de conectividade de dispositivos
- **Cloud Computing**: Benchmarking de data centers

### Sistema de Frota
- **Logística**: Rastreamento de caminhões de entrega
- **Transporte Público**: Monitoramento de ônibus
- **Emergência**: Coordenação de ambulâncias
- **Mineração**: Rastreamento de veículos pesados

## 🔮 Extensões Possíveis

### Melhorias Técnicas
1. **Interface Web**: Dashboard em tempo real
2. **Banco de Dados**: Persistência de dados históricos
3. **Machine Learning**: Predição de problemas
4. **Geolocalização**: Mapas interativos
5. **APIs REST**: Integração com sistemas externos

### Novos Cenários
1. **Sistema de Chat**: Comunicação em tempo real
2. **Streaming de Vídeo**: Distribuição de mídia
3. **Controle Industrial**: Automação de fábrica
4. **Smart City**: Sensores urbanos distribuídos

## 📄 Licença

Este projeto é desenvolvido para fins educacionais e de pesquisa. Consulte os arquivos de licença individuais em cada subprojeto.

## 🤝 Contribuições

Contribuições são bem-vindas! Para contribuir:

1. Fork o repositório
2. Crie uma branch para sua feature
3. Implemente suas mudanças
4. Adicione testes se necessário
5. Envie um Pull Request

## 📞 Suporte

Para dúvidas e problemas:

1. Consulte a documentação específica de cada projeto
2. Verifique a [documentação oficial do Cyclone DDS](https://cyclonedx.io/docs/)
3. Procure ajuda na [comunidade DDS](https://stackoverflow.com/questions/tagged/cyclone-dds)
4. Abra uma issue neste repositório

---

**Desenvolvido como parte de trabalho acadêmico sobre Eclipse Cyclone DDS**

*Demonstrando o poder da comunicação distribuída com DDS em aplicações práticas*