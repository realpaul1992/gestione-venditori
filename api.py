# api.py

from fastapi import FastAPI, HTTPException, Header, File, UploadFile
from pydantic import BaseModel, EmailStr
from typing import Optional
import os
import shutil
from db_connection import (
    create_connection,
    add_venditore,
    add_settore,
    get_settori
)
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

class Venditore(BaseModel):
    id: Optional[int] = None  # Aggiungi un campo ID opzionale se necessario
    nome_cognome: str
    email: EmailStr
    telefono: str
    citta: str
    esperienza_vendita: int
    anno_nascita: int
    settore_esperienza: str
    partita_iva: str
    agente_isenarco: str
    cv: Optional[str] = None  # Rende 'cv' opzionale
    note: Optional[str] = None  # Rende 'note' opzionale

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
    if authorization != f"Bearer {expected_token}":
        raise HTTPException(status_code=403, detail="Accesso negato.")
    
    # Connessione al database
    connection = create_connection()
    if not connection:
        raise HTTPException(status_code=500, detail="Impossibile connettersi al database.")
    
    # Inserisci o aggiorna il venditore nel database
    successo = add_venditore(connection, venditore)
    connection.close()
    
    if successo:
        return {"message": "Venditore inserito o aggiornato con successo."}
    else:
        raise HTTPException(status_code=500, detail="Errore nell'inserimento del venditore.")

@app.post("/aggiungi_settore")
def aggiungi_settore_endpoint(
    settore: Settore,
    authorization: str = Header(None)
):
    # Autenticazione
    expected_token = os.getenv('API_TOKEN')
    if authorization != f"Bearer {expected_token}":
        raise HTTPException(status_code=403, detail="Accesso negato.")
    
    # Connessione al database
    connection = create_connection()
    if not connection:
        raise HTTPException(status_code=500, detail="Impossibile connettersi al database.")
    
    # Aggiungi il settore nel database
    successo = add_settore(connection, settore.settore)
    connection.close()
    
    if successo:
        return {"message": f"Settore '{settore.settore}' aggiunto con successo."}
    else:
        raise HTTPException(status_code=500, detail="Errore nell'inserimento del settore.")
