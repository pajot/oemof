from sqlalchemy import create_engine
import keyring
from . import config as cfg
import logging


def connection():
    logging.error('You\'re using an outdated version of connection!')
    engine = create_engine(
        "postgresql+psycopg2://{user}:{passwd}@{host}:{port}/{db}".format(
            user=cfg.get("postGIS", "username"),
            passwd=keyring.get_password(
                cfg.get("postGIS", "database"),
                cfg.get("postGIS", "username")),
            host=cfg.get("postGIS", "host"),
            db=cfg.get("postGIS", "database"),
            port=int(cfg.get("postGIS", "port"))))
    return engine.connect()