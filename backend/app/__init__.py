# Re-export the application instance from app.main so startup lifecycle (DB init + migrations)
# is always executed, regardless of the import target (app:app vs app.main:app).
from .main import app
