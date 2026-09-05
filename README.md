

| Материал | Ссылка |
|----------|--------|
| Отчёт с графиками | [docs/otchet.md](docs/otchet.md) |
| Модель данных | [docs/model.md](docs/model.md) |
| Что и как запускать | [docs/demo.md](docs/demo.md) |
| Код ETL / анализ | [superstore/](superstore/README.md) |
| SQL-запросы | [sql/](sql/README.md) |
| DAG Airflow | [dags/superstore_etl.py](dags/superstore_etl.py) |

---

## Быстрый старт (локально)

```powershell
git clone https://github.com/lllexalllepexa/testsomeshi.git
cd testsomeshi
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```


```powershell
python -m superstore.etl.load_and_clean
.\scripts\run_streamlit.ps1
```

---

## Команды

### Основное (без Docker)

| Действие | Команда |
|----------|---------|
| ETL | `python -m superstore.etl.load_and_clean` |
| Качество данных | `python -m superstore.etl.data_quality_runner` |
| EDA, графики | `python -m superstore.analysis.eda` |
| Статистика | `python -m superstore.analysis.stats_models` |
| Тесты | `pytest tests/ -q` |
| Дашборд | `.\scripts\run_streamlit.ps1` |
| SQL (DuckDB) | `.\scripts\sql_duckdb_demo.ps1` |
| R | `Rscript r/analysis.R` |
| Пайплайн целиком | `.\scripts\run_pipeline.ps1` |

### С Docker

| Действие | Команда |
|----------|---------|
| PostgreSQL | `.\scripts\run_postgres.ps1` |
| Airflow | `.\scripts\run_airflow_docker.ps1` |



| Действие | Команда |
|----------|---------|
| Spark | `pip install pyspark` → `python spark/run_pyspark.py` |
| ChromaDB | `pip install chromadb sentence-transformers` → `python -m superstore.embeddings.chroma_products` |
| Jupyter | `jupyter notebook notebooks/01_eda_overview.ipynb` |

Подробнее: [docs/demo.md](docs/demo.md) · Postgres/Docker: [docs/sql_postgres.md](docs/sql_postgres.md)

---

## Структура

```
testsomeshi/
├── superstore/      Python: ETL, анализ, загрузчики
├── dashboard/       Streamlit
├── sql/             PostgreSQL, DuckDB, ClickHouse, Greenplum
├── spark/           Spark SQL
├── dags/            Airflow
├── r/               R
├── docs/            отчёты и PNG для GitHub
├── data/            данные (CSV не в git)
├── scripts/         скрипты запуска
├── notebooks/
└── tests/
```

## Стек

Python · Pandas · SQL · DuckDB · R · Streamlit · Spark · Airflow · Docker
