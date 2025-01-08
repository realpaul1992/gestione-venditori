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
    if authorization != f"Bearer {expected_token}":
        raise HTTPException(status_code=403, detail="Accesso negato.")
    
    # Connessione al database
    connection = create_connection()
    if not connection:
        raise HTTPException(status_code=500, detail="Impossibile connettersi al database.")
    
    # Mappatura settore_esperienza a settore_id
    try:
        cursor = connection.cursor()
        query_settore = "SELECT id FROM settori WHERE nome = %s"
        cursor.execute(query_settore, (venditore.settore_esperienza,))
        result = cursor.fetchone()
        if result:
            settore_id = result[0]
        else:
            raise HTTPException(status_code=400, detail=f"Settore '{venditore.settore_esperienza}' non trovato.")
        cursor.close()
    except Exception as e:
        connection.close()
        raise HTTPException(status_code=500, detail=f"Errore nella mappatura del settore: {e}")
    
    # Prepara i dati per l'inserimento
    venditore_data = {
        "nome_cognome": venditore.nome_cognome,
        "email": venditore.email,
        "telefono": venditore.telefono,
        "citta": venditore.citta,
        "esperienza_vendita": venditore.esperienza_vendita,
        "anno_nascita": venditore.anno_nascita,
        "settore_id": settore_id,
        "partita_iva": venditore.partita_iva,
        "agente_isenarco": venditore.agente_isenarco,
        "cv": venditore.cv if venditore.cv else "",
        "note": venditore.note if venditore.note else ""
    }
    
    # Inserisci o aggiorna il venditore nel database
    successo = add_venditore(connection, venditore_data)
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
        raise HTTPException(status_code=400, detail=f"Settore '{settore.settore}' già esistente o errore nell'inserimento.")
