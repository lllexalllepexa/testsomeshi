# Скрипты

[`check.py`](check.py) — всё, что сделал бы CI: линтер Ruff, проверка форматирования и все тесты.

```bash
python scripts/check.py
```

Тот же скрипт запускается перед каждым коммитом через pre-commit (`pre-commit install` один раз после установки).
