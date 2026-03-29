import logging, logging.config, pathlib

p = pathlib.Path("config/logging.ini")
if p.exists():
    logging.config.fileConfig(p)
else:
    logging.basicConfig(level=logging.INFO)
