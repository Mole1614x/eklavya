from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

configuration = settings()
engine_options = {"pool_pre_ping": True}
if not configuration.database_url.startswith("sqlite"):
    engine_options.update({
        "pool_size": configuration.database_pool_size,
        "max_overflow": configuration.database_max_overflow,
        "pool_timeout": configuration.database_pool_timeout_seconds,
        "pool_recycle": 1800,
    })
engine = create_engine(configuration.database_url, **engine_options)
Session = sessionmaker(engine)


class Base(DeclarativeBase):
    pass
