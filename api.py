# backend/api.py

from fastapi import FastAPI, HTTPException, Header, UploadFile, File
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import os
from dotenv import load_dotenv
from db_connection import (
    create_connection,
    add_venditore,
    add_settore,
    get_settori,
    search_venditori,
    delete_venditore,
    update_venditore,
    verifica_note,
    backup_database_python,
    restore_database_python
)
import logging
from fastapi.responses import StreamingResponse
from io import BytesIO

# Configure logging
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
    nome: str

@app.get("/test")
def test_endpoint():
    return {"status": "API is working!"}

@app.post("/inserisci_venditore")
def inserisci_venditore(venditore: Venditore, authorization: str = Header(None)):
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
    
    # Aggiungi settore se non esiste
    settori = get_settori(connection)
    if venditore.settore_esperienza not in settori:
        success = add_settore(connection, venditore.settore_esperienza)
        if not success:
            logger.error(f"Errore nell'aggiungere il settore '{venditore.settore_esperienza}'.")
            connection.close()
            raise HTTPException(status_code=500, detail=f"Errore nell'aggiungere il settore '{venditore.settore_esperienza}'.")
    
    # Prepara i dati per l'inserimento
    venditore_data = (
        venditore.nome_cognome,
        venditore.email,
        venditore.telefono,
        venditore.citta,
        venditore.esperienza_vendita,
        venditore.anno_nascita,
        venditore.settore_esperienza,
        venditore.partita_iva,
        venditore.agente_isenarco,
        venditore.cv if venditore.cv else "",
        venditore.note.strip() if venditore.note else ""
    )
    
    # Inserisci venditore
    success = add_venditore(connection, venditore_data)
    connection.close()
    if success:
        logger.info(f"Venditore '{venditore.email}' inserito con successo.")
        return {"message": "Venditore inserito con successo."}
    else:
        logger.error(f"Errore nell'inserimento del venditore '{venditore.email}'.")
        raise HTTPException(status_code=500, detail="Errore nell'inserimento del venditore.")

@app.post("/aggiungi_settore")
def aggiungi_settore_endpoint(settore: Settore, authorization: str = Header(None)):
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
    
    # Aggiungi settore
    success = add_settore(connection, settore.nome.strip())
    connection.close()
    if success:
        logger.info(f"Settore '{settore.nome}' aggiunto con successo.")
        return {"message": f"Settore '{settore.nome}' aggiunto con successo."}
    else:
        logger.warning(f"Settore '{settore.nome}' già esistente.")
        raise HTTPException(status_code=400, detail=f"Settore '{settore.nome}' già esistente.")

@app.get("/settori", response_model=List[str])
def get_settori_endpoint(authorization: str = Header(None)):
    # Autenticazione
    expected_token = os.getenv('API_TOKEN')
    if not expected_token:
        logger.error("API_TOKEN non configurato.")
        raise HTTPException(status_code=500, detail="API_TOKEN non configurato.")
    
    if not authorization or authorization != f"Bearer {expected_token}":
        logger.warning(f"Tentativo di accesso non autorizzato con token: {authorization}")
        raise HTTPException(status_code=403, detail="Accesso negato.")
    
    connection = create_connection()
    if not connection:
        logger.error("Impossibile connettersi al database.")
        raise HTTPException(status_code=500, detail="Impossibile connettersi al database.")
    
    settori = get_settori(connection)
    connection.close()
    return settori

@app.get("/venditori", response_model=List[Venditore])
def get_venditori_endpoint(nome: Optional[str] = None, citta: Optional[str] = None, settore: Optional[str] = None, partita_iva: Optional[str] = None, agente_isenarco: Optional[str] = None, authorization: str = Header(None)):
    # Autenticazione
    expected_token = os.getenv('API_TOKEN')
    if not expected_token:
        logger.error("API_TOKEN non configurato.")
        raise HTTPException(status_code=500, detail="API_TOKEN non configurato.")
    
    if not authorization or authorization != f"Bearer {expected_token}":
        logger.warning(f"Tentativo di accesso non autorizzato con token: {authorization}")
        raise HTTPException(status_code=403, detail="Accesso negato.")
    
    connection = create_connection()
    if not connection:
        logger.error("Impossibile connettersi al database.")
        raise HTTPException(status_code=500, detail="Impossibile connettersi al database.")
    
    records = search_venditori(connection, nome, citta, settore, partita_iva, agente_isenarco)
    connection.close()
    venditori = []
    for record in records:
        venditori.append(Venditore(
            nome_cognome=record[1],
            email=record[2],
            telefono=record[3],
            citta=record[4],
            esperienza_vendita=record[5],
            anno_nascita=record[6],
            settore_esperienza=record[7],
            partita_iva=record[8],
            agente_isenarco=record[9],
            cv=record[10],
            note=record[11]
        ))
    return venditori

