# test_db_connection.py

from db_connection import create_connection

def test_connection():
    connection = create_connection()
    if connection and connection.is_connected():
        print("Test di connessione riuscito.")
        connection.close()
    else:
        print("Test di connessione fallito.")

if __name__ == "__main__":
    test_connection()
