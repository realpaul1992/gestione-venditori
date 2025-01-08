# api.py

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, EmailStr
from typing import Optional
import os
from dotenv import load_dotenv
from db_connection import (
    create_connection,
    add_venditore,
    add_settore,
    get_settori
)
import logging

# Configura il logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

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
    cv: Optional[str] = None
    note: Optional[str] = None

class Settore(BaseModel):
    settore: str

@app.get("/test")
def test_endpoint():
    return {"status": "API is working!"}

@app.post("/inserisci_venditore")
def inserisci_venditore(
    venditore: Venditore,
    authorization: str = Header(None)
):
    # Autenticazione
    expected_token = os.getenv('API_TOKEN')
    if not expected_token:
        logger.error("API_TOKEN non configurato.")
        raise HTTPException(status_code=500, detail="API_TOKEN non configurato.")
    
    if not authorization or authorization != f"Bearer {expected_token}":
        logger.warning(f"Tentativo di accesso non autorizzato con token: {authorization}")
        raise HTTPException(status_code=403, detail="Accesso negato.")
    
    # Connessione al database
    connection = create_connection()
    if not connection:
        logger.error("Impossibile connettersi al database.")
        raise HTTPException(status_code=500, detail="Impossibile connettersi al database.")
    
    # Verifica se il settore esiste nella tabella Settori
    try:
        cursor = connection.cursor()
        query_settore = "SELECT nome FROM Settori WHERE nome = %s"
        cursor.execute(query_settore, (venditore.settore_esperienza,))
        result = cursor.fetchone()
        if not result:
            # Settore non esiste, quindi aggiungilo
            successo_settore = add_settore(connection, venditore.settore_esperienza)
            if successo_settore:
                logger.info(f"Settore '{venditore.settore_esperienza}' aggiunto al database.")
            else:
                logger.error(f"Errore nell'aggiungere il settore '{venditore.settore_esperienza}'.")
                raise HTTPException(status_code=500, detail="Errore nell'aggiungere il settore.")
        cursor.close()
    except Exception as e:
        logger.exception(f"Errore nella verifica del settore: {e}")
        connection.close()
        raise HTTPException(status_code=500, detail=f"Errore nella verifica del settore: {e}")
    
    # Prepara i dati per l'inserimento
    venditore_data = {
        "nome_cognome": venditore.nome_cognome,
        "email": venditore.email,
        "telefono": venditore.telefono,
        "citta": venditore.citta,
        "esperienza_vendita": venditore.esperienza_vendita,
        "anno_nascita": venditore.anno_nascita,
        "settore_esperienza": venditore.settore_esperienza,
        "partita_iva": venditore.partita_iva,
        "agente_isenarco": venditore.agente_isenarco,
        "cv": venditore.cv if venditore.cv else "",
        "note": venditore.note if venditore.note else ""
    }
    
    # Inserisci o aggiorna il venditore nel database
    try:
        successo = add_venditore(connection, venditore_data)
        connection.close()
        if successo:
            logger.info(f"Venditore '{venditore.email}' inserito o aggiornato con successo.")
            return {"message": "Venditore inserito o aggiornato con successo."}
        else:
            logger.error(f"Errore nell'inserimento del venditore '{venditore.email}'.")
            raise HTTPException(status_code=500, detail="Errore nell'inserimento del venditore.")
    except Exception as e:
        logger.exception(f"Errore durante l'inserimento/aggiornamento del venditore: {e}")
        connection.close()
        raise HTTPException(status_code=500, detail="Errore nell'inserimento del venditore.")

@app.post("/aggiungi_settore")
def aggiungi_settore_endpoint(
    settore: Settore,
    authorization: str = Header(None)
):
    # Autenticazione
    expected_token = os.getenv('API_TOKEN')
    if not expected_token:
        logger.error("API_TOKEN non configurato.")
        raise HTTPException(status_code=500, detail="API_TOKEN non configurato.")
    
    if not authorization or authorization != f"Bearer {expected_token}":
        logger.warning(f"Tentativo di accesso non autorizzato con token: {authorization}")
        raise HTTPException(status_code=403, detail="Accesso negato.")
    
    # Connessione al database
    connection = create_connection()
    if not connection:
        logger.error("Impossibile connettersi al database.")
        raise HTTPException(status_code=500, detail="Impossibile connettersi al database.")
    
    # Aggiungi il settore nel database
    try:
        successo = add_settore(connection, settore.settore)
        connection.close()
        if successo:
            logger.info(f"Settore '{settore.settore}' aggiunto con successo.")
            return {"message": f"Settore '{settore.settore}' aggiunto con successo."}
        else:
            logger.warning(f"Settore '{settore.settore}' già esistente o errore nell'inserimento.")
            raise HTTPException(status_code=400, detail=f"Settore '{settore.settore}' già esistente o errore nell'inserimento.")
    except Exception as e:
        logger.exception(f"Errore durante l'aggiunta del settore: {e}")
        connection.close()
        raise HTTPException(status_code=500, detail=f"Errore durante l'aggiunta del settore: {e}")
