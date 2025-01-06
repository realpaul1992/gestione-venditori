# generate_key.py

import secrets

def generate_key():
    return secrets.token_hex(16)

if __name__ == "__main__":
    print(generate_key())
