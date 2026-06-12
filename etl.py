"""
ETL do SetPiece Analytics
Lê o arquivo parquet gerado pelo grupo e popula o banco SQLite
seguindo o modelo relacional definido no relatório.
"""

import sqlite3
import pandas as pd
import hashlib
import os

PARQUET_PATH = "data/set_pieces.parquet"
DB_PATH      = "data/setpiece.db"

# Mapeamento dos nomes do parquet para os nomes padronizados no banco
TIPO_MAP = {
    "Escanteio":      "escanteio",
    "Falta Indireta": "falta_indireta",
    "Falta Direta":   "falta_direta",
    "Lateral":        "arremesso_lateral",
    "Penalti":        "penalti",
}


def criar_banco(conn):
    # Cria as tabelas do banco caso ainda não existam
    # O schema segue o modelo relacional do relatório com 5 entidades principais
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS competicoes (
        id_competicao  TEXT PRIMARY KEY,
        nome           TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS times (
        id_time  TEXT PRIMARY KEY,
        nome     TEXT NOT NULL
    );

    -- Cada partida pertence a uma competição e tem uma temporada associada
    CREATE TABLE IF NOT EXISTS partidas (
        id_partida        TEXT PRIMARY KEY,
        id_competicao     TEXT REFERENCES competicoes(id_competicao),
        temporada         TEXT,
        id_time_mandante  TEXT,
        id_time_visitante TEXT
    );

    -- Cada bola parada pertence a uma partida e a um time
    -- Guarda coordenadas de origem e a zona do campo calculada
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

    -- Cada evento representa o resultado de uma bola parada:
    -- quantas finalizações gerou, se teve gol, o xG total e onde foi o chute
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
    # Classifica a coordenada de origem em uma zona tática do campo
    # O campo StatsBomb tem dimensões 120x80
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
    # Gera um ID único e estável a partir de campos concatenados
    # Usamos MD5 só para encurtar o identificador
    key = "_".join(str(p) for p in parts)
    return hashlib.md5(key.encode()).hexdigest()[:16]


def main():
    if not os.path.exists(PARQUET_PATH):
        print(f"ERRO: {PARQUET_PATH} nao encontrado.")
        print("Baixe o arquivo set_pieces.parquet do repositorio e coloque em data/")
        return

    print(f"Lendo {PARQUET_PATH}...")
    df = pd.read_parquet(PARQUET_PATH)
    print(f"  {len(df):,} registros carregados")
    print(f"  Competicoes: {df['competition_name'].nunique()}")
    print(f"  Times: {df['team_name'].nunique()}")
    print(f"  Partidas: {df['match_id'].nunique()}")

    # Converte os nomes do parquet para o padrão do banco
    df['tipo'] = df['set_piece_type'].map(TIPO_MAP).fillna(df['set_piece_type'].str.lower())

    # Remove o banco antigo antes de recriar para evitar conflitos de schema
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"\nBanco anterior removido.")

    conn = sqlite3.connect(DB_PATH)
    criar_banco(conn)
    print("Schema criado.\n")

    # Insere as competições únicas
    comps = df[['competition_name']].drop_duplicates()
    for _, row in comps.iterrows():
        cid = make_id(row['competition_name'])
        conn.execute("INSERT OR IGNORE INTO competicoes VALUES (?,?)",
                     (cid, row['competition_name']))
    conn.commit()
    print(f"Competicoes inseridas: {len(comps)}")

    # Insere os times únicos
    times = df[['team_name']].drop_duplicates()
    for _, row in times.iterrows():
        tid = make_id(row['team_name'])
        conn.execute("INSERT OR IGNORE INTO times VALUES (?,?)",
                     (tid, row['team_name']))
    conn.commit()
    print(f"Times inseridos: {len(times)}")

    # Insere as partidas únicas vinculadas à competição correspondente
    partidas = df[['match_id','competition_name','season_name']].drop_duplicates('match_id')
    for _, row in partidas.iterrows():
        cid = make_id(row['competition_name'])
        conn.execute("INSERT OR IGNORE INTO partidas VALUES (?,?,?,?,?)",
                     (str(row['match_id']), cid, row['season_name'], None, None))
    conn.commit()
    print(f"Partidas inseridas: {len(partidas)}")

    # Insere bolas paradas e eventos em lotes de 1000 para melhor desempenho
    print(f"\nInserindo {len(df):,} bolas paradas e eventos...")
    bp_batch = []
    ev_batch = []

    for i, row in df.iterrows():
        # O ID da bola parada combina partida, time, tipo, período e minuto
        id_bp   = make_id(row['match_id'], row['team_name'], row['set_piece_type'],
                          row['period'], row['minute'])
        id_time = make_id(row['team_name'])
        zona    = zona_campo(row['origin_x'], row['origin_y'])
        id_ev   = make_id(id_bp, 'evento')

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

        # Commit em lote para não travar o banco com uma transação gigante
        if len(bp_batch) >= 1000:
            conn.executemany("INSERT OR IGNORE INTO bolas_paradas VALUES (?,?,?,?,?,?,?,?,?,?)", bp_batch)
            conn.executemany("INSERT OR IGNORE INTO eventos VALUES (?,?,?,?,?,?,?)", ev_batch)
            conn.commit()
            bp_batch.clear()
            ev_batch.clear()

    # Insere o restante
    if bp_batch:
        conn.executemany("INSERT OR IGNORE INTO bolas_paradas VALUES (?,?,?,?,?,?,?,?,?,?)", bp_batch)
        conn.executemany("INSERT OR IGNORE INTO eventos VALUES (?,?,?,?,?,?,?)", ev_batch)
        conn.commit()

    # Exibe o resumo final do banco populado
    print("\n--- Banco populado ---")
    for tabela in ['competicoes','times','partidas','bolas_paradas','eventos']:
        count = conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
        print(f"  {tabela}: {count:,} registros")

    conn.close()
    print(f"\nETL concluido. Banco salvo em {DB_PATH}")


if __name__ == "__main__":
    main()