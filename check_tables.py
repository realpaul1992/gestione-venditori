# check_tables.py

import mysql.connector
from mysql.connector import Error

def check_tables():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='venditori_db',
            user='app_user',
            password='Informatic1992.-'
        )
        if connection.is_connected():
            cursor = connection.cursor()
            # Verifica la tabella settori
            cursor.execute("DESCRIBE settori;")
            settori = cursor.fetchall()
            print("Struttura della tabella 'settori':")
            for col in settori:
                print(col)
            
            # Verifica la tabella venditori
            cursor.execute("DESCRIBE venditori;")
            venditori = cursor.fetchall()
            print("\nStruttura della tabella 'venditori':")
            for col in venditori:
                print(col)
            
            cursor.close()
    except Error as e:
        print(f"Errore: {e}")
    finally:
        if connection.is_connected():
            connection.close()

if __name__ == "__main__":
    check_tables()
