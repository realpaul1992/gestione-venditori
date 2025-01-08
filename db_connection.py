import mysql.connector
from mysql.connector import Error
import os
import pandas as pd
from io import StringIO, BytesIO
import zipfile

def create_connection():
    """
    Crea una connessione al database MySQL utilizzando le variabili d'ambiente
    (o valori di default se non sono definiti).
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
    Inizializza la tabella 'settori' se non esiste.
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
    Ritorna True se l’inserimento ha successo o il settore già esiste,
    False se si verifica un errore.
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
    Ritorna una lista di stringhe (nomi dei settori).
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
    Recupera tutte le città presenti nella tabella 'venditori' e le restituisce in ordine alfabetico.
    """
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT DISTINCT citta FROM venditori WHERE citta IS NOT NULL ORDER BY citta ASC")
        records = cursor.fetchall()
        cursor.close()
        # Filtra eventuali valori None e restituisce solo le stringhe
        return [row[0] for row in records if row[0]]
    except Error as e:
        print(f"Errore nel recuperare le città: {e}")
        return []

def add_venditore(connection, venditore):
    """
    Aggiunge un nuovo venditore al database.
    :param venditore: Tupla con:
      (nome_cognome, email, telefono, citta, esperienza_vendita,
       anno_nascita, settore_esperienza, partita_iva, agente_isenarco, cv, note)
    Ritorna True se aggiunto con successo, False altrimenti.
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
        # Email duplicata o altri vincoli
        print(f"Errore nell'aggiungere il venditore (IntegrityError): {e}")
        return False
    except Error as e:
        print(f"Errore nell'aggiungere il venditore: {e}")
        return False

def search_venditori(connection, nome=None, citta=None, settore=None, partita_iva=None, agente_isenarco=None):
    """
    Cerca venditori nel database basati sui parametri forniti.
    Ritorna una lista di record (ognuno è una tupla).
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
    Ritorna (True, "Messaggio") se l'eliminazione ha successo, altrimenti (False, "Errore").
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

def update_venditore(connection, venditore_id, nome_cognome, email, telefono, citta, 
                     esperienza_vendita, anno_nascita, settore_esperienza, 
                     partita_iva, agente_isenarco, cv_path, note):
    """
    Aggiorna i dati di un venditore esistente.
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
        print(f"Errore (IntegrityError) nell'aggiornare il venditore: {e}")
        return False, str(e)
    except Error as e:
        print(f"Errore nell'aggiornare il venditore: {e}")
        return False, str(e)

def verifica_note(connection, venditore_id):
    """
    Verifica e restituisce le note aggiornate di un venditore.
    """
    try:
        cursor = connection.cursor()
        query = "SELECT note FROM venditori WHERE id = %s"
        cursor.execute(query, (venditore_id,))
        record = cursor.fetchone()
        cursor.close()
        if record:
            return record[0] if record[0] else ""
        return ""
    except Error as e:
        print(f"Errore nella verifica delle note: {e}")
        return ""

def backup_database_python(connection):
    """
    Esegue un backup del database esportando ogni tabella in CSV e comprimendo i file in uno ZIP.
    Ritorna (True, backup_zip_bytes) se ha successo, (False, error_msg) se fallisce.
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
    Ritorna (True, "msg") o (False, "errore").
    """
    try:
        backup_zip = BytesIO(backup_zip_bytes)
        with zipfile.ZipFile(backup_zip, 'r') as zipf:
            for file in zipf.namelist():
                if file.endswith('.csv'):
                    table = file[:-4]  # nome tabella = nome del file senza ".csv"
                    df = pd.read_csv(zipf.open(file))
                    cursor = connection.cursor()
                    
                    # Pulizia della tabella prima dell'inserimento
                    cursor.execute(f"TRUNCATE TABLE `{table}`")
                    
                    # Preparazione dei dati per l'inserimento
                    cols = "`,`".join([str(i) for i in df.columns.tolist()])
                    values = ", ".join(["%s"] * len(df.columns))
                    insert_stmt = f"INSERT INTO `{table}` (`{cols}`) VALUES ({values})"
                    
                    # Inserimento dei dati
                    data = [tuple(row) for row in df.to_numpy()]
                    cursor.executemany(insert_stmt, data)
                    connection.commit()
                    cursor.close()
        return True, "Database ripristinato con successo."
    except Exception as e:
        return False, f"Errore durante il ripristino del database: {e}"
