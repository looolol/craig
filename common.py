import os
import json
import logging

ID_FILE = 'processed_ids.json'


def setup_logging(name=None):
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        handler = logging.StreamHandler()  # Log to console
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)  # Set log level

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
