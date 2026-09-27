from app.db.base import Base
from app.db.session import engine
from app.models import *  # noqa: F401,F403

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Starter database schema created.")
