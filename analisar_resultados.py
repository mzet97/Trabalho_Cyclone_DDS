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
    Gera gráfico de RTT por tamanho de payload com desvio padrão.
    
    Args:
        data: Dicionário com DataFrames de cada cliente
        output_dir: Diretório para salvar gráficos
    """
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
    
    # Cria figura com subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12))
    
    # Gráfico 1: RTT médio com desvio padrão
    ax1.errorbar(stats['size'], stats['mean'], yerr=stats['std'], 
                marker='o', capsize=8, capthick=3, linewidth=3, markersize=8,
                color='blue', ecolor='lightblue', alpha=0.8)
    
    ax1.fill_between(stats['size'], 
                     stats['mean'] - stats['std'], 
                     stats['mean'] + stats['std'], 
                     alpha=0.2, color='blue')
    
    ax1.set_xlabel('Tamanho do Payload (bytes) - Escala Log Base 2', fontsize=12)
    ax1.set_ylabel('RTT Médio (μs)', fontsize=12)
    ax1.set_title('Round-Trip Time Médio por Tamanho de Payload\n(com Desvio Padrão - Escala Logarítmica Base 2)', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.set_xscale('log', base=2)
    ax1.set_yscale('log')
    
    # Adiciona anotações com valores
    for _, row in stats.iterrows():
        ax1.annotate(f'{row["mean"]:.0f}μs', 
                    (row['size'], row['mean']), 
                    textcoords="offset points", 
                    xytext=(0,10), ha='center', fontsize=9)
    
    # Gráfico 2: Coeficiente de variação (CV = std/mean)
    cv = (stats['std'] / stats['mean']) * 100
    ax2.bar(range(len(stats)), cv, color='orange', alpha=0.7)
    ax2.set_xlabel('Tamanho do Payload (bytes)', fontsize=12)
    ax2.set_ylabel('Coeficiente de Variação (%)', fontsize=12)
    ax2.set_title('Variabilidade do RTT por Tamanho de Payload', fontsize=14, fontweight='bold')
    ax2.set_xticks(range(len(stats)))
    ax2.set_xticklabels([f'{int(size)}' for size in stats['size']], rotation=45)
    ax2.grid(True, alpha=0.3, axis='y')
    
    # Adiciona valores no gráfico de barras
    for i, v in enumerate(cv):
        ax2.text(i, v + 0.5, f'{v:.1f}%', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    
    # Salva gráfico
    output_file = os.path.join(output_dir, 'rtt_by_size_detailed.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Gráfico detalhado salvo: {output_file}")
    plt.close()
    
    # Gráfico adicional: Box plot aprimorado com desvio padrão
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12))
    
    sizes = sorted(combined_df['size'].unique())
    rtt_data = [combined_df[combined_df['size'] == size]['rtt_us'].values for size in sizes]
    
    # Box plot principal
    box_plot = ax1.boxplot(rtt_data, labels=[f'{int(size)}' for size in sizes], 
                          patch_artist=True, notch=True, showmeans=True)
    
    # Colorir as caixas
    colors = plt.cm.viridis(np.linspace(0, 1, len(sizes)))
    for patch, color in zip(box_plot['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    # Adiciona overlay com média e desvio padrão
    means = [np.mean(data) for data in rtt_data]
    stds = [np.std(data) for data in rtt_data]
    
    ax1.errorbar(range(1, len(sizes) + 1), means, yerr=stds,
                fmt='ro', capsize=8, capthick=3, linewidth=2, markersize=8,
                ecolor='red', markerfacecolor='red', markeredgecolor='black',
                label='Média ± Desvio Padrão', alpha=0.8)
    
    ax1.set_xlabel('Tamanho do Payload (bytes)', fontsize=12)
    ax1.set_ylabel('RTT (μs)', fontsize=12)
    ax1.set_title('Distribuição de RTT por Tamanho de Payload\n(Box Plot com Média ± Desvio Padrão)', 
                 fontsize=14, fontweight='bold')
    ax1.set_yscale('log')
    
    # Adiciona marcações customizadas no eixo Y para todos os valores de desvio padrão
    y_ticks_custom = []
    
    # Adiciona valores de média ± desvio padrão
    for mean, std in zip(means, stds):
        y_ticks_custom.extend([mean - std, mean, mean + std])
    
    # Adiciona valores mínimos e máximos dos dados
    for data in rtt_data:
        if len(data) > 0:
            y_ticks_custom.extend([np.min(data), np.max(data)])
    
    # Remove duplicatas e ordena
    y_ticks_custom = sorted(list(set(y_ticks_custom)))
    
    # Filtra valores válidos (positivos para escala log)
    y_ticks_custom = [y for y in y_ticks_custom if y > 0]
    
    # Combina com ticks logarítmicos padrão
    current_ticks = ax1.get_yticks()
    all_ticks = sorted(list(set(list(current_ticks) + y_ticks_custom)))
    
    # Filtra para evitar muitas marcações (mantém apenas valores significativos)
    filtered_ticks = []
    for tick in all_ticks:
        if tick > 0 and (not filtered_ticks or tick / filtered_ticks[-1] > 1.2):
            filtered_ticks.append(tick)
    
    ax1.set_yticks(filtered_ticks)
    ax1.set_yticklabels([f'{int(tick)}' if tick >= 1 else f'{tick:.1f}' for tick in filtered_ticks], fontsize=9)
    
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.tick_params(axis='x', rotation=45)
    ax1.legend(fontsize=10)
    
    # Gráfico de barras com desvio padrão (usando escala log base 2)
    ax2.errorbar(sizes, means, yerr=stds, fmt='o-', capsize=8, capthick=3, 
                linewidth=3, markersize=8, color='darkblue', ecolor='lightblue',
                markerfacecolor='blue', markeredgecolor='black', alpha=0.8)
    
    # Área sombreada do desvio padrão
    ax2.fill_between(sizes, np.array(means) - np.array(stds), 
                    np.array(means) + np.array(stds), alpha=0.2, color='blue')
    
    # Adiciona valores nas barras
    for size, mean, std in zip(sizes, means, stds):
        ax2.annotate(f'{mean:.0f}μs\n±{std:.0f}', 
                    (size, mean + std), textcoords="offset points", 
                    xytext=(0,10), ha='center', va='bottom', 
                    fontsize=9, fontweight='bold')
    
    ax2.set_xlabel('Tamanho do Payload (bytes) - Escala Log Base 2', fontsize=12)
    ax2.set_ylabel('RTT Médio (μs)', fontsize=12)
    ax2.set_title('RTT Médio com Desvio Padrão por Tamanho de Payload\n(Escala Logarítmica Base 2)', 
                 fontsize=14, fontweight='bold')
    ax2.set_xscale('log', base=2)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Salva box plot aprimorado
    output_file_box = os.path.join(output_dir, 'rtt_boxplot.png')
    plt.savefig(output_file_box, dpi=300, bbox_inches='tight')
    print(f"Box plot aprimorado salvo: {output_file_box}")
    plt.close()


def plot_rtt_scatter(data: Dict[str, pd.DataFrame], output_dir: str = "."):
    """
    Gera gráfico de dispersão do RTT com desvio padrão.
    
    Args:
        data: Dicionário com DataFrames de cada cliente
        output_dir: Diretório para salvar gráficos
    """
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
    
    # Cria figura com múltiplos subplots
    fig = plt.figure(figsize=(16, 12))
    
    # Subplot 1: Dispersão geral com desvio padrão
    ax1 = plt.subplot(2, 2, 1)
    
    # Calcula estatísticas por tamanho para overlay
    stats = combined_df.groupby('size')['rtt_us'].agg(['mean', 'std']).reset_index()
    
    # Scatter plot de todos os pontos
    sizes = combined_df['size'].unique()
    colors = plt.cm.tab10(np.linspace(0, 1, len(sizes)))
    
    for i, size in enumerate(sorted(sizes)):
        size_data = combined_df[combined_df['size'] == size]
        ax1.scatter(size_data['size'], size_data['rtt_us'], 
                   alpha=0.6, s=30, color=colors[i], 
                   label=f'{int(size)} bytes (n={len(size_data)})')
    
    # Overlay com média e desvio padrão
    ax1.errorbar(stats['size'], stats['mean'], yerr=stats['std'],
                fmt='ko-', capsize=8, capthick=3, linewidth=3, markersize=8,
                ecolor='red', markerfacecolor='red', markeredgecolor='black',
                label='Média ± Desvio Padrão')
    
    ax1.set_xlabel('Tamanho do Payload (bytes) - Escala Log Base 2', fontsize=12)
    ax1.set_ylabel('RTT (μs)', fontsize=12)
    ax1.set_title('Dispersão de RTT por Tamanho de Payload\n(com Média e Desvio Padrão)', 
                 fontsize=14, fontweight='bold')
    ax1.set_xscale('log', base=2)
    ax1.set_yscale('log')
    ax1.grid(True, alpha=0.3)
    ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
    
    # Subplot 2: Dispersão por iteração com envelope de desvio padrão
    ax2 = plt.subplot(2, 2, 2)
    
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
                ax2.scatter(size_data['iteration'], size_data['rtt_us'], 
                           alpha=0.4, s=20, color=colors[i], label=f'{int(size)} bytes')
                
                # Plot da média móvel
                ax2.plot(size_data['iteration'], rolling_mean, 
                        color=colors[i], linewidth=2, alpha=0.8)
                
                # Envelope do desvio padrão
                ax2.fill_between(size_data['iteration'], 
                               rolling_mean - rolling_std, 
                               rolling_mean + rolling_std, 
                               alpha=0.2, color=colors[i])
    
    ax2.set_xlabel('Iteração', fontsize=12)
    ax2.set_ylabel('RTT (μs)', fontsize=12)
    ax2.set_title('RTT por Iteração\n(Média Móvel ± Desvio Padrão)', 
                 fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=9)
    
    # Subplot 3: Dispersão com intervalos de confiança
    ax3 = plt.subplot(2, 2, 3)
    
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
        ax3.scatter(size_data['size'], size_data['rtt_us'], 
                   alpha=0.3, s=20, color=colors[i])
    
    # Overlay com média e intervalo de confiança
    ax3.errorbar(confidence_stats['size'], confidence_stats['mean'], 
                yerr=confidence_stats['ci_95'],
                fmt='ro-', capsize=8, capthick=3, linewidth=3, markersize=8,
                ecolor='darkred', markerfacecolor='red', markeredgecolor='black',
                label='Média ± IC 95%')
    
    ax3.set_xlabel('Tamanho do Payload (bytes) - Escala Log Base 2', fontsize=12)
    ax3.set_ylabel('RTT (μs)', fontsize=12)
    ax3.set_title('RTT com Intervalos de Confiança (95%)\n(Dispersão + Média)', 
                 fontsize=14, fontweight='bold')
    ax3.set_xscale('log', base=2)
    ax3.set_yscale('log')
    ax3.grid(True, alpha=0.3)
    ax3.legend(fontsize=10)
    
    # Subplot 4: Heatmap de densidade RTT vs Tamanho
    ax4 = plt.subplot(2, 2, 4)
    
    # Cria bins para o heatmap
    size_bins = np.logspace(np.log10(combined_df['size'].min()), 
                           np.log10(combined_df['size'].max()), 20)
    rtt_bins = np.logspace(np.log10(combined_df['rtt_us'].min()), 
                          np.log10(combined_df['rtt_us'].max()), 30)
    
    # Cria o heatmap
    hist, xedges, yedges = np.histogram2d(combined_df['size'], combined_df['rtt_us'], 
                                         bins=[size_bins, rtt_bins])
    
    # Plot do heatmap
    im = ax4.imshow(hist.T, origin='lower', aspect='auto', 
                   extent=[size_bins[0], size_bins[-1], rtt_bins[0], rtt_bins[-1]],
                   cmap='YlOrRd', alpha=0.8)
    
    # Overlay com média e desvio padrão
    ax4.errorbar(stats['size'], stats['mean'], yerr=stats['std'],
                fmt='bo-', capsize=6, capthick=2, linewidth=2, markersize=6,
                ecolor='blue', markerfacecolor='blue', markeredgecolor='white',
                label='Média ± Desvio Padrão')
    
    ax4.set_xlabel('Tamanho do Payload (bytes) - Escala Log Base 2', fontsize=12)
    ax4.set_ylabel('RTT (μs)', fontsize=12)
    ax4.set_title('Densidade de RTT vs Tamanho\n(Heatmap + Estatísticas)', 
                 fontsize=14, fontweight='bold')
    ax4.set_xscale('log', base=2)
    ax4.set_yscale('log')
    ax4.legend(fontsize=10)
    
    # Adiciona colorbar
    cbar = plt.colorbar(im, ax=ax4, shrink=0.8)
    cbar.set_label('Densidade de Medições', fontsize=10)
    
    plt.tight_layout()
    
    # Salva gráfico de dispersão
    output_file = os.path.join(output_dir, 'rtt_scatter_analysis.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Gráfico de dispersão salvo: {output_file}")
    plt.close()


def plot_rtt_distribution(data: Dict[str, pd.DataFrame], output_dir: str = "."):
    """
    Gera histogramas individuais de distribuição de RTT para cada tamanho de payload.
    
    Args:
        data: Dicionário com DataFrames de cada cliente
        output_dir: Diretório para salvar gráficos
    """
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
        
        # Configurar ticks do eixo x para mostrar os tamanhos
        plt.xticks(violin_positions, [f'{int(size)}' for size in violin_positions], rotation=45)
        
        plt.xlabel('Tamanho do Payload (bytes) - Escala Log Base 2', fontsize=12)
        plt.ylabel('RTT (μs)', fontsize=12)
        plt.title('Distribuição Comparativa de RTT por Tamanho de Payload\n(Violin Plot - Escala Logarítmica Base 2)', 
                 fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        
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