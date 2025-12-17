from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def make_cfg(db_url: str) -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "alembic")
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def test_migration_upgrade_and_downgrade(tmp_path: Path):
    db_url = f"sqlite:///{tmp_path/'mig.db'}"
    cfg = make_cfg(db_url)

    command.upgrade(cfg, "head")
    inspector = inspect(create_engine(db_url))
    assert "books" in inspector.get_table_names()

    command.downgrade(cfg, "base")
    inspector = inspect(create_engine(db_url))
    assert "books" not in inspector.get_table_names()
