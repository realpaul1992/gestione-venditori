# add_cv_note_columns.py

import mysql.connector
from mysql.connector import Error

def add_columns_venditori():
    try:
        # Connessione al database
        connection = mysql.connector.connect(
            host='localhost',
            database='venditori_db',
            user='app_user',
            password='Informatic1992.-'
        )
        if connection.is_connected():
            cursor = connection.cursor()
            # Comandi SQL per aggiungere le colonne
            alter_table_queries = [
                "ALTER TABLE venditori ADD COLUMN cv VARCHAR(255);",
                "ALTER TABLE venditori ADD COLUMN note TEXT;"
            ]
            for query in alter_table_queries:
                try:
                    cursor.execute(query)
                    connection.commit()
                    print(f"Eseguito: {query}")
                except mysql.connector.Error as err:
                    if err.errno == 1060:
                        print(f"Colonna già esistente: {query}")
                    else:
                        print(f"Errore: {err}")
            cursor.close()
    except Error as e:
        print(f"Errore durante l'aggiunta delle colonne: {e}")
    finally:
        if connection.is_connected():
            connection.close()
            print("Connessione al database chiusa.")

if __name__ == "__main__":
    add_columns_venditori()
