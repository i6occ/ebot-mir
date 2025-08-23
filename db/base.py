# -*- coding: utf-8 -*-
import os, importlib
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import config as cfg

def _dsn():
    if getattr(cfg, "DB_URL", None):
        return cfg.DB_URL
    data_dir = getattr(cfg, "DATA_DIR", "/root/Ebot/data")
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.abspath(os.path.join(data_dir, "ebot.db"))
    return f"sqlite:///{path}"

ENGINE = create_engine(_dsn(), echo=False, future=True)
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, future=True)

@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

def create_all():
    models = importlib.import_module("db.models")
    models.Base.metadata.create_all(bind=ENGINE)
