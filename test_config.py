# test_config.py

import yaml

def test_load_config():
    try:
        with open('config.yaml') as file:
            config = yaml.load(file, Loader=yaml.SafeLoader)
        print("Config Caricata Correttamente:")
        print(config)
    except Exception as e:
        print(f"Errore nel caricamento del config.yaml: {e}")

if __name__ == "__main__":
    test_load_config()
