"""
ETL: set_pieces.parquet -> SQLite
Lê o parquet gerado pelo Carlos e popula o banco seguindo
o schema relacional do relatório SetPiece Analytics.
"""

import sqlite3
import pandas as pd
import hashlib
import os

PARQUET_PATH = "data/set_pieces.parquet"
DB_PATH      = "data/setpiece.db"

TIPO_MAP = {
    "Escanteio":     "escanteio",
    "Falta Indireta":"falta_indireta",
    "Falta Direta":  "falta_direta",
    "Lateral":       "arremesso_lateral",
    "Penalti":       "penalti",
}


def criar_banco(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS competicoes (
        id_competicao  TEXT PRIMARY KEY,
        nome           TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS times (
        id_time  TEXT PRIMARY KEY,
        nome     TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS partidas (
        id_partida       TEXT PRIMARY KEY,
        id_competicao    TEXT REFERENCES competicoes(id_competicao),
        temporada        TEXT,
        id_time_mandante TEXT,
        id_time_visitante TEXT
    );

    CREATE TABLE IF NOT EXISTS bolas_paradas (
        id_bp         TEXT PRIMARY KEY,
        id_partida    TEXT REFERENCES partidas(id_partida),
        id_time       TEXT REFERENCES times(id_time),
        tipo          TEXT,
        minuto        INTEGER,
        faixa_minuto  TEXT,
        periodo       INTEGER,
        coord_x       REAL,
        coord_y       REAL,
        zona_campo    TEXT
    );

    CREATE TABLE IF NOT EXISTS eventos (
        id_evento        TEXT PRIMARY KEY,
        id_bp            TEXT REFERENCES bolas_paradas(id_bp),
        shots_generated  INTEGER,
        goals_scored     INTEGER,
        xg_sum           REAL,
        shot_x           REAL,
        shot_y           REAL
    );
    """)
    conn.commit()


def zona_campo(x, y):
    if x is None or pd.isna(x):
        return None
    if x < 40:
        return "terco_defensivo"
    elif x < 80:
        return "terco_medio"
    elif y < 27:
        return "terco_ofensivo_esquerdo"
    elif y > 53:
        return "terco_ofensivo_direito"
    else:
        return "terco_ofensivo_central"


def make_id(*parts):
    """Gera ID estável a partir de campos concatenados."""
    key = "_".join(str(p) for p in parts)
    return hashlib.md5(key.encode()).hexdigest()[:16]


def main():
    if not os.path.exists(PARQUET_PATH):
        print(f"ERRO: {PARQUET_PATH} nao encontrado.")
        print("Baixe o arquivo set_pieces.parquet do repositorio do Carlos e coloque em data/")
        return

    print(f"Lendo {PARQUET_PATH}...")
    df = pd.read_parquet(PARQUET_PATH)
    print(f"  {len(df):,} registros carregados")
    print(f"  Competicoes: {df['competition_name'].nunique()}")
    print(f"  Times: {df['team_name'].nunique()}")
    print(f"  Partidas: {df['match_id'].nunique()}")

    # Mapear tipo
    df['tipo'] = df['set_piece_type'].map(TIPO_MAP).fillna(df['set_piece_type'].str.lower())

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"\nBanco anterior removido.")

    conn = sqlite3.connect(DB_PATH)
    criar_banco(conn)
    print("Schema criado.\n")

    # Competicoes
    comps = df[['competition_name']].drop_duplicates()
    for _, row in comps.iterrows():
        cid = make_id(row['competition_name'])
        conn.execute("INSERT OR IGNORE INTO competicoes VALUES (?,?)",
                     (cid, row['competition_name']))
    conn.commit()
    print(f"Competicoes inseridas: {len(comps)}")

    # Times
    times = df[['team_name']].drop_duplicates()
    for _, row in times.iterrows():
        tid = make_id(row['team_name'])
        conn.execute("INSERT OR IGNORE INTO times VALUES (?,?)",
                     (tid, row['team_name']))
    conn.commit()
    print(f"Times inseridos: {len(times)}")

    # Partidas (match_id + competition + season é suficiente; times não estão no parquet por partida)
    partidas = df[['match_id','competition_name','season_name']].drop_duplicates('match_id')
    for _, row in partidas.iterrows():
        cid = make_id(row['competition_name'])
        conn.execute("INSERT OR IGNORE INTO partidas VALUES (?,?,?,?,?)",
                     (str(row['match_id']), cid, row['season_name'], None, None))
    conn.commit()
    print(f"Partidas inseridas: {len(partidas)}")

    # Bolas paradas + eventos
    print(f"\nInserindo {len(df):,} bolas paradas e eventos...")
    bp_batch  = []
    ev_batch  = []

    for i, row in df.iterrows():
        id_bp    = make_id(row['match_id'], row['team_name'], row['set_piece_type'],
                           row['period'], row['minute'])
        id_time  = make_id(row['team_name'])
        zona     = zona_campo(row['origin_x'], row['origin_y'])
        id_ev    = make_id(id_bp, 'evento')

        bp_batch.append((
            id_bp,
            str(row['match_id']),
            id_time,
            row['tipo'],
            int(row['minute']),
            row['minute_band'],
            int(row['period']),
            row['origin_x'] if pd.notna(row['origin_x']) else None,
            row['origin_y'] if pd.notna(row['origin_y']) else None,
            zona,
        ))

        ev_batch.append((
            id_ev,
            id_bp,
            int(row['shots_generated']),
            int(row['goals_scored']),
            float(row['xg_sum']) if pd.notna(row['xg_sum']) else 0.0,
            float(row['shot_x']) if pd.notna(row['shot_x']) else None,
            float(row['shot_y']) if pd.notna(row['shot_y']) else None,
        ))

        if len(bp_batch) >= 1000:
            conn.executemany("INSERT OR IGNORE INTO bolas_paradas VALUES (?,?,?,?,?,?,?,?,?,?)", bp_batch)
            conn.executemany("INSERT OR IGNORE INTO eventos VALUES (?,?,?,?,?,?,?)", ev_batch)
            conn.commit()
            bp_batch.clear()
            ev_batch.clear()

    if bp_batch:
        conn.executemany("INSERT OR IGNORE INTO bolas_paradas VALUES (?,?,?,?,?,?,?,?,?,?)", bp_batch)
        conn.executemany("INSERT OR IGNORE INTO eventos VALUES (?,?,?,?,?,?,?)", ev_batch)
        conn.commit()

    print("\n--- Banco populado ---")
    for tabela in ['competicoes','times','partidas','bolas_paradas','eventos']:
        count = conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
        print(f"  {tabela}: {count:,} registros")

    conn.close()
    print(f"\nETL concluido. Banco salvo em {DB_PATH}")


if __name__ == "__main__":
    main()
