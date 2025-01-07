# db_connection.py

import mysql.connector
from mysql.connector import Error
import os
import pandas as pd
from io import StringIO, BytesIO
import zipfile

def create_connection():
    """
    Crea una connessione al database MySQL utilizzando le variabili d'ambiente.
    """
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 3306)),
            database=os.getenv('DB_DATABASE', 'railway'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', 'mdopkNSoSVTDnnuWFRnEWqMeqAOewWpt')
        )
        if connection.is_connected():
            print("Connessione al database avvenuta con successo.")
            return connection
    except Error as e:
        print(f"Errore di connessione al database: {e}")
        return None

def initialize_settori(connection):
    """
    Inizializza la tabella dei settori se non esiste.
    """
    try:
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settori (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nome VARCHAR(255) UNIQUE NOT NULL
            )
        """)
        connection.commit()
        cursor.close()
    except Error as e:
        print(f"Errore nell'inizializzare la tabella settori: {e}")

def add_settore(connection, nome_settore):
    """
    Aggiunge un nuovo settore al database.
    :param connection: Connessione al database.
    :param nome_settore: Nome del settore da aggiungere.
    :return: Bool. True se aggiunto con successo, False se già esiste.
    """
    try:
        cursor = connection.cursor()
        query = "INSERT INTO settori (nome) VALUES (%s)"
        cursor.execute(query, (nome_settore,))
        connection.commit()
        cursor.close()
        return True
    except mysql.connector.IntegrityError:
        # Settore già esistente
        return False
    except Error as e:
        print(f"Errore nell'aggiungere il settore: {e}")
        return False

def get_settori(connection):
    """
    Recupera tutti i settori dal database.
    :param connection: Connessione al database.
    :return: Lista di settori.
    """
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT nome FROM settori ORDER BY nome ASC")
        records = cursor.fetchall()
        cursor.close()
        return [record[0] for record in records]
    except Error as e:
        print(f"Errore nel recuperare i settori: {e}")
        return []

def get_available_cities(connection):
    """
    Recupera tutte le città presenti nel database.
    :param connection: Connessione al database.
    :return: Lista di città.
    """
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT DISTINCT citta FROM venditori ORDER BY citta ASC")
        records = cursor.fetchall()
        cursor.close()
        return [record[0] for record in records]
    except Error as e:
        print(f"Errore nel recuperare le città: {e}")
        return []

def add_venditore(connection, venditore):
    """
    Aggiunge un nuovo venditore al database.
    :param connection: Connessione al database.
    :param venditore: Tuple contenente i dati del venditore.
    :return: Bool. True se aggiunto con successo, False altrimenti.
    """
    try:
        cursor = connection.cursor()
        query = """
            INSERT INTO venditori 
            (nome_cognome, email, telefono, citta, esperienza_vendita, 
             anno_nascita, settore_esperienza, partita_iva, agente_isenarco, cv, note, data_creazione)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """
        cursor.execute(query, venditore)
        connection.commit()
        cursor.close()
        return True
    except mysql.connector.IntegrityError as e:
        # Email duplicata o altri vincoli violati
        print(f"Errore nell'aggiungere il venditore: {e}")
        return False
    except Error as e:
        print(f"Errore nell'aggiungere il venditore: {e}")
        return False

def search_venditori(connection, nome=None, citta=None, settore=None, partita_iva=None, agente_isenarco=None):
    """
    Cerca venditori nel database basati sui parametri forniti.
    :param connection: Connessione al database.
    :param nome: Nome o parte del nome del venditore.
    :param citta: Città del venditore.
    :param settore: Settore di esperienza.
    :param partita_iva: "Sì", "No" o None.
    :param agente_isenarco: "Sì", "No" o None.
    :return: Lista di venditori.
    """
    try:
        cursor = connection.cursor()
        query = """
            SELECT 
                id, 
                nome_cognome, 
                email, 
                telefono, 
                citta, 
                esperienza_vendita, 
                anno_nascita, 
                settore_esperienza, 
                partita_iva, 
                agente_isenarco, 
                cv, 
                note, 
                data_creazione
            FROM venditori
            WHERE 1=1
        """
        params = []
        
        if nome:
            query += " AND nome_cognome LIKE %s"
            params.append(f"%{nome}%")
        if citta:
            query += " AND citta = %s"
            params.append(citta)
        if settore:
            query += " AND settore_esperienza = %s"
            params.append(settore)
        if partita_iva:
            query += " AND partita_iva = %s"
            params.append(partita_iva)
        if agente_isenarco:
            query += " AND agente_isenarco = %s"
            params.append(agente_isenarco)
        
        cursor.execute(query, tuple(params))
        records = cursor.fetchall()
        cursor.close()
        return records
    except Error as e:
        print(f"Errore nella ricerca dei venditori: {e}")
        return []

def delete_venditore(connection, venditore_id):
    """
    Elimina un venditore dal database basato sull'ID.
    :param connection: Connessione al database.
    :param venditore_id: ID del venditore da eliminare.
    :return: Tuple (successo: bool, messaggio: str)
    """
    try:
        cursor = connection.cursor()
        query = "DELETE FROM venditori WHERE id = %s"
        cursor.execute(query, (venditore_id,))
        connection.commit()
        cursor.close()
        return True, "Venditore eliminato con successo."
    except Error as e:
        print(f"Errore nell'eliminare il venditore: {e}")
        return False, f"Errore nell'eliminare il venditore: {e}"

def update_venditore(connection, venditore_id, nome_cognome, email, telefono, citta, esperienza_vendita, anno_nascita, settore_esperienza, partita_iva, agente_isenarco, cv_path, note):
    """
    Aggiorna i dati di un venditore esistente.
    :param connection: Connessione al database.
    :param venditore_id: ID del venditore da aggiornare.
    :param nome_cognome: Nome e cognome aggiornati.
    :param email: Email aggiornata.
    :param telefono: Telefono aggiornato.
    :param citta: Città aggiornata.
    :param esperienza_vendita: Esperienza nella vendita aggiornata.
    :param anno_nascita: Anno di nascita aggiornato.
    :param settore_esperienza: Settore di esperienza aggiornato.
    :param partita_iva: Partita IVA aggiornata.
    :param agente_isenarco: Stato di iscrizione Enasarco aggiornato.
    :param cv_path: Percorso del CV aggiornato.
    :param note: Note aggiornate.
    :return: Tuple (successo: bool, messaggio: str)
    """
    try:
        cursor = connection.cursor()
        query = """
            UPDATE venditori 
            SET 
                nome_cognome = %s,
                email = %s,
                telefono = %s,
                citta = %s,
                esperienza_vendita = %s,
                anno_nascita = %s,
                settore_esperienza = %s,
                partita_iva = %s,
                agente_isenarco = %s,
                cv = %s,
                note = %s
            WHERE id = %s
        """
        cursor.execute(query, (
            nome_cognome, email, telefono, citta, esperienza_vendita,
            anno_nascita, settore_esperienza, partita_iva, agente_isenarco,
            cv_path, note, venditore_id
        ))
        connection.commit()
        cursor.close()
        return True, "Venditore aggiornato con successo."
    except mysql.connector.IntegrityError as e:
        # Gestisce errori di duplicazione email
        print(f"Errore nell'aggiornare il venditore: {e}")
        return False, f"Errore nell'aggiornare il venditore: {e}"
    except Error as e:
        print(f"Errore nell'aggiornare il venditore: {e}")
        return False, f"Errore nell'aggiornare il venditore: {e}"

def verifica_note(connection, venditore_id):
    """
    Verifica e restituisce le note aggiornate di un venditore.
    :param connection: Connessione al database.
    :param venditore_id: ID del venditore.
    :return: Stringa delle note aggiornate.
    """
    try:
        cursor = connection.cursor()
        query = "SELECT note FROM venditori WHERE id = %s"
        cursor.execute(query, (venditore_id,))
        record = cursor.fetchone()
        cursor.close()
        return record[0] if record else ""
    except Error as e:
        print(f"Errore nella verifica delle note: {e}")
        return ""

def backup_database_python(connection):
    """
    Esegue un backup del database esportando ogni tabella in un file CSV e comprimendoli in un ZIP.
    :param connection: Connessione al database.
    :return: Tuple (successo: bool, risultato: bytes o messaggio di errore)
    """
    try:
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        cursor.close()

        backup_zip = BytesIO()
        with zipfile.ZipFile(backup_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for table_tuple in tables:
                table = table_tuple[0]
                df = pd.read_sql(f"SELECT * FROM {table}", connection)
                csv_buffer = StringIO()
                df.to_csv(csv_buffer, index=False)
                zipf.writestr(f"{table}.csv", csv_buffer.getvalue())
        
        backup_zip.seek(0)
        return True, backup_zip.getvalue()
    except Exception as e:
        return False, str(e)

def restore_database_python(connection, backup_zip_bytes):
    """
    Ripristina il database importando i dati da un file ZIP contenente CSV delle tabelle.
    :param connection: Connessione al database.
    :param backup_zip_bytes: Contenuto del file ZIP in bytes.
    :return: Tuple (successo: bool, messaggio: str)
    """
    try:
        backup_zip = BytesIO(backup_zip_bytes)
        with zipfile.ZipFile(backup_zip, 'r') as zipf:
            for file in zipf.namelist():
                if file.endswith('.csv'):
                    table = file[:-4]  # Rimuove '.csv'
                    df = pd.read_csv(zipf.open(file))
                    cursor = connection.cursor()
                    
                    # Pulizia della tabella prima dell'inserimento
                    cursor.execute(f"TRUNCATE TABLE {table}")
                    
                    # Preparazione dei dati per l'inserimento
                    cols = "`,`".join([str(i) for i in df.columns.tolist()])
                    values = ", ".join(["%s"] * len(df.columns))
                    insert_stmt = f"INSERT INTO `{table}` (`{cols}`) VALUES ({values})"
                    
                    # Inserimento dei dati in batch
                    data = [tuple(row) for row in df.to_numpy()]
                    cursor.executemany(insert_stmt, data)
                    connection.commit()
                    cursor.close()
        return True, "Database ripristinato con successo."
    except Exception as e:
        return False, f"Errore durante il ripristino del database: {e}"

def add_venditori_bulk(connection, venditori, overwrite=False):
    """
    Aggiunge più venditori al database in una sola operazione.
    :param connection: Connessione al database.
    :param venditori: Lista di tuple contenenti i dati dei venditori.
    :param overwrite: Bool. Se True, aggiorna i record esistenti. Se False, ignora i duplicati.
    :return: Tuple (successo: bool, messaggio: str)
    """
    try:
        cursor = connection.cursor()
        if overwrite:
            # Aggiorna i record esistenti basati sull'email
            query_update = """
                UPDATE venditori 
                SET 
                    nome_cognome = %s,
                    telefono = %s,
                    citta = %s,
                    esperienza_vendita = %s,
                    anno_nascita = %s,
                    settore_esperienza = %s,
                    partita_iva = %s,
                    agente_isenarco = %s,
                    cv = %s,
                    note = %s
                WHERE email = %s
            """
            # Preparare i dati per l'aggiornamento
            venditori_update = [
                (
                    venditore[0],  # nome_cognome
                    venditore[2],  # telefono
                    venditore[3],  # citta
                    venditore[4],  # esperienza_vendita
                    venditore[5],  # anno_nascita
                    venditore[6],  # settore_esperienza
                    venditore[7],  # partita_iva
                    venditore[8],  # agente_isenarco
                    venditore[9],  # cv
                    venditore[10], # note
                    venditore[1]   # email
                )
                for venditore in venditori
            ]
            cursor.executemany(query_update, venditori_update)
            connection.commit()
            aggiornati = cursor.rowcount
            cursor.close()
            print(f"{aggiornati} venditori aggiornati con successo.")
            return True, f"{aggiornati} venditori aggiornati con successo."
        else:
            # Inserisce solo i venditori non esistenti
            query_insert = """
                INSERT INTO venditori 
                (nome_cognome, email, telefono, citta, esperienza_vendita, 
                 anno_nascita, settore_esperienza, partita_iva, agente_isenarco, cv, note, data_creazione)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            cursor.executemany(query_insert, venditori)
            connection.commit()
            inseriti = cursor.rowcount
            cursor.close()
            print(f"{inseriti} venditori aggiunti con successo.")
            return True, f"{inseriti} venditori aggiunti con successo."
    except Error as e:
        print(f"Errore nell'aggiungere/aggiornare i venditori: {e}")
        return False, f"Errore nell'aggiungere/aggiornare i venditori: {e}"

def get_existing_emails(connection, emails):
    """
    Recupera le email che già esistono nel database.
    :param connection: Connessione al database.
    :param emails: Lista di email da verificare.
    :return: Set di email esistenti.
    """
    try:
        cursor = connection.cursor()
        if not emails:
            return set()
        format_strings = ','.join(['%s'] * len(emails))
        query = f"SELECT email FROM venditori WHERE email IN ({format_strings})"
        cursor.execute(query, tuple(emails))
        records = cursor.fetchall()
        cursor.close()
        existing_emails = set(record[0] for record in records)
        return existing_emails
    except Error as e:
        print(f"Errore nel recuperare le email esistenti: {e}")
        return set()
