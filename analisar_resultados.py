#!/usr/bin/env python3
"""
Script de análise de resultados RTT

Este script processa os arquivos CSV gerados pelos clientes RTT
e gera estatísticas e gráficos de desempenho.
"""

import os
import glob
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict
import sys


def find_csv_files(directory: str = ".") -> List[str]:
    """
    Encontra todos os arquivos CSV de resultados RTT.
    
    Args:
        directory: Diretório para buscar arquivos CSV
        
    Returns:
        Lista de caminhos para arquivos CSV
    """
    pattern = os.path.join(directory, "rtt_*.csv")
    csv_files = glob.glob(pattern)
    return sorted(csv_files)


def remove_outliers(df: pd.DataFrame, column: str = 'rtt_us') -> pd.DataFrame:
    """
    Remove outliers usando o método IQR (Interquartile Range).
    
    Args:
        df: DataFrame com os dados
        column: Nome da coluna para detectar outliers
        
    Returns:
        DataFrame sem outliers
    """
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    
    # Define limites para outliers
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    # Remove outliers
    df_clean = df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]
    
    outliers_removed = len(df) - len(df_clean)
    if outliers_removed > 0:
        print(f"    Removidos {outliers_removed} outliers ({outliers_removed/len(df)*100:.1f}%)")
    
    return df_clean


def load_csv_data(csv_files: List[str]) -> Dict[str, pd.DataFrame]:
    """
    Carrega dados de múltiplos arquivos CSV.
    
    Args:
        csv_files: Lista de caminhos para arquivos CSV
        
    Returns:
        Dicionário com DataFrames indexados por nome do arquivo
    """
    data = {}
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            
            # Validação básica
            required_columns = ['size', 'iteration', 'rtt_us']
            if not all(col in df.columns for col in required_columns):
                print(f"Aviso: {csv_file} não possui colunas necessárias. Ignorando.")
                continue
                
            # Remove medições inválidas (RTT negativo ou zero)
            initial_count = len(df)
            df = df[df['rtt_us'] > 0]
            invalid_removed = initial_count - len(df)
            
            if invalid_removed > 0:
                print(f"    Removidas {invalid_removed} medições inválidas")
            
            if len(df) == 0:
                print(f"Aviso: {csv_file} não possui dados válidos. Ignorando.")
                continue
            
            # Remove outliers por tamanho de payload
            df_clean_list = []
            for size in df['size'].unique():
                size_df = df[df['size'] == size]
                if len(size_df) > 10:  # Só remove outliers se tiver dados suficientes
                    size_df_clean = remove_outliers(size_df)
                    df_clean_list.append(size_df_clean)
                else:
                    df_clean_list.append(size_df)
            
            if df_clean_list:
                df = pd.concat(df_clean_list, ignore_index=True)
                
            # Extrai nome do cliente do arquivo
            filename = os.path.basename(csv_file)
            client_name = filename.replace('.csv', '')
            
            data[client_name] = df
            print(f"Carregado: {csv_file} ({len(df)} medições válidas)")
            
        except Exception as e:
            print(f"Erro ao carregar {csv_file}: {e}")
            
    return data