@app.delete("/venditori/{venditore_id}")
def delete_venditore_endpoint(venditore_id: int, authorization: str = Header(None)):
    # Autenticazione
    expected_token = os.getenv('API_TOKEN')
    if not expected_token:
        logger.error("API_TOKEN non configurato.")
        raise HTTPException(status_code=500, detail="API_TOKEN non configurato.")
    
    if not authorization or authorization != f"Bearer {expected_token}":
        logger.warning(f"Tentativo di accesso non autorizzato con token: {authorization}")
        raise HTTPException(status_code=403, detail="Accesso negato.")
    
    connection = create_connection()
    if not connection:
        logger.error("Impossibile connettersi al database.")
        raise HTTPException(status_code=500, detail="Impossibile connettersi al database.")
    
    success, message = delete_venditore(connection, venditore_id)
    connection.close()
    if success:
        logger.info(f"Venditore ID {venditore_id} eliminato con successo.")
        return {"message": message}
    else:
        logger.error(f"Errore nell'eliminare il venditore ID {venditore_id}: {message}")
        raise HTTPException(status_code=500, detail=message)

@app.put("/venditori/{venditore_id}")
def update_venditore_endpoint(venditore_id: int, venditore: Venditore, authorization: str = Header(None)):
    # Autenticazione
    expected_token = os.getenv('API_TOKEN')
    if not expected_token:
        logger.error("API_TOKEN non configurato.")
        raise HTTPException(status_code=500, detail="API_TOKEN non configurato.")
    
    if not authorization or authorization != f"Bearer {expected_token}":
        logger.warning(f"Tentativo di accesso non autorizzato con token: {authorization}")
        raise HTTPException(status_code=403, detail="Accesso negato.")
    
    connection = create_connection()
    if not connection:
        logger.error("Impossibile connettersi al database.")
        raise HTTPException(status_code=500, detail="Impossibile connettersi al database.")
    
    # Aggiungi settore se non esiste
    settori = get_settori(connection)
    if venditore.settore_esperienza not in settori:
        success = add_settore(connection, venditore.settore_esperienza)
        if not success:
            logger.error(f"Errore nell'aggiungere il settore '{venditore.settore_esperienza}'.")
            connection.close()
            raise HTTPException(status_code=500, detail=f"Errore nell'aggiungere il settore '{venditore.settore_esperienza}'.")
    
    # Aggiorna venditore
    success, message = update_venditore(
        connection,
        venditore_id,
        venditore.nome_cognome,
        venditore.email,
        venditore.telefono,
        venditore.citta,
        venditore.esperienza_vendita,
        venditore.anno_nascita,
        venditore.settore_esperienza,
        venditore.partita_iva,
        venditore.agente_isenarco,
        venditore.cv if venditore.cv else "",
        venditore.note.strip() if venditore.note else ""
    )
    connection.close()
    if success:
        logger.info(f"Venditore ID {venditore_id} aggiornato con successo.")
        return {"message": message}
    else:
        logger.error(f"Errore nell'aggiornare il venditore ID {venditore_id}: {message}")
        raise HTTPException(status_code=500, detail=message)

@app.post("/backup")
def backup_database_endpoint(authorization: str = Header(None)):
    # Autenticazione
    expected_token = os.getenv('API_TOKEN')
    if not expected_token:
        logger.error("API_TOKEN non configurato.")
        raise HTTPException(status_code=500, detail="API_TOKEN non configurato.")
    
    if not authorization or authorization != f"Bearer {expected_token}":
        logger.warning(f"Tentativo di accesso non autorizzato con token: {authorization}")
        raise HTTPException(status_code=403, detail="Accesso negato.")
    
    connection = create_connection()
    if not connection:
        logger.error("Impossibile connettersi al database.")
        raise HTTPException(status_code=500, detail="Impossibile connettersi al database.")
    
    success, backup_data = backup_database_python(connection)
    connection.close()
    if success:
        backup_io = BytesIO(backup_data)
        backup_io.seek(0)
        filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        return StreamingResponse(backup_io, media_type="application/zip", headers={"Content-Disposition": f"attachment; filename={filename}"})
    else:
        logger.error(f"Errore durante il backup: {backup_data}")
        raise HTTPException(status_code=500, detail=f"Errore durante il backup: {backup_data}")

@app.post("/restore")
def restore_database_endpoint(file: UploadFile = File(...), authorization: str = Header(None)):
    # Autenticazione
    expected_token = os.getenv('API_TOKEN')
    if not expected_token:
        logger.error("API_TOKEN non configurato.")
        raise HTTPException(status_code=500, detail="API_TOKEN non configurato.")
    
    if not authorization or authorization != f"Bearer {expected_token}":
        logger.warning(f"Tentativo di accesso non autorizzato con token: {authorization}")
        raise HTTPException(status_code=403, detail="Accesso negato.")
    
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Il file caricato deve essere un ZIP.")
    
    connection = create_connection()
    if not connection:
        logger.error("Impossibile connettersi al database.")
        raise HTTPException(status_code=500, detail="Impossibile connettersi al database.")
    
    try:
        contents = file.file.read()
        success, message = restore_database_python(connection, contents)
        connection.close()
        if success:
            return {"message": "Database ripristinato con successo."}
        else:
            raise HTTPException(status_code=500, detail=message)
    except Exception as e:
        logger.error(f"Errore durante il ripristino: {e}")
        connection.close()
        raise HTTPException(status_code=500, detail=f"Errore durante il ripristino: {e}")
