# Med-Z4 Application Implementation Roadmap

Create database connection
```text
database.py (SQLAlchemy engine)
```

Test connection to medz1 database:
```python
from database import engine
with engine.connect() as conn:
    result = conn.execute("SELECT 1")
    print("Database connected!")
```

Verification
```bash
# Database test script connects without errors
python -c "from config import DATABASE_URL; print('Config OK')"
```