def calculate_statistics(data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Calcula estatísticas agregadas por tamanho de payload.
    
    Args:
        data: Dicionário com DataFrames de cada cliente
        
    Returns:
        DataFrame com estatísticas agregadas
    """
    all_data = []
    
    for client_name, df in data.items():
        df_copy = df.copy()
        df_copy['client'] = client_name
        all_data.append(df_copy)
    
    if not all_data:
        return pd.DataFrame()
        
    # Combina todos os dados
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Calcula estatísticas por tamanho
    stats = combined_df.groupby('size')['rtt_us'].agg([
        'count',
        'mean',
        'std',
        'min',
        'max',
        lambda x: np.percentile(x, 50),  # mediana
        lambda x: np.percentile(x, 95),  # percentil 95
        lambda x: np.percentile(x, 99)   # percentil 99
    ]).round(2)
    
    # Renomeia colunas
    stats.columns = ['count', 'mean', 'std', 'min', 'max', 'p50', 'p95', 'p99']
    
    return stats


def plot_rtt_by_size(data: Dict[str, pd.DataFrame], output_dir: str = "."):
    """
    Gera gráficos individuais de RTT por tamanho de payload com desvio padrão.
    
    Args:
        data: Dicionário com DataFrames de cada cliente
        output_dir: Diretório para salvar gráficos
    """
    # Cria diretório de saída se não existir
    os.makedirs(output_dir, exist_ok=True)
    
    # Combina dados de todos os clientes
    all_data = []
    for client_name, df in data.items():
        all_data.append(df)
    
    if not all_data:
        print("Nenhum dado disponível para plotar.")
        return
        
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Calcula estatísticas por tamanho
    stats = combined_df.groupby('size')['rtt_us'].agg([
        'count', 'mean', 'std', 'min', 'max'
    ]).reset_index()
    
    # Gráfico 1: RTT médio com desvio padrão
    plt.figure(figsize=(14, 8))
    
    plt.errorbar(stats['size'], stats['mean'], yerr=stats['std'], 
                marker='o', capsize=8, capthick=3, linewidth=3, markersize=8,
                color='blue', ecolor='lightblue', alpha=0.8, label='RTT Médio ± Desvio Padrão')
    
    plt.fill_between(stats['size'], 
                     stats['mean'] - stats['std'], 
                     stats['mean'] + stats['std'], 
                     alpha=0.2, color='blue', label='Área do Desvio Padrão')
    
    plt.xlabel('Tamanho do Payload (bytes) - Escala Log Base 2', fontsize=12)
    plt.ylabel('RTT Médio (μs)', fontsize=12)
    plt.title('Round-Trip Time Médio por Tamanho de Payload\n(com Desvio Padrão - Escala Logarítmica Base 2)', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.xscale('log', base=2)
    plt.yscale('log')
    
    # Adiciona marcações customizadas no eixo Y para todos os valores de desvio padrão
    y_ticks_custom = []
    
    # Adiciona valores de média ± desvio padrão (apenas dentro do range desejado)
    for _, row in stats.iterrows():
        mean, std = row['mean'], row['std']
        values = [mean - std, mean, mean + std]
        # Filtra valores dentro do range 150-10000
        values = [v for v in values if 150 <= v <= 10000]
        y_ticks_custom.extend(values)
    
    # Remove duplicatas e ordena
    y_ticks_custom = sorted(list(set(y_ticks_custom)))
    
    # Filtra valores válidos (positivos para escala log)
    y_ticks_custom = [y for y in y_ticks_custom if y > 0]
    
    # Combina com ticks logarítmicos padrão dentro do range
    current_ticks = plt.gca().get_yticks()
    current_ticks = [t for t in current_ticks if 150 <= t <= 10000]
    all_ticks = sorted(list(set(list(current_ticks) + y_ticks_custom)))
    
    # Filtra para evitar muitas marcações (mantém apenas valores significativos)
    filtered_ticks = []
    for tick in all_ticks:
        if tick > 0 and (not filtered_ticks or tick / filtered_ticks[-1] > 1.2):
            filtered_ticks.append(tick)
    
    plt.yticks(filtered_ticks, [f'{int(tick)}' if tick >= 1 else f'{tick:.1f}' for tick in filtered_ticks], fontsize=9)
    
    # Define os limites do eixo Y APÓS configurar os ticks
    plt.ylim(150, 10000)
    
    plt.legend(fontsize=10)
    
    # Adiciona anotações com valores
    for _, row in stats.iterrows():
        plt.annotate(f'{row["mean"]:.0f}μs', 
                    (row['size'], row['mean']), 
                    textcoords="offset points", 
                    xytext=(0,10), ha='center', fontsize=9)
    
    plt.tight_layout()
    
    # Salva gráfico 1
    output_file1 = os.path.join(output_dir, 'rtt_mean_with_std.png')
    plt.savefig(output_file1, dpi=300, bbox_inches='tight')
    print(f"Gráfico RTT médio salvo: {output_file1}")
    plt.close()
    
    # Gráfico 2: Coeficiente de variação (CV = std/mean)
    plt.figure(figsize=(14, 8))
    
    cv = (stats['std'] / stats['mean']) * 100
    plt.bar(stats['size'], cv, color='orange', alpha=0.7, label='Coeficiente de Variação', width=stats['size']*0.3)
    plt.xlabel('Tamanho do Payload (bytes) - Escala Log Base 2', fontsize=12)
    plt.ylabel('Coeficiente de Variação (%)', fontsize=12)
    plt.title('Variabilidade do RTT por Tamanho de Payload', fontsize=14, fontweight='bold')
    plt.xscale('log', base=2)
    plt.grid(True, alpha=0.3, axis='y')
    plt.legend(fontsize=10)
    
    # Adiciona valores no gráfico de barras
    for size, v in zip(stats['size'], cv):
        plt.text(size, v + 0.5, f'{v:.1f}%', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    
    # Salva gráfico 2
    output_file2 = os.path.join(output_dir, 'rtt_coefficient_variation.png')
    plt.savefig(output_file2, dpi=300, bbox_inches='tight')
    print(f"Gráfico coeficiente de variação salvo: {output_file2}")
    plt.close()
    
    # Gráfico 3: Box plot principal
    plt.figure(figsize=(14, 8))
    
    sizes = sorted(combined_df['size'].unique())
    rtt_data = [combined_df[combined_df['size'] == size]['rtt_us'].values for size in sizes]
    
    # Box plot principal
    box_plot = plt.boxplot(rtt_data, tick_labels=[f'{int(size)}' for size in sizes], 
                          patch_artist=True, notch=True, showmeans=True)
    
    # Colorir as caixas
    colors = plt.cm.viridis(np.linspace(0, 1, len(sizes)))
    for patch, color in zip(box_plot['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    # Adiciona overlay com média e desvio padrão
    means = [np.mean(data) for data in rtt_data]
    stds = [np.std(data) for data in rtt_data]
    
    plt.errorbar(range(1, len(sizes) + 1), means, yerr=stds,
                fmt='ro', capsize=8, capthick=3, linewidth=2, markersize=8,
                ecolor='red', markerfacecolor='red', markeredgecolor='black',
                label='Média ± Desvio Padrão', alpha=0.8)
    
    plt.xlabel('Tamanho do Payload (bytes) - Escala Log Base 2', fontsize=12)
    plt.ylabel('RTT (μs)', fontsize=12)
    plt.title('Distribuição de RTT por Tamanho de Payload\n(Box Plot com Média ± Desvio Padrão)', 
                 fontsize=14, fontweight='bold')
    plt.yscale('log')
    
    # Configura eixo X com escala log base 2 e posições corretas
    plt.gca().set_xticks(range(1, len(sizes) + 1))
    plt.gca().set_xticklabels([f'{int(size)}' for size in sizes])
    
    # Adiciona escala log base 2 simulada através de anotações
    ax = plt.gca()
    ax2 = ax.twiny()
    ax2.set_xlim(ax.get_xlim())
    ax2.set_xticks(range(1, len(sizes) + 1))
    ax2.set_xticklabels([f'2^{int(np.log2(size))}' if size > 0 and np.log2(size).is_integer() else '' for size in sizes], fontsize=9)
    ax2.set_xlabel('Potência de 2', fontsize=10, style='italic')
    
    # Adiciona marcações customizadas no eixo Y para todos os valores de desvio padrão
    y_ticks_custom = []
    
    # Adiciona valores de média ± desvio padrão (apenas dentro do range desejado)
    for mean, std in zip(means, stds):
        values = [mean - std, mean, mean + std]
        # Filtra valores dentro do range 150-10000
        values = [v for v in values if 150 <= v <= 10000]
        y_ticks_custom.extend(values)
    
    # Adiciona valores mínimos e máximos dos dados (apenas dentro do range)
    for data in rtt_data:
        if len(data) > 0:
            min_val = np.min(data)
            max_val = np.max(data)
            if 150 <= min_val <= 10000:
                y_ticks_custom.append(min_val)
            if 150 <= max_val <= 10000:
                y_ticks_custom.append(max_val)
    
    # Remove duplicatas e ordena
    y_ticks_custom = sorted(list(set(y_ticks_custom)))
    
    # Filtra valores válidos (positivos para escala log)
    y_ticks_custom = [y for y in y_ticks_custom if y > 0]
    
    # Combina com ticks logarítmicos padrão dentro do range
    current_ticks = plt.gca().get_yticks()
    current_ticks = [t for t in current_ticks if 150 <= t <= 10000]
    all_ticks = sorted(list(set(list(current_ticks) + y_ticks_custom)))
    
    # Filtra para evitar muitas marcações (mantém apenas valores significativos)
    filtered_ticks = []
    for tick in all_ticks:
        if tick > 0 and (not filtered_ticks or tick / filtered_ticks[-1] > 1.2):
            filtered_ticks.append(tick)
    
    plt.yticks(filtered_ticks, [f'{int(tick)}' if tick >= 1 else f'{tick:.1f}' for tick in filtered_ticks], fontsize=9)
    
    # Define os limites do eixo Y APÓS configurar os ticks
    plt.ylim(150, 10000)
    
    plt.grid(True, alpha=0.3, axis='y')
    plt.tick_params(axis='x', rotation=45)
    plt.tick_params(axis='x', which='both', top=False)  # Remove ticks superiores do eixo principal
    plt.legend(fontsize=10)
    
    plt.tight_layout()
    
    # Salva box plot
    output_file_box = os.path.join(output_dir, 'rtt_boxplot.png')
    plt.savefig(output_file_box, dpi=300, bbox_inches='tight')
    print(f"Box plot salvo: {output_file_box}")
    plt.close()
    
    # Gráfico 4: RTT médio com desvio padrão (escala log base 2)
    plt.figure(figsize=(14, 8))
    
    plt.errorbar(sizes, means, yerr=stds, fmt='o-', capsize=8, capthick=3, 
                linewidth=3, markersize=8, color='darkblue', ecolor='lightblue',
                markerfacecolor='blue', markeredgecolor='black', alpha=0.8,
                label='RTT Médio ± Desvio Padrão')
    
    # Área sombreada do desvio padrão
    plt.fill_between(sizes, np.array(means) - np.array(stds), 
                    np.array(means) + np.array(stds), alpha=0.2, color='blue',
                    label='Área do Desvio Padrão')
    
    # Adiciona valores nas barras
    for size, mean, std in zip(sizes, means, stds):
        plt.annotate(f'{mean:.0f}μs\n±{std:.0f}', 
                    (size, mean + std), textcoords="offset points", 
                    xytext=(0,10), ha='center', va='bottom', 
                    fontsize=9, fontweight='bold')
    
    plt.xlabel('Tamanho do Payload (bytes) - Escala Log Base 2', fontsize=12)
    plt.ylabel('RTT Médio (μs)', fontsize=12)
    plt.title('RTT Médio com Desvio Padrão por Tamanho de Payload\n(Escala Logarítmica Base 2)', 
                 fontsize=14, fontweight='bold')
    plt.xscale('log', base=2)
    plt.yscale('log')
    
    # Adiciona marcações customizadas no eixo Y para todos os valores de desvio padrão
    y_ticks_custom = []
    
    # Adiciona valores de média ± desvio padrão (apenas dentro do range desejado)
    for mean, std in zip(means, stds):
        values = [mean - std, mean, mean + std]
        # Filtra valores dentro do range 150-10000
        values = [v for v in values if 150 <= v <= 10000]
        y_ticks_custom.extend(values)
    
    # Remove duplicatas e ordena
    y_ticks_custom = sorted(list(set(y_ticks_custom)))
    
    # Filtra valores válidos (positivos para escala log)
    y_ticks_custom = [y for y in y_ticks_custom if y > 0]
    
    # Combina com ticks logarítmicos padrão dentro do range
    current_ticks = plt.gca().get_yticks()
    current_ticks = [t for t in current_ticks if 150 <= t <= 10000]
    all_ticks = sorted(list(set(list(current_ticks) + y_ticks_custom)))
    
    # Filtra para evitar muitas marcações (mantém apenas valores significativos)
    filtered_ticks = []
    for tick in all_ticks:
        if tick > 0 and (not filtered_ticks or tick / filtered_ticks[-1] > 1.2):
            filtered_ticks.append(tick)
    
    plt.yticks(filtered_ticks, [f'{int(tick)}' if tick >= 1 else f'{tick:.1f}' for tick in filtered_ticks], fontsize=9)
    
    # Define os limites do eixo Y APÓS configurar os ticks
    plt.ylim(150, 10000)
    
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=10)
    
    plt.tight_layout()
    
    # Salva gráfico de linha com escala log
    output_file_line = os.path.join(output_dir, 'rtt_mean_log_scale.png')
    plt.savefig(output_file_line, dpi=300, bbox_inches='tight')
    print(f"Gráfico RTT médio (escala log) salvo: {output_file_line}")
    plt.close()


def plot_rtt_scatter(data: Dict[str, pd.DataFrame], output_dir: str = "."):
    """
    Gera gráficos individuais de dispersão do RTT com desvio padrão.
    
    Args:
        data: Dicionário com DataFrames de cada cliente
        output_dir: Diretório para salvar gráficos
    """
    # Cria diretório de saída se não existir
    os.makedirs(output_dir, exist_ok=True)
    
    # Combina dados de todos os clientes
    all_data = []
    for client_name, df in data.items():
        df_copy = df.copy()
        df_copy['client'] = client_name
        all_data.append(df_copy)
    
    if not all_data:
        print("Nenhum dado disponível para plotar.")
        return
        
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Gráfico 1: Dispersão geral com desvio padrão
    plt.figure(figsize=(14, 10))
    
    # Calcula estatísticas por tamanho para overlay
    stats = combined_df.groupby('size')['rtt_us'].agg(['mean', 'std']).reset_index()
    
    # Scatter plot de todos os pontos
    sizes = combined_df['size'].unique()
    colors = plt.cm.tab10(np.linspace(0, 1, len(sizes)))
    
    for i, size in enumerate(sorted(sizes)):
        size_data = combined_df[combined_df['size'] == size]
        plt.scatter(size_data['size'], size_data['rtt_us'], 
                   alpha=0.6, s=30, color=colors[i], 
                   label=f'{int(size)} bytes (n={len(size_data)})')
    
    # Overlay com média e desvio padrão
    plt.errorbar(stats['size'], stats['mean'], yerr=stats['std'],
                fmt='ko-', capsize=8, capthick=3, linewidth=3, markersize=8,
                ecolor='red', markerfacecolor='red', markeredgecolor='black',
                label='Média ± Desvio Padrão')
    
    plt.xlabel('Tamanho do Payload (bytes) - Escala Log Base 2', fontsize=12)
    plt.ylabel('RTT (μs)', fontsize=12)
    plt.title('Dispersão de RTT por Tamanho de Payload\n(com Média e Desvio Padrão)', 
                 fontsize=14, fontweight='bold')
    plt.xscale('log', base=2)
    plt.yscale('log')
    plt.ylim(150, 10000)
    
    # Adiciona marcações customizadas no eixo Y com valores específicos e bem distribuídos
    y_ticks_custom = []
    
    # Adiciona valores de média ± desvio padrão (apenas dentro do range desejado)
    for _, row in stats.iterrows():
        mean_val = row['mean']
        std_val = row['std']
        values = [mean_val - std_val, mean_val, mean_val + std_val]
        # Filtra valores dentro do range 150-10000
        values = [v for v in values if 150 <= v <= 10000]
        y_ticks_custom.extend(values)
    
    # Define ticks logarítmicos específicos para melhor visualização
    log_ticks = [150, 200, 300, 500, 700, 1000, 1500, 2000, 3000, 5000, 7000, 10000]
    
    # Combina todos os valores
    all_ticks = sorted(list(set(y_ticks_custom + log_ticks)))
    
    # Filtra para manter apenas valores dentro do range e com boa distribuição
    filtered_ticks = []
    for tick in all_ticks:
        if 150 <= tick <= 10000:
            # Adiciona o tick se for o primeiro ou se a diferença for significativa
            if not filtered_ticks or (tick / filtered_ticks[-1] >= 1.2):
                filtered_ticks.append(tick)
    
    # Garante que os valores extremos estejam incluídos
    if 150 not in filtered_ticks:
        filtered_ticks.insert(0, 150)
    if 10000 not in filtered_ticks:
        filtered_ticks.append(10000)
    
    # Ordena novamente
    filtered_ticks = sorted(filtered_ticks)
    
    plt.yticks(filtered_ticks)
    
    plt.grid(True, alpha=0.3)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
    
    plt.tight_layout()
    
    # Salva gráfico 1
    output_file1 = os.path.join(output_dir, 'rtt_scatter_general.png')
    plt.savefig(output_file1, dpi=300, bbox_inches='tight')
    print(f"Gráfico dispersão geral salvo: {output_file1}")
    plt.close()
    
    # Gráfico 2: Dispersão por iteração com envelope de desvio padrão
    plt.figure(figsize=(14, 8))
    
    # Seleciona alguns tamanhos representativos para visualização
    representative_sizes = sorted(sizes)[:6]  # Primeiros 6 tamanhos
    
    for i, size in enumerate(representative_sizes):
        size_data = combined_df[combined_df['size'] == size].sort_values('iteration')
        if len(size_data) > 0:
            # Calcula média móvel e desvio padrão móvel (janela de 50 pontos)
            window_size = min(50, len(size_data) // 4)
            if window_size > 1:
                rolling_mean = size_data['rtt_us'].rolling(window=window_size, center=True).mean()
                rolling_std = size_data['rtt_us'].rolling(window=window_size, center=True).std()
                
                # Plot dos pontos individuais
                plt.scatter(size_data['iteration'], size_data['rtt_us'], 
                           alpha=0.4, s=20, color=colors[i], label=f'{int(size)} bytes')
                
                # Plot da média móvel
                plt.plot(size_data['iteration'], rolling_mean, 
                        color=colors[i], linewidth=2, alpha=0.8)
                
                # Envelope do desvio padrão
                plt.fill_between(size_data['iteration'], 
                               rolling_mean - rolling_std, 
                               rolling_mean + rolling_std, 
                               alpha=0.2, color=colors[i])
    
    plt.xlabel('Iteração', fontsize=12)
    plt.ylabel('RTT (μs)', fontsize=12)
    plt.title('RTT por Iteração\n(Média Móvel ± Desvio Padrão)', 
                 fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=9)
    
    plt.tight_layout()
    
    # Salva gráfico 2
    output_file2 = os.path.join(output_dir, 'rtt_scatter_iteration.png')
    plt.savefig(output_file2, dpi=300, bbox_inches='tight')
    print(f"Gráfico dispersão por iteração salvo: {output_file2}")
    plt.close()
    
    # Gráfico 3: Dispersão com intervalos de confiança
    plt.figure(figsize=(14, 8))
    
    # Calcula intervalos de confiança (95%)
    confidence_stats = combined_df.groupby('size')['rtt_us'].agg([
        'mean', 'std', 'count'
    ]).reset_index()
    
    # Calcula erro padrão e intervalo de confiança
    confidence_stats['se'] = confidence_stats['std'] / np.sqrt(confidence_stats['count'])
    confidence_stats['ci_95'] = 1.96 * confidence_stats['se']  # 95% CI
    
    # Scatter plot com intervalos de confiança
    for i, size in enumerate(sorted(sizes)):
        size_data = combined_df[combined_df['size'] == size]
        plt.scatter(size_data['size'], size_data['rtt_us'], 
                   alpha=0.3, s=20, color=colors[i])
    
    # Overlay com média e intervalo de confiança
    plt.errorbar(confidence_stats['size'], confidence_stats['mean'], 
                yerr=confidence_stats['ci_95'],
                fmt='ro-', capsize=8, capthick=3, linewidth=3, markersize=8,
                ecolor='darkred', markerfacecolor='red', markeredgecolor='black',
                label='Média ± IC 95%')
    
    plt.xlabel('Tamanho do Payload (bytes) - Escala Log Base 2', fontsize=12)
    plt.ylabel('RTT (μs)', fontsize=12)
    plt.title('RTT com Intervalos de Confiança (95%)\n(Dispersão + Média)', 
                 fontsize=14, fontweight='bold')
    plt.xscale('log', base=2)
    plt.yscale('log')
    plt.ylim(150, 10000)
    
    # Adiciona marcações customizadas no eixo Y com valores específicos e bem distribuídos
    y_ticks_custom = []
    
    # Adiciona valores de média ± intervalo de confiança (apenas dentro do range desejado)
    for _, row in confidence_stats.iterrows():
        mean_val = row['mean']
        ci_val = row['ci_95']
        values = [mean_val - ci_val, mean_val, mean_val + ci_val]
        # Filtra valores dentro do range 150-10000
        values = [v for v in values if 150 <= v <= 10000]
        y_ticks_custom.extend(values)
    
    # Define ticks logarítmicos específicos para melhor visualização
    log_ticks = [150, 200, 300, 500, 700, 1000, 1500, 2000, 3000, 5000, 7000, 10000]
    
    # Combina todos os valores
    all_ticks = sorted(list(set(y_ticks_custom + log_ticks)))
    
    # Filtra para manter apenas valores dentro do range e com boa distribuição
    filtered_ticks = []
    for tick in all_ticks:
        if 150 <= tick <= 10000:
            # Adiciona o tick se for o primeiro ou se a diferença for significativa
            if not filtered_ticks or (tick / filtered_ticks[-1] >= 1.2):
                filtered_ticks.append(tick)
    
    # Garante que os valores extremos estejam incluídos
    if 150 not in filtered_ticks:
        filtered_ticks.insert(0, 150)
    if 10000 not in filtered_ticks:
        filtered_ticks.append(10000)
    
    # Ordena novamente
    filtered_ticks = sorted(filtered_ticks)
    
    plt.yticks(filtered_ticks)
    
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=10)
    
    plt.tight_layout()
    
    # Salva gráfico 3
    output_file3 = os.path.join(output_dir, 'rtt_scatter_confidence.png')
    plt.savefig(output_file3, dpi=300, bbox_inches='tight')
    print(f"Gráfico dispersão com IC salvo: {output_file3}")
    plt.close()
    
    # Gráfico 4: Heatmap de densidade RTT vs Tamanho
    plt.figure(figsize=(14, 8))
    
    # Cria bins para o heatmap
    size_bins = np.logspace(np.log10(combined_df['size'].min()), 
                           np.log10(combined_df['size'].max()), 20)
    rtt_bins = np.logspace(np.log10(combined_df['rtt_us'].min()), 
                          np.log10(combined_df['rtt_us'].max()), 30)
    
    # Cria o heatmap
    hist, xedges, yedges = np.histogram2d(combined_df['size'], combined_df['rtt_us'], 
                                         bins=[size_bins, rtt_bins])
    
    # Plot do heatmap
    im = plt.imshow(hist.T, origin='lower', aspect='auto', 
                   extent=[size_bins[0], size_bins[-1], rtt_bins[0], rtt_bins[-1]],
                   cmap='YlOrRd', alpha=0.8)
    
    # Overlay com média e desvio padrão
    plt.errorbar(stats['size'], stats['mean'], yerr=stats['std'],
                fmt='bo-', capsize=6, capthick=2, linewidth=2, markersize=6,
                ecolor='blue', markerfacecolor='blue', markeredgecolor='white',
                label='Média ± Desvio Padrão')
    
    plt.xlabel('Tamanho do Payload (bytes) - Escala Log Base 2', fontsize=12)
    plt.ylabel('RTT (μs)', fontsize=12)
    plt.title('Densidade de RTT vs Tamanho\n(Heatmap + Estatísticas)', 
                 fontsize=14, fontweight='bold')
    plt.xscale('log', base=2)
    plt.yscale('log')
    plt.ylim(150, 10000)
    
    # Adiciona marcações customizadas no eixo Y incluindo valores de desvio padrão
    y_ticks_custom = []
    
    # Adiciona valores de média ± desvio padrão (apenas dentro do range desejado)
    for _, row in stats.iterrows():
        mean_val = row['mean']
        std_val = row['std']
        values = [mean_val - std_val, mean_val, mean_val + std_val]
        # Filtra valores dentro do range 150-10000
        values = [v for v in values if 150 <= v <= 10000]
        y_ticks_custom.extend(values)
    
    # Adiciona valores intermediários importantes
    intermediate_values = [200, 300, 500, 700, 1000, 1500, 2000, 3000, 5000, 7000]
    y_ticks_custom.extend([v for v in intermediate_values if 150 <= v <= 10000])
    
    # Remove duplicatas e ordena
    y_ticks_custom = sorted(list(set(y_ticks_custom)))
    
    # Combina com ticks logarítmicos padrão dentro do range
    current_ticks = plt.gca().get_yticks()
    current_ticks = [t for t in current_ticks if 150 <= t <= 10000]
    all_ticks = sorted(list(set(list(current_ticks) + y_ticks_custom)))
    
    # Filtra para evitar muitas marcações (mantém apenas valores significativos)
    filtered_ticks = []
    for tick in all_ticks:
        if tick > 0 and (not filtered_ticks or tick / filtered_ticks[-1] > 1.15):
            filtered_ticks.append(tick)
    
    plt.yticks(filtered_ticks, [f'{int(tick)}' if tick >= 1 else f'{tick:.1f}' for tick in filtered_ticks], fontsize=9)
    
    plt.legend(fontsize=10)
    
    # Adiciona colorbar
    cbar = plt.colorbar(im, shrink=0.8)
    cbar.set_label('Densidade de Medições', fontsize=10)
    
    plt.tight_layout()
    
    # Salva gráfico 4
    output_file4 = os.path.join(output_dir, 'rtt_heatmap_density.png')
    plt.savefig(output_file4, dpi=300, bbox_inches='tight')
    print(f"Gráfico heatmap de densidade salvo: {output_file4}")
    plt.close()


def plot_rtt_distribution(data: Dict[str, pd.DataFrame], output_dir: str = "."):
    """
    Gera histogramas individuais de distribuição de RTT para cada tamanho de payload.
    
    Args:
        data: Dicionário com DataFrames de cada cliente
        output_dir: Diretório para salvar gráficos
    """
    # Cria diretório de saída se não existir
    os.makedirs(output_dir, exist_ok=True)
    
    # Combina dados de todos os clientes
    all_data = []
    for client_name, df in data.items():
        all_data.append(df)
    
    if not all_data:
        print("Nenhum dado disponível para plotar.")
        return
        
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Pega todos os tamanhos disponíveis
    available_sizes = sorted(combined_df['size'].unique())
    
    print(f"Gerando histogramas individuais para {len(available_sizes)} tamanhos de payload...")
    
    # Gera um gráfico individual para cada tamanho
    for size in available_sizes:
        size_data = combined_df[combined_df['size'] == size]['rtt_us']
        
        if len(size_data) > 0:
            # Cria figura individual
            plt.figure(figsize=(10, 8))
            
            # Calcula estatísticas
            mean_rtt = size_data.mean()
            std_rtt = size_data.std()
            median_rtt = size_data.median()
            p95_rtt = size_data.quantile(0.95)
            p99_rtt = size_data.quantile(0.99)
            
            # Histograma com melhor visualização
            n_bins = min(50, max(10, len(size_data) // 20))
            counts, bins, patches = plt.hist(size_data, bins=n_bins, 
                                           alpha=0.7, edgecolor='black', 
                                           color='skyblue', density=True)
            
            # Linhas de estatísticas principais
            plt.axvline(mean_rtt, color='red', linestyle='--', linewidth=3,
                       label=f'Média: {mean_rtt:.1f}μs')
            plt.axvline(median_rtt, color='green', linestyle='--', linewidth=3,
                       label=f'Mediana: {median_rtt:.1f}μs')
            plt.axvline(p95_rtt, color='orange', linestyle=':', linewidth=3,
                       label=f'P95: {p95_rtt:.1f}μs')
            plt.axvline(p99_rtt, color='purple', linestyle=':', linewidth=2,
                       label=f'P99: {p99_rtt:.1f}μs')
            
            # Múltiplas áreas de desvio padrão
            plt.axvspan(mean_rtt - std_rtt, mean_rtt + std_rtt, 
                       alpha=0.3, color='red', label=f'±1σ ({std_rtt:.1f}μs)')
            plt.axvspan(mean_rtt - 2*std_rtt, mean_rtt + 2*std_rtt, 
                       alpha=0.15, color='orange', label=f'±2σ ({2*std_rtt:.1f}μs)')
            plt.axvspan(mean_rtt - 3*std_rtt, mean_rtt + 3*std_rtt, 
                       alpha=0.1, color='yellow', label=f'±3σ ({3*std_rtt:.1f}μs)')
            
            # Adiciona curva normal teórica para comparação
            x_norm = np.linspace(size_data.min(), size_data.max(), 100)
            y_norm = (1/(std_rtt * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x_norm - mean_rtt) / std_rtt)**2)
            plt.plot(x_norm, y_norm, 'k-', linewidth=2, alpha=0.8, label='Distribuição Normal Teórica')
            
            plt.xlabel('RTT (μs)', fontsize=14)
            plt.ylabel('Densidade', fontsize=14)
            plt.title(f'Distribuição RTT - {int(size)} bytes\n'
                     f'n={len(size_data)}, CV={std_rtt/mean_rtt*100:.1f}%', 
                     fontsize=16, fontweight='bold')
            plt.grid(True, alpha=0.3)
            plt.legend(fontsize=12, loc='upper right')
            
            # Adiciona caixa de texto com estatísticas detalhadas
            stats_text = f'Estatísticas Detalhadas:\n'
            stats_text += f'Min: {size_data.min():.1f}μs\n'
            stats_text += f'Max: {size_data.max():.1f}μs\n'
            stats_text += f'Std: {std_rtt:.1f}μs\n'
            stats_text += f'Variância: {size_data.var():.1f}μs²\n'
            stats_text += f'Skewness: {size_data.skew():.2f}\n'
            stats_text += f'Kurtosis: {size_data.kurtosis():.2f}'
            
            plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes,
                    verticalalignment='top', horizontalalignment='left',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.9),
                    fontsize=10)
            
            # Salva gráfico individual
            output_file = os.path.join(output_dir, f'rtt_distribution_{int(size)}_bytes.png')
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"  Histograma salvo: rtt_distribution_{int(size)}_bytes.png")
            plt.close()
        else:
            print(f"  Aviso: Sem dados para {int(size)} bytes - arquivo não gerado")
    
    # Gráfico adicional: Violin plot comparativo com escala log base 2
    plt.figure(figsize=(16, 8))
    
    # Prepara dados para violin plot
    violin_data = []
    violin_positions = []
    violin_labels = []
    
    for size in available_sizes:
        size_data = combined_df[combined_df['size'] == size]['rtt_us']
        if len(size_data) > 5:  # Só inclui se tiver dados suficientes
            violin_data.append(size_data.values)
            violin_positions.append(size)  # Usa o tamanho real como posição
            violin_labels.append(f'{int(size)}\n(n={len(size_data)})')
    
    if violin_data:
        parts = plt.violinplot(violin_data, positions=violin_positions, 
                              showmeans=True, showmedians=True, widths=[pos*0.3 for pos in violin_positions])
        
        # Colorir os violinos
        colors = plt.cm.plasma(np.linspace(0, 1, len(violin_data)))
        for pc, color in zip(parts['bodies'], colors):
            pc.set_facecolor(color)
            pc.set_alpha(0.7)
        
        # Configurar eixos com escala log base 2
        plt.xscale('log', base=2)
        plt.yscale('log')
        plt.ylim(150, 10000)
        
        # Configurar ticks do eixo x para mostrar os tamanhos
        plt.xticks(violin_positions, [f'{int(size)}' for size in violin_positions], rotation=45)
        
        plt.xlabel('Tamanho do Payload (bytes) - Escala Log Base 2', fontsize=12)
        plt.ylabel('RTT (μs)', fontsize=12)
        plt.title('Distribuição Comparativa de RTT por Tamanho de Payload\n(Violin Plot - Escala Logarítmica Base 2)', 
                 fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        
        # Adiciona legenda explicativa
        from matplotlib.lines import Line2D
        legend_elements = [Line2D([0], [0], color='black', lw=2, label='Mediana'),
                          Line2D([0], [0], color='red', lw=2, label='Média'),
                          Line2D([0], [0], color='purple', lw=3, alpha=0.7, label='Distribuição de Densidade')]
        plt.legend(handles=legend_elements, fontsize=10)
        
        # Salva violin plot
        output_file_violin = os.path.join(output_dir, 'rtt_violin_plot.png')
        plt.savefig(output_file_violin, dpi=300, bbox_inches='tight')
        print(f"Violin plot salvo: {output_file_violin}")
    
    plt.close()


def generate_report(data: Dict[str, pd.DataFrame], stats: pd.DataFrame, 
                   output_dir: str = "."):
    """
    Gera relatório em texto com estatísticas detalhadas.
    
    Args:
        data: Dicionário com DataFrames de cada cliente
        stats: DataFrame com estatísticas agregadas
        output_dir: Diretório para salvar relatório
    """
    # Cria diretório de saída se não existir
    os.makedirs(output_dir, exist_ok=True)
    
    report_file = os.path.join(output_dir, 'relatorio_rtt.txt')
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("RELATÓRIO DE ANÁLISE RTT\n")
        f.write("=" * 50 + "\n\n")
        
        # Informações gerais
        total_clients = len(data)
        total_measurements = sum(len(df) for df in data.values())
        
        f.write(f"Clientes analisados: {total_clients}\n")
        f.write(f"Total de medições: {total_measurements}\n\n")
        
        # Lista de clientes
        f.write("CLIENTES:\n")
        for client_name, df in data.items():
            f.write(f"  {client_name}: {len(df)} medições\n")
        f.write("\n")
        
        # Estatísticas por tamanho
        f.write("ESTATÍSTICAS POR TAMANHO DE PAYLOAD:\n")
        f.write("Size(bytes)  Count    Mean(μs)   Std(μs)    Min(μs)    Max(μs)    P50(μs)    P95(μs)    P99(μs)\n")
        f.write("-" * 100 + "\n")
        
        for size, row in stats.iterrows():
            f.write(f"{size:>10d}  {row['count']:>5.0f}  {row['mean']:>9.2f}  {row['std']:>9.2f}  "
                   f"{row['min']:>9.2f}  {row['max']:>9.2f}  {row['p50']:>9.2f}  "
                   f"{row['p95']:>9.2f}  {row['p99']:>9.2f}\n")
        
        f.write("\n")
        
        # Análise de anomalias
        f.write("ANÁLISE DE ANOMALIAS:\n")
        
        # Combina todos os dados
        all_data = []
        for client_name, df in data.items():
            df_copy = df.copy()
            df_copy['client'] = client_name
            all_data.append(df_copy)
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            
            # Detecta outliers usando IQR
            for size in combined_df['size'].unique():
                size_data = combined_df[combined_df['size'] == size]['rtt_us']
                
                if len(size_data) > 10:  # Só analisa se tiver dados suficientes
                    q1 = size_data.quantile(0.25)
                    q3 = size_data.quantile(0.75)
                    iqr = q3 - q1
                    lower_bound = q1 - 1.5 * iqr
                    upper_bound = q3 + 1.5 * iqr
                    
                    outliers = size_data[(size_data < lower_bound) | (size_data > upper_bound)]
                    outlier_percentage = (len(outliers) / len(size_data)) * 100
                    
                    if outlier_percentage > 5:  # Reporta se > 5% outliers
                        f.write(f"  {size} bytes: {outlier_percentage:.1f}% outliers detectados\n")
        
    print(f"Relatório salvo: {report_file}")


def main():
    """
    Função principal do analisador de resultados.
    """
    parser = argparse.ArgumentParser(
        description="Analisador de resultados RTT"
    )
    parser.add_argument("--directory", default=".",
                       help="Diretório contendo arquivos CSV (padrão: atual)")
    parser.add_argument("--output", default=".",
                       help="Diretório para salvar resultados (padrão: atual)")
    parser.add_argument("--no-plots", action="store_true",
                       help="Não gerar gráficos")
    
    args = parser.parse_args()
    
    # Encontra arquivos CSV
    csv_files = find_csv_files(args.directory)
    
    if not csv_files:
        print(f"Nenhum arquivo CSV encontrado em {args.directory}")
        print("Procurando por arquivos com padrão 'rtt_*.csv'")
        sys.exit(1)
    
    print(f"Encontrados {len(csv_files)} arquivos CSV")
    
    # Carrega dados
    data = load_csv_data(csv_files)
    
    if not data:
        print("Nenhum dado válido encontrado nos arquivos CSV")
        sys.exit(1)
    
    # Calcula estatísticas
    stats = calculate_statistics(data)
    
    if stats.empty:
        print("Não foi possível calcular estatísticas")
        sys.exit(1)
    
    # Exibe estatísticas no console
    print("\nESTATÍSTICAS POR TAMANHO DE PAYLOAD:")
    print(stats)
    
    # Gera gráficos
    if not args.no_plots:
        try:
            plot_rtt_by_size(data, args.output)
            plot_rtt_scatter(data, args.output)
            plot_rtt_distribution(data, args.output)
        except Exception as e:
            print(f"Erro ao gerar gráficos: {e}")
            print("Continuando sem gráficos...")
    
    # Gera relatório
    try:
        generate_report(data, stats, args.output)
    except Exception as e:
        print(f"Erro ao gerar relatório: {e}")
    
    print("\nAnálise concluída!")


if __name__ == "__main__":
    main()