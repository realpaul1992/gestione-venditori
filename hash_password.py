# hash_password.py

import bcrypt

def hash_password(plain_password):
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')

if __name__ == "__main__":
    password = "Informatic1992.-"  # 🔒 Sostituisci con la tua password reale
    print(hash_password(password))

