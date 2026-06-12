"""
Métricas SetPiece Analytics - fonte: SQLite populado pelo parquet do Carlos.
"""

import sqlite3
import pandas as pd

DB_PATH = "data/setpiece.db"


def get_conn():
    return sqlite3.connect(DB_PATH)


# ── Listas para filtros ───────────────────────────────────────────────────────

def lista_times():
    conn = get_conn()
    df = pd.read_sql("SELECT id_time, nome FROM times ORDER BY nome", conn)
    conn.close()
    return df


def lista_competicoes():
    conn = get_conn()
    df = pd.read_sql("SELECT id_competicao, nome FROM competicoes ORDER BY nome", conn)
    conn.close()
    return df


def lista_temporadas(competicao_id=None):
    conn = get_conn()
    if competicao_id:
        df = pd.read_sql(
            "SELECT DISTINCT temporada FROM partidas WHERE id_competicao=? ORDER BY temporada",
            conn, params=[competicao_id]
        )
    else:
        df = pd.read_sql("SELECT DISTINCT temporada FROM partidas ORDER BY temporada", conn)
    conn.close()
    return df


# ── Métricas principais ───────────────────────────────────────────────────────

def metricas_por_tipo(time_id=None, competicao_id=None, temporada=None):
    conn = get_conn()
    filtros, params = _filtros(time_id, competicao_id, temporada)
    where = ("WHERE " + " AND ".join(filtros)) if filtros else ""

    df = pd.read_sql(f"""
        SELECT
            bp.tipo,
            COUNT(bp.id_bp)                                      AS total_bp,
            SUM(e.shots_generated)                               AS finalizacoes,
            SUM(e.goals_scored)                                  AS gols,
            ROUND(AVG(CASE WHEN e.xg_sum > 0 THEN e.xg_sum END), 4) AS xg_medio
        FROM bolas_paradas bp
        JOIN eventos e ON e.id_bp = bp.id_bp
        JOIN partidas p ON p.id_partida = bp.id_partida
        {where}
        GROUP BY bp.tipo
        ORDER BY total_bp DESC
    """, conn, params=params)
    conn.close()

    df['TF'] = (df['finalizacoes'] / df['total_bp'] * 100).round(1)
    df['TC'] = (df['gols'] / df['total_bp'] * 100).round(1)
    df['xg_medio'] = df['xg_medio'].round(3)
    return df


def metricas_por_faixa_minuto(time_id=None, competicao_id=None, temporada=None):
    conn = get_conn()
    filtros, params = _filtros(time_id, competicao_id, temporada)
    where = ("WHERE " + " AND ".join(filtros)) if filtros else ""

    df = pd.read_sql(f"""
        SELECT
            bp.faixa_minuto,
            COUNT(bp.id_bp)      AS total_bp,
            SUM(e.goals_scored)  AS gols,
            ROUND(AVG(CASE WHEN e.xg_sum > 0 THEN e.xg_sum END), 4) AS xg_medio
        FROM bolas_paradas bp
        JOIN eventos e ON e.id_bp = bp.id_bp
        JOIN partidas p ON p.id_partida = bp.id_partida
        {where}
        GROUP BY bp.faixa_minuto
        ORDER BY bp.faixa_minuto
    """, conn, params=params)
    conn.close()
    return df


def metricas_por_time(competicao_id=None, temporada=None, n=15):
    conn = get_conn()
    filtros, params = _filtros(None, competicao_id, temporada)
    where = ("WHERE " + " AND ".join(filtros)) if filtros else ""

    df = pd.read_sql(f"""
        SELECT
            t.nome                                               AS time,
            COUNT(bp.id_bp)                                      AS total_bp,
            SUM(e.shots_generated)                               AS finalizacoes,
            SUM(e.goals_scored)                                  AS gols,
            ROUND(AVG(CASE WHEN e.xg_sum > 0 THEN e.xg_sum END), 4) AS xg_medio
        FROM bolas_paradas bp
        JOIN eventos e ON e.id_bp = bp.id_bp
        JOIN partidas p ON p.id_partida = bp.id_partida
        JOIN times t ON t.id_time = bp.id_time
        {where}
        GROUP BY t.nome
        ORDER BY gols DESC
        LIMIT ?
    """, conn, params=params + [n])
    conn.close()

    df['TF'] = (df['finalizacoes'] / df['total_bp'] * 100).round(1)
    df['TC'] = (df['gols'] / df['total_bp'] * 100).round(1)
    return df


