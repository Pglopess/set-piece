"""
Dashboard principal do SetPiece Analytics.
Interface construída com Streamlit para visualização
das métricas e análises de bola parada.
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from mplsoccer import Pitch, VerticalPitch
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from metrics import (
    metricas_por_tipo, metricas_por_faixa_minuto, metricas_por_time,
    coordenadas_bp, coordenadas_chutes, lista_times, lista_competicoes,
    lista_temporadas, evolucao_temporada, padroes_por_time
)

st.set_page_config(
    page_title="SetPiece Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dicionário com os nomes
TIPO_LABELS = {
    "escanteio":         "Escanteio",
    "falta_direta":      "Falta Direta",
    "falta_indireta":    "Falta Indireta",
    "arremesso_lateral": "Arremesso Lateral",
    "penalti":           "Penalti",
}

# Cores associadas a cada tipo de bola parada nos gráficos
COR_TIPO = {
    "escanteio":         "#4e9af1",
    "falta_direta":      "#f4a031",
    "falta_indireta":    "#f4d03f",
    "arremesso_lateral": "#4ecf7a",
    "penalti":           "#e05c5c",
}

#  Sidebar com filtros 
with st.sidebar:
    st.title("SetPiece Analytics")
    st.caption("StatsBomb Open Data")
    st.divider()

    # Filtro de competição
    comps_df = lista_competicoes()
    comp_opcoes = {"Todas": None}
    comp_opcoes.update(dict(zip(comps_df['nome'], comps_df['id_competicao'])))
    comp_sel = st.selectbox("Competicao", list(comp_opcoes.keys()))
    comp_id = comp_opcoes[comp_sel]

    # Temporadas disponíveis 
    temps_df = lista_temporadas(comp_id)
    temp_opcoes = {"Todas": None}
    temp_opcoes.update({t: t for t in temps_df['temporada']})
    temp_sel = st.selectbox("Temporada", list(temp_opcoes.keys()))
    temporada = temp_opcoes[temp_sel]

    # Filtro de time
    times_df = lista_times()
    time_opcoes = {"Todos os times": None}
    time_opcoes.update(dict(zip(times_df['nome'], times_df['id_time'])))
    time_sel = st.selectbox("Time", list(time_opcoes.keys()))
    time_id = time_opcoes[time_sel]

    # Filtro de tipo de bola parada
    tipo_opcoes = {"Todos": None} | {v: k for k, v in TIPO_LABELS.items()}
    tipo_sel = st.selectbox("Tipo de Bola Parada", list(tipo_opcoes.keys()))
    tipo_id = tipo_opcoes[tipo_sel]

    st.divider()
    # Navegação entre páginas do dashboard
    pagina = st.radio("Pagina", [
        "Visao Geral",
        "Analise Espacial",
        "Por Faixa de Minuto",
        "Ranking de Times",
        "Evolucao por Temporada",
        "Analise de Padroes",
    ])

# Funções auxiliares 

def fmt_pct(v):
    return f"{v:.1f}%" if pd.notna(v) else "-"

def dark_fig(w=8, h=4):

    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor('#0e1117')
    ax.set_facecolor('#0e1117')
    ax.tick_params(colors='white')
    ax.spines[:].set_visible(False)
    return fig, ax

# Visao Geral 
if pagina == "Visao Geral":
    st.header("Visao Geral - Metricas Ofensivas")

    df = metricas_por_tipo(time_id=time_id, competicao_id=comp_id, temporada=temporada)
    df['tipo_label'] = df['tipo'].map(TIPO_LABELS).fillna(df['tipo'])

    total_bp   = df['total_bp'].sum()
    total_gols = df['gols'].sum()
    tf_geral   = (df['finalizacoes'].sum() / total_bp * 100) if total_bp else 0
    tc_geral   = (df['gols'].sum() / total_bp * 100) if total_bp else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total de Bolas Paradas", f"{total_bp:,}")
    c2.metric("Gols Originados", int(total_gols))
    c3.metric("Taxa de Finalizacao", fmt_pct(tf_geral))
    c4.metric("Taxa de Conversao", fmt_pct(tc_geral))

    st.divider()

    # Tabela com todas as métricas por tipo
    tabela = df[['tipo_label','total_bp','finalizacoes','gols','TF','TC','xg_medio']].copy()
    tabela.columns = ['Tipo','Total BP','Finalizacoes','Gols','TF (%)','TC (%)','xG Medio']
    st.dataframe(tabela, use_container_width=True, hide_index=True)

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Volume por Tipo")
        fig, ax = dark_fig(5, 3.5)
        cores = [COR_TIPO.get(t, '#888') for t in df['tipo']]
        bars = ax.barh(df['tipo_label'], df['total_bp'], color=cores)
        ax.bar_label(bars, padding=4, color='white', fontsize=9)
        plt.tight_layout()
        st.pyplot(fig); plt.close()

    with col2:
        # Gráfico comparativo entre TF e TC para ver quais tipos geram mais perigo
        st.subheader("TF vs TC por Tipo")
        fig, ax = dark_fig(5, 3.5)
        x = np.arange(len(df))
        w = 0.35
        ax.bar(x - w/2, df['TF'], w, label='TF (%)', color='#4e9af1')
        ax.bar(x + w/2, df['TC'], w, label='TC (%)', color='#f4a031')
        ax.set_xticks(x)
        ax.set_xticklabels(df['tipo_label'], rotation=20, ha='right', color='white', fontsize=8)
        ax.legend(facecolor='#1e2130', labelcolor='white', fontsize=8)
        plt.tight_layout()
        st.pyplot(fig); plt.close()

    # xG médio
    st.subheader("xG Medio por Tipo")
    fig, ax = dark_fig(8, 2.5)
    cores = [COR_TIPO.get(t, '#888') for t in df['tipo']]
    bars = ax.bar(df['tipo_label'], df['xg_medio'], color=cores)
    ax.bar_label(bars, fmt='%.3f', padding=3, color='white', fontsize=9)
    plt.tight_layout()
    st.pyplot(fig); plt.close()

# Analise Espacial
elif pagina == "Analise Espacial":
    st.header("Analise Espacial")

    tab1, tab2 = st.tabs(["Heatmap de Origens", "Mapa de Finalizacoes"])

    with tab1:
        df_coords = coordenadas_bp(tipo=tipo_id, time_id=time_id,
                                   competicao_id=comp_id, temporada=temporada)
        if df_coords.empty:
            st.warning("Sem dados para os filtros selecionados.")
        else:
            # mplsoccer desenha o campo automaticamente no padrão StatsBomb
            pitch = Pitch(pitch_type='statsbomb', pitch_color='#1a1a2e', line_color='#aaaaaa')
            fig, ax = pitch.draw(figsize=(10, 6))
            fig.patch.set_facecolor('#0e1117')
            # bin_statistic conta quantos pontos caem em cada célula da grade
            bin_s = pitch.bin_statistic(df_coords['coord_x'], df_coords['coord_y'],
                                        statistic='count', bins=(25, 16))
            pitch.heatmap(bin_s, ax=ax, cmap='YlOrRd', edgecolors='#0e1117', alpha=0.85)
            ax.set_title(f"Heatmap de Origens - {tipo_sel} | {time_sel}",
                         color='white', fontsize=13, pad=10)
            st.pyplot(fig); plt.close()
            st.caption(f"{len(df_coords):,} bolas paradas plotadas")

    with tab2:
        df_chutes = coordenadas_chutes(tipo=tipo_id, time_id=time_id,
                                       competicao_id=comp_id, temporada=temporada)
        if df_chutes.empty:
            st.warning("Sem finalizacoes para os filtros selecionados.")
        else:
            pitch = VerticalPitch(pitch_type='statsbomb', half=True,
                                  pitch_color='#1a1a2e', line_color='#aaaaaa')
            fig, ax = pitch.draw(figsize=(7, 8))
            fig.patch.set_facecolor('#0e1117')

            gols   = df_chutes[df_chutes['goals_scored'] == 1]
            outros = df_chutes[df_chutes['goals_scored'] == 0]

            pitch.scatter(outros['shot_x'], outros['shot_y'], ax=ax,
                         s=60, color='#4e9af1', alpha=0.5, edgecolors='white', linewidths=0.3)
            pitch.scatter(gols['shot_x'], gols['shot_y'], ax=ax,
                         s=120, color='#f4a031', alpha=0.95, edgecolors='white',
                         linewidths=0.5, marker='*')

            p1 = mpatches.Patch(color='#4e9af1', label='Chute sem gol')
            p2 = mpatches.Patch(color='#f4a031', label='Gol')
            ax.legend(handles=[p1, p2], facecolor='#1e2130', labelcolor='white',
                     loc='lower center', fontsize=9)
            ax.set_title(f"Finalizacoes - {tipo_sel} | {time_sel}",
                        color='white', fontsize=13, pad=10)
            st.pyplot(fig); plt.close()
            st.caption(f"{len(df_chutes):,} finalizacoes | {len(gols):,} gols")

# Por Faixa de Minuto
elif pagina == "Por Faixa de Minuto":
    st.header("Distribuicao por Faixa de Minuto")

    df_min = metricas_por_faixa_minuto(time_id=time_id, competicao_id=comp_id, temporada=temporada)

    col1, col2 = st.columns(2)

    with col1:
        # Volume total
        st.subheader("Volume de Bolas Paradas")
        fig, ax = dark_fig(5, 3.5)
        ax.bar(df_min['faixa_minuto'], df_min['total_bp'], color='#4e9af1')
        ax.set_xticklabels(df_min['faixa_minuto'], rotation=30, ha='right', color='white', fontsize=9)
        plt.tight_layout()
        st.pyplot(fig); plt.close()

    with col2:
        st.subheader("Gols por Faixa")
        fig, ax = dark_fig(5, 3.5)
        ax.bar(df_min['faixa_minuto'], df_min['gols'], color='#f4a031')
        ax.set_xticklabels(df_min['faixa_minuto'], rotation=30, ha='right', color='white', fontsize=9)
        plt.tight_layout()
        st.pyplot(fig); plt.close()

    st.subheader("xG Medio por Faixa")
    fig, ax = dark_fig(9, 3)
    bars = ax.bar(df_min['faixa_minuto'], df_min['xg_medio'], color='#b07cf4')
    ax.bar_label(bars, fmt='%.3f', padding=3, color='white', fontsize=8)
    ax.set_xticklabels(df_min['faixa_minuto'], rotation=30, ha='right', color='white', fontsize=9)
    plt.tight_layout()
    st.pyplot(fig); plt.close()

    st.divider()
    tabela = df_min.copy()
    tabela.columns = ['Faixa','Total BP','Gols','xG Medio']
    st.dataframe(tabela, use_container_width=True, hide_index=True)

# Ranking de Times
elif pagina == "Ranking de Times":
    st.header("Ranking de Times")

    n = st.slider("Quantidade de times", 5, 30, 15)
    df_times = metricas_por_time(competicao_id=comp_id, temporada=temporada, n=n)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Gols em Bola Parada")
        fig, ax = dark_fig(6, max(4, n * 0.35))
        y = np.arange(len(df_times))
        ax.barh(y, df_times['gols'], color='#f4a031')
        ax.set_yticks(y)
        ax.set_yticklabels(df_times['time'], color='white', fontsize=8)
        plt.tight_layout()
        st.pyplot(fig); plt.close()

    with col2:
        st.subheader("Taxa de Conversao (%)")
        fig, ax = dark_fig(6, max(4, n * 0.35))
        y = np.arange(len(df_times))
        ax.barh(y, df_times['TC'], color='#4e9af1')
        ax.set_yticks(y)
        ax.set_yticklabels(df_times['time'], color='white', fontsize=8)
        plt.tight_layout()
        st.pyplot(fig); plt.close()

    st.divider()
    tabela = df_times[['time','total_bp','finalizacoes','gols','TF','TC','xg_medio']].copy()
    tabela.columns = ['Time','Total BP','Finalizacoes','Gols','TF (%)','TC (%)','xG Medio']
    st.dataframe(tabela, use_container_width=True, hide_index=True)

# Evolucao por Temporada
elif pagina == "Evolucao por Temporada":
    st.header("Evolucao por Temporada")

    df_evo = evolucao_temporada(time_id=time_id, competicao_id=comp_id)
    if df_evo.empty:
        st.warning("Sem dados para os filtros selecionados.")
    else:
        df_evo['tipo_label'] = df_evo['tipo'].map(TIPO_LABELS).fillna(df_evo['tipo'])

        # Pivot para ter uma coluna por tipo, facilitando o gráfico de linhas
        df_vol = df_evo.pivot_table(index='temporada', columns='tipo_label',
                                    values='total_bp', aggfunc='sum').fillna(0)
        df_gols = df_evo.pivot_table(index='temporada', columns='tipo_label',
                                     values='gols', aggfunc='sum').fillna(0)

        st.subheader("Volume de Bolas Paradas por Temporada")
        fig, ax = dark_fig(12, 4)
        for col in df_vol.columns:
            ax.plot(df_vol.index, df_vol[col], marker='o', markersize=4, label=col)
        ax.legend(facecolor='#1e2130', labelcolor='white', fontsize=8)
        ax.set_xlabel('Temporada', color='white')
        plt.xticks(rotation=45, ha='right', color='white')
        plt.tight_layout()
        st.pyplot(fig); plt.close()

        st.subheader("Gols em Bola Parada por Temporada")
        fig, ax = dark_fig(12, 4)
        for col in df_gols.columns:
            ax.plot(df_gols.index, df_gols[col], marker='o', markersize=4, label=col)
        ax.legend(facecolor='#1e2130', labelcolor='white', fontsize=8)
        ax.set_xlabel('Temporada', color='white')
        plt.xticks(rotation=45, ha='right', color='white')
        plt.tight_layout()
        st.pyplot(fig); plt.close()

# Analise de Padroes (IRP)
elif pagina == "Analise de Padroes":
    st.header("Analise de Padroes - IRP")
    st.caption("Identifica clusters de finalizacao geradas em bolas paradas, revelando jogadas ensaiadas recorrentes.")

    if time_id is None:
        st.warning("Selecione um time no filtro para visualizar os padroes.")
    else:
        # O usuário controla quantos padrões quer visualizar
        k = st.slider("Numero de padroes (clusters)", 2, 6, 4)

        try:
            df_pts, resumo = padroes_por_time(time_id=time_id, tipo=tipo_id, k=k)
        except Exception as e:
            st.error(f"Dados insuficientes para o filtro selecionado: {e}")
            st.stop()

        if df_pts.empty:
            st.warning("Sem finalizacoes registradas para esse time com os filtros atuais.")
        else:
            # Cores fixas para cada cluster, até 6 padrões
            CORES_CLUSTER = ['#4e9af1','#f4a031','#4ecf7a','#e05c5c','#b07cf4','#f4d03f']

            # Mapa de campo
            pitch = VerticalPitch(pitch_type='statsbomb', half=True,
                                  pitch_color='#1a1a2e', line_color='#aaaaaa')
            fig, ax = pitch.draw(figsize=(7, 8))
            fig.patch.set_facecolor('#0e1117')

            for cl in sorted(df_pts['cluster'].unique()):
                sub = df_pts[df_pts['cluster'] == cl]
                cor = CORES_CLUSTER[cl % len(CORES_CLUSTER)]
                gols_sub   = sub[sub['goals_scored'] == 1]
                outros_sub = sub[sub['goals_scored'] == 0]

                # Finalizações sem gol como pontos, gols como estrelas
                pitch.scatter(outros_sub['shot_x'], outros_sub['shot_y'], ax=ax,
                             s=60, color=cor, alpha=0.55, edgecolors='white', linewidths=0.3,
                             label=f"Padrao {cl+1}")
                if len(gols_sub):
                    pitch.scatter(gols_sub['shot_x'], gols_sub['shot_y'], ax=ax,
                                 s=140, color=cor, alpha=1.0, edgecolors='white',
                                 linewidths=0.8, marker='*')

            ax.legend(facecolor='#1e2130', labelcolor='white', loc='lower center',
                     fontsize=9, ncol=k)
            ax.set_title(f"Padroes de Finalizacao - {time_sel} | {tipo_sel}",
                        color='white', fontsize=13, pad=10)
            st.pyplot(fig); plt.close()
            st.caption("Estrelas = gols. Cada cor representa um padrao recorrente de finalizacao.")

            st.divider()
            st.subheader("Resumo por Padrao")

            col1, col2 = st.columns(2)

            with col1:
                # Volume de finalizações por padrão
                fig, ax = dark_fig(5, 3.5)
                cores  = [CORES_CLUSTER[i % len(CORES_CLUSTER)] for i in resumo['cluster']]
                labels = [f"Padrao {i+1}" for i in resumo['cluster']]
                bars = ax.bar(labels, resumo['finalizacoes'], color=cores)
                ax.bar_label(bars, padding=3, color='white', fontsize=9)
                ax.set_title("Finalizacoes por Padrao", color='white', fontsize=11)
                ax.tick_params(colors='white')
                plt.tight_layout()
                st.pyplot(fig); plt.close()

            with col2:
                fig, ax = dark_fig(5, 3.5)
                bars = ax.bar(labels, resumo['TC'], color=cores)
                ax.bar_label(bars, fmt='%.1f%%', padding=3, color='white', fontsize=9)
                ax.set_title("Taxa de Conversao por Padrao (%)", color='white', fontsize=11)
                ax.tick_params(colors='white')
                plt.tight_layout()
                st.pyplot(fig); plt.close()

            # Tabela com todos os dados do resumo
            tabela = resumo[['cluster','finalizacoes','gols','TC','xg_medio','pct_total']].copy()
            tabela['cluster'] = tabela['cluster'].apply(lambda x: f"Padrao {x+1}")
            tabela.columns = ['Padrao','Finalizacoes','Gols','TC (%)','xG Medio','% do Total']
            st.dataframe(tabela, use_container_width=True, hide_index=True)