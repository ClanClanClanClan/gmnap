import logging
import logging.config
import pathlib

p = pathlib.Path("config/logging.ini")
if p.exists():
    logging.config.fileConfig(p)
else:
    logging.basicConfig(level=logging.INFO)
