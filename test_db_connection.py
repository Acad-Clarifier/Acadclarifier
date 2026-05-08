import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from apps.backend.config import Config
print('Database URI:', Config.SQLALCHEMY_DATABASE_URI)

# Try to connect
import sqlalchemy
engine = sqlalchemy.create_engine(Config.SQLALCHEMY_DATABASE_URI)
with engine.connect() as conn:
    result = conn.execute(sqlalchemy.text('SELECT name FROM sqlite_master WHERE type="table"'))
    tables = result.fetchall()
    print('Tables found:', [row[0] for row in tables])
    print('✅ Database connection successful!')
