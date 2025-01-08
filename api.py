# api.py

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, EmailStr
import mysql.connector
from mysql.connector import Error
import os

app = FastAPI()

class Venditore(BaseModel):
    nome_cognome: str
    email: EmailStr
    telefono: str
    citta: str
    esperienza_vendita: int
    anno_nascita: int
    settore_esperienza: str
    partita_iva: str
    agente_isenarco: str
    cv: str = None  # Percorso al CV, opzionale
    note: str = None

def create_connection():
    """
    Crea una connessione al database MySQL utilizzando le variabili d'ambiente.
    """
    try:
        connection = mysql.connector.connect(
            host=os.environ['DB_HOST'],
            port=int(os.environ['DB_PORT']),
            database=os.environ['DB_DATABASE'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD']
        )
        if connection.is_connected():
            print("Connessione al database avvenuta con successo.")
            return connection
    except Error as e:
        print(f"Errore di connessione al database: {e}")
        return None

def add_settore(connection, nome_settore):
    """
    Aggiunge un nuovo settore al database se non esiste.
    """
    try:
        cursor = connection.cursor()
        query = """
            INSERT INTO settori (nome) 
            VALUES (%s) 
            ON DUPLICATE KEY UPDATE nome = nome
        """
        cursor.execute(query, (nome_settore,))
        connection.commit()
        cursor.close()
        print(f"Settore '{nome_settore}' inserito o già esistente.")
    except Error as e:
        print(f"Errore nell'aggiungere il settore '{nome_settore}': {e}")

def get_settore_id(connection, nome_settore):
    """
    Recupera l'ID del settore dato il nome.
    """
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT id FROM settori WHERE nome = %s", (nome_settore,))
        settore = cursor.fetchone()
        cursor.close()
        return settore[0] if settore else None
    except Error as e:
        print(f"Errore nel recuperare l'ID del settore '{nome_settore}': {e}")
        return None

def add_venditore(connection, venditore):
    """
    Aggiunge un nuovo venditore al database.
    """
    try:
        cursor = connection.cursor()
        query = """
            INSERT INTO venditori 
            (nome_cognome, email, telefono, citta, esperienza_vendita, 
             anno_nascita, settore_esperienza, partita_iva, agente_isenarco, cv, note, data_creazione)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE 
                nome_cognome = VALUES(nome_cognome),
                telefono = VALUES(telefono),
                citta = VALUES(citta),
                esperienza_vendita = VALUES(esperienza_vendita),
                anno_nascita = VALUES(anno_nascita),
                settore_esperienza = VALUES(settore_esperienza),
                partita_iva = VALUES(partita_iva),
                agente_isenarco = VALUES(agente_isenarco),
                cv = VALUES(cv),
                note = VALUES(note),
                data_creazione = NOW()
        """
        cursor.execute(query, (
            venditore.nome_cognome,
            venditore.email,
            venditore.telefono,
            venditore.citta,
            venditore.esperienza_vendita,
            venditore.anno_nascita,
            venditore.settore_id,
            venditore.partita_iva,
            venditore.agente_isenarco,
            venditore.cv,
            venditore.note
        ))
        connection.commit()
        cursor.close()
        print(f"Venditore '{venditore.nome_cognome}' inserito o aggiornato con successo.")
    except Error as e:
        print(f"Errore nell'aggiungere il venditore '{venditore.nome_cognome}': {e}")
        raise

@app.post("/inserisci_venditore")
async def inserisci_venditore(venditore: Venditore, authorization: str = Header(None)):
    """
    Endpoint per inserire o aggiornare un venditore.
    """
    expected_token = os.environ.get('API_TOKEN')
    if authorization != f"Bearer {expected_token}":
        raise HTTPException(status_code=403, detail="Accesso negato.")
    
    connection = create_connection()
    if not connection:
        raise HTTPException(status_code=500, detail="Errore di connessione al database.")
    
    try:
        # Aggiungi settore se non esiste
        add_settore(connection, venditore.settore_esperienza)
        
        # Recupera l'ID del settore
        settore_id = get_settore_id(connection, venditore.settore_esperienza)
        if not settore_id:
            raise HTTPException(status_code=500, detail=f"Settore '{venditore.settore_esperienza}' non trovato o non creato.")
        
        # Assegna l'ID del settore al venditore
        venditore.settore_id = settore_id
        
        # Aggiungi il venditore al database
        add_venditore(connection, venditore)
        
        return {"message": "Venditore inserito o aggiornato con successo."}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if connection.is_connected():
            connection.close()
            print("Connessione al database chiusa.")