def evolucao_temporada(time_id=None, competicao_id=None):
    conn = get_conn()
    filtros, params = _filtros(time_id, competicao_id, None)
    where = ("WHERE " + " AND ".join(filtros)) if filtros else ""

    df = pd.read_sql(f"""
        SELECT
            p.temporada,
            bp.tipo,
            COUNT(bp.id_bp)     AS total_bp,
            SUM(e.goals_scored) AS gols
        FROM bolas_paradas bp
        JOIN eventos e ON e.id_bp = bp.id_bp
        JOIN partidas p ON p.id_partida = bp.id_partida
        {where}
        GROUP BY p.temporada, bp.tipo
        ORDER BY p.temporada
    """, conn, params=params)
    conn.close()
    return df


def coordenadas_bp(tipo=None, time_id=None, competicao_id=None, temporada=None):
    conn = get_conn()
    filtros, params = _filtros(time_id, competicao_id, temporada)
    filtros.append("bp.coord_x IS NOT NULL")
    if tipo:
        filtros.append("bp.tipo = ?")
        params.append(tipo)
    where = "WHERE " + " AND ".join(filtros)

    df = pd.read_sql(f"""
        SELECT bp.coord_x, bp.coord_y, bp.tipo
        FROM bolas_paradas bp
        JOIN partidas p ON p.id_partida = bp.id_partida
        {where}
    """, conn, params=params)
    conn.close()
    return df


def coordenadas_chutes(tipo=None, time_id=None, competicao_id=None, temporada=None):
    conn = get_conn()
    filtros, params = _filtros(time_id, competicao_id, temporada)
    filtros.append("e.shot_x IS NOT NULL")
    if tipo:
        filtros.append("bp.tipo = ?")
        params.append(tipo)
    where = "WHERE " + " AND ".join(filtros)

    df = pd.read_sql(f"""
        SELECT e.shot_x, e.shot_y, e.goals_scored, e.xg_sum, bp.tipo
        FROM eventos e
        JOIN bolas_paradas bp ON bp.id_bp = e.id_bp
        JOIN partidas p ON p.id_partida = bp.id_partida
        {where}
    """, conn, params=params)
    conn.close()
    return df


# ── Helper interno ────────────────────────────────────────────────────────────

def _filtros(time_id, competicao_id, temporada):
    filtros, params = [], []
    if time_id:
        filtros.append("bp.id_time = ?")
        params.append(time_id)
    if competicao_id:
        filtros.append("p.id_competicao = ?")
        params.append(competicao_id)
    if temporada:
        filtros.append("p.temporada = ?")
        params.append(temporada)
    return filtros, params


if __name__ == "__main__":
    print("=== Metricas por tipo ===")
    print(metricas_por_tipo().to_string(index=False))
    print("\n=== Top times por gols ===")
    print(metricas_por_time(n=8).to_string(index=False))
    print("\n=== Por faixa de minuto ===")
    print(metricas_por_faixa_minuto().to_string(index=False))


# ── Análise de Padrões (IRP) ──────────────────────────────────────────────────

def padroes_por_time(time_id, tipo=None, k=4):
    """
    Clusteriza as finalizações geradas por um time em bolas paradas.
    Retorna o DataFrame com coluna 'cluster' e o resumo por cluster.
    """
    from sklearn.cluster import KMeans

    conn = get_conn()
    filtros = ["bp.id_time = ?", "e.shot_x IS NOT NULL"]
    params  = [time_id]
    if tipo:
        filtros.append("bp.tipo = ?")
        params.append(tipo)

    where = "WHERE " + " AND ".join(filtros)

    df = pd.read_sql(f"""
        SELECT
            bp.coord_x AS origem_x,
            bp.coord_y AS origem_y,
            e.shot_x,
            e.shot_y,
            e.goals_scored,
            e.xg_sum,
            bp.tipo
        FROM bolas_paradas bp
        JOIN eventos e ON e.id_bp = bp.id_bp
        {where}
    """, conn, params=params)
    conn.close()

    if len(df) < k * 3:
        k = max(2, len(df) // 3)

    coords = df[['shot_x', 'shot_y']].values
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    df['cluster'] = km.fit_predict(coords)

    resumo = df.groupby('cluster').agg(
        finalizacoes=('cluster', 'count'),
        gols=('goals_scored', 'sum'),
        xg_medio=('xg_sum', 'mean'),
        shot_x_medio=('shot_x', 'mean'),
        shot_y_medio=('shot_y', 'mean'),
    ).round(3).reset_index()

    resumo['TC'] = (resumo['gols'] / resumo['finalizacoes'] * 100).round(1)
    resumo['pct_total'] = (resumo['finalizacoes'] / resumo['finalizacoes'].sum() * 100).round(1)

    return df, resumo
