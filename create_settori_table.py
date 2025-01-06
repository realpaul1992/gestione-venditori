# create_settori_table.py

import mysql.connector
from mysql.connector import Error
from db_connection import create_connection, initialize_settori

def main():
    connection = create_connection()
    if connection:
        initialize_settori(connection)
        connection.close()
    else:
        print("Connessione al database fallita.")

if __name__ == "__main__":
    main()
