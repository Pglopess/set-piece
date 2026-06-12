# ⚽ SetPiece Analytics

Dashboard interativo para análise de **bolas paradas no futebol**, construído com Python e Streamlit utilizando os dados abertos da StatsBomb.

![SetPiece Analytics](https://i.imgur.com/mXPNDzr.png)

---

## Sobre o Projeto

O SetPiece Analytics permite explorar métricas ofensivas de bolas paradas (escanteios, faltas, pênaltis e arremessos laterais) com visualizações espaciais, rankings de times e identificação de padrões táticos por clustering.

### Páginas disponíveis

- **Visão Geral** — métricas gerais por tipo de bola parada (volume, gols, taxa de finalização, xG)
- **Análise Espacial** — heatmap de origens e mapa de finalizações no campo
- **Por Faixa de Minuto** — distribuição de volume, gols e xG ao longo do jogo
- **Ranking de Times** — times com mais gols e melhor taxa de conversão
- **Evolução por Temporada** — tendências ao longo das temporadas
- **Análise de Padrões** — identificação de jogadas ensaiadas via clustering (IRP)

---

## Tecnologias

- [Python 3.10+](https://www.python.org/)
- [Streamlit](https://streamlit.io/) — interface web
- [mplsoccer](https://mplsoccer.readthedocs.io/) — visualizações de campo
- [StatsBombPy](https://github.com/statsbomb/statsbombpy) — dados de futebol
- [Pandas](https://pandas.pydata.org/) + [NumPy](https://numpy.org/) — manipulação de dados
- [Matplotlib](https://matplotlib.org/) — gráficos

---

## Como Executar

### 1. Clone o repositório

```bash
git clone https://github.com/Pglopess/set-piece.git
cd set-piece
```

### 2. Crie um ambiente virtual (recomendado)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Gere o banco de dados

```bash
python etl.py
```

Isso vai processar o arquivo `data/set_pieces.parquet` e gerar o `.db` utilizado pelo app.

### 5. Execute o app

```bash
streamlit run app.py
```

O app vai abrir automaticamente no navegador em `http://localhost:8501`.

---

## Estrutura do Projeto

```
set-piece/
├── app.py            # Interface principal (Streamlit)
├── etl.py            # Carregamento e transformação dos dados StatsBomb
├── metrics.py        # Cálculo das métricas e queries
├── requirements.txt  # Dependências do projeto
└── .gitignore
```

---

## Filtros Disponíveis

No painel lateral do app é possível filtrar por:

- **Competição** — ex: Champions League, La Liga
- **Temporada**
- **Time**
- **Tipo de bola parada** — Escanteio, Falta Direta, Falta Indireta, Arremesso Lateral, Pênalti

---

## Dados

Os dados são provenientes do [StatsBomb Open Data](https://github.com/statsbomb/open-data), acessados via biblioteca `statsbombpy`. Nenhum download manual é necessário.