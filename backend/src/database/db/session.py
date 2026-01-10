from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config.config import Config


engine = create_engine(
    Config.database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)