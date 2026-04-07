from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# Extension singletons are initialized in create_app() to avoid circular imports.
db = SQLAlchemy()
migrate = Migrate()
