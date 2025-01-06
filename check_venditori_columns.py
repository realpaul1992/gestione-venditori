# check_venditori_columns.py

import mysql.connector
from mysql.connector import Error
from db_connection import create_connection

def check_venditori_columns():
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("DESCRIBE venditori;")
            columns = cursor.fetchall()
            column_names = [column[0] for column in columns]
            print("Colonne nella tabella 'venditori':", column_names)
            if 'note' in column_names:
                print("La colonna 'note' esiste.")
            else:
                print("La colonna 'note' NON esiste. Aggiungila utilizzando la query ALTER TABLE.")
            cursor.close()
        except Error as e:
            print(f"Errore durante il controllo delle colonne: {e}")
        finally:
            connection.close()
    else:
        print("Connessione al database fallita.")

if __name__ == "__main__":
    check_venditori_columns()
