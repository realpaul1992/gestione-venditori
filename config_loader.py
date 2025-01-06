# config_loader.py
import yaml
from yaml.loader import SafeLoader

def load_db_config(config_file='config.yaml'):
    with open(config_file) as file:
        config = yaml.load(file, Loader=SafeLoader)
    return config['mysql']
