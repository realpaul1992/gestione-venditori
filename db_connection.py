import mysql.connector
from mysql.connector import Error
import os
import pandas as pd
from io import StringIO, BytesIO
import zipfile

def create_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 3306)),
            database=os.getenv('DB_DATABASE', 'railway'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', 'password_di_prova')  # personalizza
        )
        if connection.is_connected():
            print("Connessione DB avvenuta con successo.")
            return connection
    except Error as e:
        print(f"Errore: {e}")
        return None

def initialize_settori(connection):
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
        print("Errore init settori:", e)

def search_venditori(connection, nome=None, citta=None, settore=None, partita_iva=None, agente_isenarco=None):
    """
    Restituisce una lista di dizionari: 
    [
      {
        "id": X,
        "nome_cognome": ...,
        ...
      },
      ...
    ]
    """
    try:
        cursor = connection.cursor(dictionary=True)  # <-- importante per restituire come dict
        query = """SELECT
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
        print("Errore search venditori:", e)
        return []

def get_settori(connection):
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT nome FROM settori ORDER BY nome ASC")
        rec = cursor.fetchall()
        cursor.close()
        return [r[0] for r in rec]
    except Error as e:
        print("Errore get_settori:", e)
        return []

def get_available_cities(connection):
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT DISTINCT citta FROM venditori ORDER BY citta ASC")
        rec = cursor.fetchall()
        cursor.close()
        return [r[0] for r in rec]
    except Error as e:
        print("Errore get_available_cities:", e)
        return []

def delete_venditore(connection, venditore_id):
    try:
        cursor = connection.cursor()
        query = "DELETE FROM venditori WHERE id = %s"
        cursor.execute(query, (venditore_id,))
        connection.commit()
        cursor.close()
        return True, "Venditore eliminato con successo."
    except Error as e:
        print("Errore delete_venditore:", e)
        return False, str(e)

def backup_database_python(connection):
    """
    Esegue un backup esportando i dati in CSV e poi comprimendo in uno ZIP.
    """
    try:
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        backup_zip = BytesIO()

        with zipfile.ZipFile(backup_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            for (table,) in tables:
                df = pd.read_sql(f"SELECT * FROM {table}", connection)
                csv_buffer = StringIO()
                df.to_csv(csv_buffer, index=False)
                zf.writestr(f"{table}.csv", csv_buffer.getvalue())

        backup_zip.seek(0)
        return True, backup_zip.getvalue()
    except Exception as e:
        return False, str(e)

def restore_database_python(connection, backup_zip_bytes):
    """
    Ripristina importando i CSV da uno ZIP.
    """
    try:
        zfile = BytesIO(backup_zip_bytes)
        with zipfile.ZipFile(zfile, 'r') as zf:
            for name in zf.namelist():
                if name.endswith('.csv'):
                    table_name = name[:-4]
                    df = pd.read_csv(zf.open(name))
                    cursor = connection.cursor()
                    # Svuota la tabella
                    cursor.execute(f"TRUNCATE TABLE {table_name}")
                    # Prepara insert
                    cols = df.columns.tolist()
                    col_list = "`,`".join(cols)
                    val_list = ",".join(["%s"]*len(cols))
                    insert_q = f"INSERT INTO `{table_name}` (`{col_list}`) VALUES ({val_list})"
                    data = [tuple(row) for _, row in df.iterrows()]
                    cursor.executemany(insert_q, data)
                    connection.commit()
                    cursor.close()
        return True, "Database ripristinato con successo."
    except Exception as e:
        return False, str(e)
