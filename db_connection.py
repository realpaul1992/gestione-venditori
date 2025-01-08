import mysql.connector
from mysql.connector import Error
import os
import pandas as pd
from io import StringIO, BytesIO
import zipfile

def create_connection():
    """
    Crea una connessione al database MySQL.
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
    Recupera tutti i settori dal database in forma di lista di stringhe.
    """
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT nome FROM settori ORDER BY nome ASC")
        records = cursor.fetchall()
        cursor.close()
        # Restituisce solo la lista di nomi settori
        return [r[0] for r in records]
    except Error as e:
        print(f"Errore nel recuperare i settori: {e}")
        return []

def get_available_cities(connection):
    """
    Recupera tutte le città uniche dal database in forma di lista di stringhe.
    """
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT DISTINCT citta FROM venditori ORDER BY citta ASC")
        records = cursor.fetchall()
        cursor.close()
        return [r[0] for r in records]
    except Error as e:
        print(f"Errore nel recuperare le città: {e}")
        return []

def search_venditori(connection, nome=None, citta=None, settore=None, partita_iva=None, agente_isenarco=None):
    """
    Cerca venditori nel database e restituisce una lista di DIZIONARI,
    così potrai fare record["nome_cognome"] in Streamlit.
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
        rows = cursor.fetchall()
        
        # Recupero i nomi delle colonne
        columns = [desc[0] for desc in cursor.description]
        
        # Converto ogni riga in dizionario
        records = []
        for row in rows:
            row_dict = {}
            for col_name, col_value in zip(columns, row):
                row_dict[col_name] = col_value
            records.append(row_dict)
        
        cursor.close()
        return records

    except Error as e:
        print(f"Errore nella ricerca dei venditori: {e}")
        return []

def delete_venditore(connection, venditore_id):
    """
    Elimina un venditore dal database basato sull'ID.
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
        return False, str(e)

def backup_database_python(connection):
    """
    Esegue il backup del database esportando ogni tabella in un file CSV e comprimendoli in uno ZIP.
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
                # Uso pandas.read_sql
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
    """
    try:
        backup_zip = BytesIO(backup_zip_bytes)
        with zipfile.ZipFile(backup_zip, 'r') as zipf:
            for file in zipf.namelist():
                if file.endswith('.csv'):
                    table = file[:-4]  # Rimuove '.csv'
                    df = pd.read_csv(zipf.open(file))
                    cursor = connection.cursor()
                    
                    # Svuota la tabella
                    cursor.execute(f"TRUNCATE TABLE {table}")
                    
                    # Prepara i dati
                    cols = "`,`".join(df.columns.tolist())
                    values = ", ".join(["%s"] * len(df.columns))
                    insert_stmt = f"INSERT INTO `{table}` (`{cols}`) VALUES ({values})"
                    
                    data = [tuple(row) for row in df.to_numpy()]
                    cursor.executemany(insert_stmt, data)
                    connection.commit()
                    cursor.close()
        return True, "Database ripristinato con successo."
    except Exception as e:
        return False, f"Errore durante il ripristino del database: {e}"
