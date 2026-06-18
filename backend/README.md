# Flying Foods ERP Backend

Django/DRF backend for the Flying Foods restaurant and inventory system.

Install with `pip install -e ".[dev]"`, copy `.env.example` to `.env`, then run:

```powershell
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Run checks with:

```powershell
pytest
python manage.py makemigrations --check --dry-run
python manage.py check
```
