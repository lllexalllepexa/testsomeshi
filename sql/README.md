# SQL

| Каталог | СУБД | Как запустить |
|---------|-----|----------------|
| `duckdb/` | DuckDB | `.\scripts\sql_duckdb_demo.ps1` (без Docker) |
| `postgres/` | PostgreSQL | `docker compose up -d postgres` → `.\scripts\run_postgres.ps1` |
| `clickhouse/` | ClickHouse | `docker compose up -d clickhouse` |
| `greenplum/` | Greenplum | примеры MPP-SQL (кластер не обязателен) |

Spark: [../spark/README.md](../spark/README.md).
