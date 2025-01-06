# verify_password.py

import bcrypt

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

if __name__ == "__main__":
    # Inserisci qui la password che stai utilizzando per il login
    plain_password = "Informatic1992.-"
    
    # Inserisci qui l'hash della password dal config.yaml
    hashed_password = "$2b$12$MUQY2jX69VgqGE2lfmb7huJIhhI0hAV6Tk2nEW9Is0DQAGna9nzta"
    
    if verify_password(plain_password, hashed_password):
        print("La password corrisponde all'hash.")
    else:
        print("La password NON corrisponde all'hash.")
