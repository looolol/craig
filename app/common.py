import os
import json
import logging
from logging.handlers import TimedRotatingFileHandler

ID_FILE = os.getenv('ID_FILE')
LOG_FILE = os.getenv('LOG_FILE')

RATE_LIMIT_STATUS = int(os.getenv('RATE_LIMIT_STATUS'))


def setup_logging(name=None, level=logging.INFO, filename=LOG_FILE, when='midnight', interval=1, backup_count=7):
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        if filename:
            handler = TimedRotatingFileHandler(
                filename, when=when, interval=interval, backupCount=backup_count
            )
        else:
            handler = logging.StreamHandler()

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)

    return logger



def decode_url(url):
    return url.replace("&amp;", "&")


def get_entry_id(entry):
    if '/' not in entry.id:
        return entry.id
    else:
        entry.id = entry.id.split('/')[-1].split("_")[-1]
        return entry.id


def load_processed_ids():
    if os.path.exists(ID_FILE):
        with open(ID_FILE, 'r') as file:
            return set(json.load(file))
    return set()


def save_processed_ids(ids):
    with open(ID_FILE, 'w') as file:
        json.dump(list(ids), file)
