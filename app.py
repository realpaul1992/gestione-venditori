# app.py

import streamlit as st
from db_connection import (
    create_connection, 
    add_venditore, 
    search_venditori, 
    add_settore, 
    get_settori, 
    get_available_cities,  
    update_venditore,
    delete_venditore,
    verifica_note,
    initialize_settori,
    backup_database_python,  # Import della nuova funzione di backup
    restore_database_python, # Import della nuova funzione di ripristino
    add_venditori_bulk,
    get_existing_emails
)
import pandas as pd
import os
from datetime import datetime, timedelta
import plotly.express as px  # Import di Plotly per grafici avanzati
import base64  # Importato per il download del CV
from io import BytesIO

# Funzione per creare e memorizzare la connessione nel cache
@st.cache_resource
def get_connection():
    connection = create_connection()
    if connection:
        initialize_settori(connection)
    return connection

# Funzione per caricare tutte le città dal CSV
@st.cache_data
def load_all_cities():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(current_dir, 'italian_cities.csv')
        
        if not os.path.exists(csv_path):
            st.warning("Il file 'italian_cities.csv' non è stato trovato nella directory corrente.")
            return []
        
        df = pd.read_csv(csv_path, delimiter=';', encoding='utf-8')
        df.columns = df.columns.str.strip()
        
        if 'denominazione_ita' not in df.columns:
            st.warning("La colonna 'denominazione_ita' non è presente nel CSV.")
            return []
        
        cities = df['denominazione_ita'].dropna().unique().tolist()
        return sorted(cities)
    except pd.errors.ParserError:
        st.error("Errore nella lettura del file CSV.")
        return []
    except Exception as e:
        st.error(f"Errore inaspettato: {e}")
        return []

def automatic_backup(connection):
    """
    Esegue un backup automatico se è passato più di 24 ore dall'ultimo backup.
    """
    last_backup_file = 'last_backup.txt'
    current_time = datetime.now()

    # Verifica se esiste un file che registra l'ultimo backup
    if os.path.exists(last_backup_file):
        try:
            with open(last_backup_file, 'r') as f:
                last_backup_time_str = f.read()
                last_backup_time = datetime.strptime(last_backup_time_str, "%Y-%m-%d %H:%M:%S")
        except Exception as e:
            st.sidebar.error(f"Errore nel leggere il file di ultimo backup: {e}")
            last_backup_time = current_time - timedelta(days=1)  # Forza il backup in caso di errore
    else:
        last_backup_time = current_time - timedelta(days=1)  # Forza il backup la prima volta

    # Se è passato più di 24 ore, esegui un backup
    if current_time - last_backup_time > timedelta(hours=24):
        st.sidebar.info("Eseguendo backup automatico...")
        successo, risultato = backup_database_python(connection)  # Utilizza la nuova funzione
        if successo:
            # Crea un nome file con data e ora
            timestamp = current_time.strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_auto_{timestamp}.zip"
            
            # Prepara il download del backup
            st.sidebar.success(f"Backup automatico creato alle {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            st.sidebar.download_button(
                label="📥 Scarica Backup Automatico",
                data=risultato,
                file_name=backup_filename,
                mime='application/zip'
            )
            
            # Aggiorna l'ultimo backup
            with open(last_backup_file, 'w') as f:
                f.write(current_time.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            st.sidebar.error(f"Backup automatico fallito: {risultato}")

def anno_nascita_index(anno):
    """
    Calcola l'indice dell'anno di nascita per il selectbox.
    """
    anni = list(range(1900, 2025))
    if anno in anni:
        return anni.index(anno)
    else:
        return 0  # Default a 1900 se l'anno non è trovato

def main():
    # Configura la pagina Streamlit con un tema chiaro
    st.set_page_config(page_title="Gestione Venditori", layout="wide", initial_sidebar_state="expanded", page_icon="📈")

    # Inserisci il logo aziendale all'inizio della pagina
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo.svg')  # Assicurati che il percorso sia corretto
    if os.path.exists(logo_path):
        st.image(logo_path, width=250)  # Ingrandisci il logo a 250 pixel
    else:
        st.warning("Logo aziendale non trovato. Assicurati che 'logo.svg' sia nella directory corrente.")

    # Inizializza tutte le variabili necessarie nella session_state
    if 'venditori_data' not in st.session_state:
        st.session_state.venditori_data = []
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = 'Inserisci Venditore'
    if 'delete_confirm_id' not in st.session_state:
        st.session_state.delete_confirm_id = None
    if 'display_count' not in st.session_state:
        st.session_state.display_count = 10  # Numero iniziale di venditori da mostrare

    # Rimuovi il titolo principale
    # st.title("📈 Gestione dei Venditori")  # Rimosso come richiesto

    # Ottieni la connessione al database
    connection = get_connection()

    if not connection:
        st.error("Impossibile connettersi al database.")
        st.stop()

    # Caricamento automatizzato del file CSV delle città italiane
    all_cities = load_all_cities()
    if not all_cities:
        st.warning("Verifica che il file 'italian_cities.csv' sia presente nella stessa directory di app.py.")

    # Definisci le opzioni delle schede
    schede = [
        "Inserisci Venditore",
        "Cerca Venditori",
        "Dashboard",
        "Gestisci Settori e Profili Venditori",
        "Backup e Ripristino",
        "Esporta/Importa Venditori"  # Nuova Scheda
    ]

    # Barra laterale per la navigazione
    st.sidebar.title("📋 Navigazione")
    st.session_state.active_tab = st.sidebar.radio(
        "Seleziona la sezione:",
        schede,
        index=schede.index(st.session_state.active_tab),
        key="schede_radio"
    )

    # Esegui il backup automatico all'avvio
    automatic_backup(connection)

    # Funzione per gestire l'eliminazione
    def handle_delete(venditore_id):
        st.session_state.delete_confirm_id = venditore_id

    # Funzione per confermare l'eliminazione
    def confirm_delete(venditore_id):
        successo, messaggio = delete_venditore(connection, venditore_id)
        if successo:
            st.success(messaggio)
            # Rimuovi il venditore dai dati visualizzati
            st.session_state.venditori_data = [v for v in st.session_state.venditori_data if v[0] != venditore_id]
        else:
            st.error(messaggio)
        st.session_state.delete_confirm_id = None

    # Scheda 1: Inserisci Venditore
    if st.session_state.active_tab == "Inserisci Venditore":
        st.header("📥 Inserisci Nuovo Venditore")
        with st.form("form_inserisci_venditore"):
            # Miglioramento del layout del form usando colonne
            col1, col2, col3 = st.columns(3)
            
            with col1:
                nome_cognome = st.text_input("Nome e Cognome", placeholder="Inserisci il nome completo")
                email = st.text_input("Email", placeholder="Inserisci l'email")
                telefono = st.text_input("Telefono", placeholder="Inserisci il numero di telefono")
            
            with col2:
                if all_cities:
                    citta = st.selectbox("Città", all_cities)
                else:
                    citta = st.selectbox("Città", ["Carica prima il CSV"])
                esperienza_vendita = st.select_slider(
                    "Esperienza nella vendita (anni)", 
                    options=list(range(0, 101)), 
                    value=0
                )
                anno_nascita = st.selectbox(
                    "Anno di Nascita", 
                    options=list(range(1900, 2025))
                )
            
            with col3:
                settori = get_settori(connection)
                if settori:
                    settore_esperienza = st.selectbox(
                        "Settore di Esperienza", 
                        settori
                    )
                else:
                    settore_esperienza = st.selectbox(
                        "Settore di Esperienza", 
                        ["Carica prima i settori"]
                    )
                partita_iva = st.selectbox(
                    "Partita IVA", 
                    options=["Sì", "No"]
                )
                agente_isenarco = st.selectbox(
                    "Agente Iscritto Enasarco", 
                    options=["Sì", "No"]
                )
            
            # Sezione per CV e Note senza il titolo
            col4, col5 = st.columns([2, 3])
            with col4:
                cv_file = st.file_uploader("Carica il CV (PDF)", type=["pdf"])
            with col5:
                note = st.text_area("Note", placeholder="Inserisci eventuali note")
            
            submit_button = st.form_submit_button("Aggiungi Venditore")
            if submit_button:
                if (nome_cognome and email and citta and 
                    citta != "Carica prima il CSV" and 
                    settore_esperienza != "Carica prima i settori"):
                    # Gestisci il caricamento del CV
                    cv_path = None
                    if cv_file is not None:
                        cv_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cv_files')
                        os.makedirs(cv_dir, exist_ok=True)
                        cv_path = os.path.join(cv_dir, cv_file.name)
                        try:
                            with open(cv_path, "wb") as f:
                                f.write(cv_file.getbuffer())
                            st.success(f"CV salvato in: `{cv_path}`")
                        except Exception as e:
                            st.error(f"Errore nel salvataggio del CV: {e}")
                            cv_path = None
                    
                    venditore = (
                        nome_cognome, 
                        email, 
                        telefono, 
                        citta, 
                        esperienza_vendita,
                        anno_nascita, 
                        settore_esperienza, 
                        partita_iva, 
                        agente_isenarco,
                        cv_path,  # Campo 'cv'
                        note.strip()  # Campo 'note'
                    )
                    successo = add_venditore(connection, venditore)
                    if successo:
                        st.success("Venditore aggiunto con successo!")
                        # Aggiorna lo stato dei venditori
                        st.session_state.venditori_data = search_venditori(connection)
                    else:
                        st.error("Si è verificato un errore durante l'inserimento del venditore.")
                else:
                    st.error("🔴 Nome, Email, Città e Settore sono obbligatori.")

    # Scheda 2: Cerca Venditori
    elif st.session_state.active_tab == "Cerca Venditori":
        st.header("🔍 Cerca Venditori")
        with st.form("form_cerca_venditori"):
            # Miglioramento del layout del form usando colonne
            col1, col2, col3 = st.columns(3)
            
            with col1:
                nome_cerca = st.text_input("Nome e Cognome", placeholder="Inserisci il nome da cercare")
                partita_iva_cerca = st.selectbox("Partita IVA", ["Tutti", "Sì", "No"])
            
            with col2:
                available_cities = get_available_cities(connection)
                citta_cerca = st.selectbox("Città", ["Tutte"] + available_cities)
                agente_isenarco_cerca = st.selectbox(
                    "Agente Iscritto Enasarco", 
                    options=["Tutti", "Sì", "No"]
                )
            
            with col3:
                settori = get_settori(connection)
                if settori:
                    settore_cerca = st.selectbox("Settore di Esperienza", ["Tutti"] + settori)
                else:
                    settore_cerca = st.selectbox("Settore di Esperienza", ["Carica prima i settori"])
            
            cerca_button = st.form_submit_button("Cerca")
        
        if cerca_button:
            # Mappatura dei valori "Tutti" a None
            nome_param = nome_cerca if nome_cerca else None
            citta_param = citta_cerca if citta_cerca != "Tutte" else None
            settore_param = settore_cerca if settore_cerca != "Tutti" else None
            partita_iva_param = partita_iva_cerca if partita_iva_cerca != "Tutti" else None
            agente_isenarco_param = agente_isenarco_cerca if agente_isenarco_cerca != "Tutti" else None

            records = search_venditori(
                connection, 
                nome=nome_param, 
                citta=citta_param, 
                settore=settore_param, 
                partita_iva=partita_iva_param,
                agente_isenarco=agente_isenarco_param
            )
            st.session_state.venditori_data = records  # Aggiorna lo stato con i risultati della ricerca
            st.session_state.display_count = 10  # Reset della visualizzazione

        else:
            if 'venditori_data' not in st.session_state:
                st.session_state.venditori_data = []  # Reset dei dati se non si è cliccato "Cerca"

        st.markdown("---")

        # Visualizza i venditori solo se ci sono risultati
        if st.session_state.venditori_data:
            st.subheader(f"Risultati della Ricerca: {len(st.session_state.venditori_data)} Venditori Trovati")
            
            # Mostra solo i primi 'display_count' venditori
            venditori_display = st.session_state.venditori_data[:st.session_state.display_count]

            for record in venditori_display:
                with st.expander(f"📌 {record[1]}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**Email:** {record[2]}")
                        st.markdown(f"**Telefono:** {record[3]}")
                        st.markdown(f"**Città:** {record[4]}")
                        st.markdown(f"**Esperienza Vendita:** {record[5]} anni")
                    
                    with col2:
                        st.markdown(f"**Settore:** {record[7]}")
                        st.markdown(f"**Partita IVA:** {record[8]}")
                        st.markdown(f"**Agente Iscritto Enasarco:** {record[9]}")
                        st.markdown(f"**Note:** {record[11]}")
                    
                    st.markdown(f"**Data Creazione:** {record[12].strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # Pulsanti di azione organizzati in due colonne
                    action_col1, action_col2 = st.columns([1, 1])
                    
                    with action_col1:
                        # Pulsante di download CV
                        if record[10]:  # 'cv' è il campo all'indice 10
                            if os.path.exists(record[10]):
                                try:
                                    with open(record[10], "rb") as f:
                                        cv_bytes = f.read()
                                    st.download_button(
                                        label="📄 Scarica CV",
                                        data=cv_bytes,
                                        file_name=os.path.basename(record[10]),
                                        mime="application/pdf",
                                        key=f"download_{record[0]}"
                                    )
                                except Exception as e:
                                    st.error(f"Errore nel leggere il CV: {e}")
                            else:
                                st.warning("**CV:** File non trovato.")
                        else:
                            st.info("**CV:** N/A")
                    
                    with action_col2:
                        # Pulsante di eliminazione posizionato a destra
                        delete_button = st.button("🗑️ Elimina", key=f"delete_{record[0]}")
                        if delete_button:
                            handle_delete(record[0])

            # Pulsante "Carica Altro" per lo scroll infinito
            if st.session_state.display_count < len(st.session_state.venditori_data):
                if st.button("Carica Altro", key="load_more"):
                    st.session_state.display_count += 10  # Incrementa di 10 venditori
            else:
                st.info("Hai visualizzato tutti i venditori.")

        else:
            st.info("Nessun venditore trovato.")

        # Conferma per l'eliminazione
        if st.session_state.delete_confirm_id is not None:
            venditore_id = st.session_state.delete_confirm_id
            st.warning("Sei sicuro di voler eliminare questo venditore?", icon="⚠️")
            confirm, cancel = st.columns([1, 1])
            with confirm:
                if st.button("Conferma Eliminazione", key="confirm_delete"):
                    confirm_delete(venditore_id)
            with cancel:
                if st.button("Annulla Eliminazione", key="cancel_delete"):
                    st.session_state.delete_confirm_id = None

    # Scheda 3: Dashboard
    elif st.session_state.active_tab == "Dashboard":
        st.header("📊 Dashboard")
        st.markdown("---")

        # Organizza i grafici in colonne per una migliore disposizione
        col1, col2 = st.columns(2)

        with col1:
            # 1. Numero Totale di Venditori
            try:
                cursor = connection.cursor()
                query_totale = "SELECT COUNT(*) as totale FROM venditori"
                cursor.execute(query_totale)
                df_totale = cursor.fetchone()
                totale_venditori = df_totale[0] if df_totale else 0
                st.subheader(f"Numero Totale di Venditori: **{totale_venditori}**")
                cursor.close()
            except Exception as e:
                st.error(f"Errore nel calcolare il numero totale di venditori. Dettaglio: {e}")

        with col2:
            # 2. Numero di Venditori per Settore
            try:
                cursor = connection.cursor()
                query_settori = "SELECT settore_esperienza, COUNT(*) as totale FROM venditori GROUP BY settore_esperienza"
                cursor.execute(query_settori)
                records_settori = cursor.fetchall()
                df_settori = pd.DataFrame(records_settori, columns=['settore_esperienza', 'totale'])
                fig_settori = px.bar(df_settori, x='settore_esperienza', y='totale',
                                     title="Numero di Venditori per Settore",
                                     labels={'settore_esperienza': 'Settore', 'totale': 'Totale Venditori'},
                                     color='settore_esperienza', template='plotly_white')  # Cambiato template
                st.plotly_chart(fig_settori, use_container_width=True)
                cursor.close()
            except Exception as e:
                st.error(f"Errore nel generare il report: Numero di Venditori per Settore. Dettaglio: {e}")

        st.markdown("---")

        # Organizza altri grafici in colonne
        col3, col4 = st.columns(2)

        with col3:
            # 3. Distribuzione delle Esperienze nella Vendita
            try:
                cursor = connection.cursor()
                query_esperienza = "SELECT esperienza_vendita, COUNT(*) as totale FROM venditori GROUP BY esperienza_vendita ORDER BY esperienza_vendita"
                cursor.execute(query_esperienza)
                records_esperienza = cursor.fetchall()
                df_esperienza = pd.DataFrame(records_esperienza, columns=['esperienza_vendita', 'totale'])
                fig_esperienza = px.histogram(df_esperienza, x='esperienza_vendita', y='totale',
                                             title="Distribuzione delle Esperienze nella Vendita",
                                             labels={'esperienza_vendita': 'Esperienza (anni)', 'totale': 'Totale Venditori'},
                                             nbins=20, template='plotly_white')  # Cambiato template
                st.plotly_chart(fig_esperienza, use_container_width=True)
                cursor.close()
            except Exception as e:
                st.error(f"Errore nel generare il report: Distribuzione delle Esperienze nella Vendita. Dettaglio: {e}")

        with col4:
            # 4. Città con più Venditori
            try:
                cursor = connection.cursor()
                query_citta = "SELECT citta, COUNT(*) as totale FROM venditori GROUP BY citta ORDER BY totale DESC LIMIT 10"
                cursor.execute(query_citta)
                records_citta = cursor.fetchall()
                df_citta = pd.DataFrame(records_citta, columns=['citta', 'totale'])
                fig_citta = px.pie(df_citta, names='citta', values='totale',
                                   title="Città con più Venditori",
                                   hole=0.3, template='plotly_white')  # Cambiato template
                st.plotly_chart(fig_citta, use_container_width=True)
                cursor.close()
            except Exception as e:
                st.error(f"Errore nel generare il report: Città con più Venditori. Dettaglio: {e}")

        # Aggiungi ulteriori grafici o sezioni se necessario

    # Scheda 4: Gestisci Settori e Profili Venditori
    elif st.session_state.active_tab == "Gestisci Settori e Profili Venditori":
        st.header("🔧 Gestisci Settori e Profili Venditori")
        st.markdown("---")

        # Sezione per aggiungere un nuovo settore
        st.subheader("➕ Aggiungi Nuovo Settore")
        with st.form("form_aggiungi_settore"):
            nuovo_settore = st.text_input("Nome del nuovo settore", placeholder="Inserisci il nome del settore")
            aggiungi_settore = st.form_submit_button("Aggiungi Settore")
            if aggiungi_settore:
                if nuovo_settore.strip():
                    successo = add_settore(connection, nuovo_settore.strip())
                    if successo:
                        st.success(f"Settore **'{nuovo_settore}'** aggiunto con successo!")
                        # Aggiorna manualmente le informazioni
                        settori = get_settori(connection)
                    else:
                        st.warning(f"Il settore **'{nuovo_settore}'** esiste già.")
                else:
                    st.error("🔴 Il campo del settore non può essere vuoto.")

        st.markdown("---")

        # Sezione per modificare il profilo di un venditore
        st.subheader("🔄 Modifica Profilo Venditore")

        # Inizializza lo stato se non esiste
        if 'venditore_selezionato_tab4' not in st.session_state:
            st.session_state.venditore_selezionato_tab4 = None

        with st.form("form_cerca_venditore_tab4"):
            st.markdown("### 🔎 Ricerca Venditore")
            nome_cerca_modifica = st.text_input("Nome e Cognome", placeholder="Inserisci il nome da cercare")
            citta_cerca_modifica = st.selectbox("Città", ["Tutte"] + all_cities)
            cerca_button_modifica = st.form_submit_button("Cerca Venditore")
        
        if cerca_button_modifica:
            # Mappatura dei valori "Tutte" a None
            nome_param = nome_cerca_modifica if nome_cerca_modifica else None
            citta_param = citta_cerca_modifica if citta_cerca_modifica != "Tutte" else None

            records_modifica = search_venditori(
                connection, 
                nome=nome_param, 
                citta=citta_param, 
                settore=None,  
                partita_iva=None,
                agente_isenarco=None
            )
            if records_modifica:
                # Creiamo una lista di venditori da selezionare
                venditori_list = {f"{record[1]} (ID: {record[0]})": record for record in records_modifica}
                venditore_selezionato = st.selectbox("Seleziona il Venditore da Modificare", list(venditori_list.keys()))
                
                if venditore_selezionato:
                    venditore_record = venditori_list[venditore_selezionato]
                    st.session_state.venditore_selezionato_tab4 = venditore_record
                    st.success(f"Venditore selezionato: **{venditore_selezionato}**")
            else:
                st.info("Nessun venditore trovato con i criteri di ricerca inseriti.")

        # Mostra il form per aggiornare tutti i campi solo se un venditore è selezionato
        if st.session_state.venditore_selezionato_tab4:
            venditore = st.session_state.venditore_selezionato_tab4
            st.markdown("---")
            st.subheader("📝 Aggiorna Profilo Venditore")

            # **Correzione Indice per CV**
            if venditore[10] and os.path.exists(venditore[10]):
                try:
                    with open(venditore[10], "rb") as f:
                        cv_bytes = f.read()
                    st.download_button(
                        label="📄 Scarica CV Esistente",
                        data=cv_bytes,
                        file_name=os.path.basename(venditore[10]),
                        mime="application/pdf",
                        key=f"download_existing_{venditore[0]}"
                    )
                except Exception as e:
                    st.error(f"Errore nel leggere il CV: {e}")
            else:
                st.info("**CV Esistente:** N/A")

            with st.form("form_aggiorna_profilo_tab4"):
                st.markdown("### 👤 Informazioni Venditore")
                # Miglioramento del layout del form usando colonne
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    nome_cognome_mod = st.text_input("Nome e Cognome", value=venditore[1], key="nome_cognome_mod")
                    email_mod = st.text_input("Email", value=venditore[2], key="email_mod")
                    telefono_mod = st.text_input("Telefono", value=venditore[3], key="telefono_mod")
                
                with col2:
                    if all_cities:
                        if venditore[4] in all_cities:
                            index_citta = all_cities.index(venditore[4])
                        else:
                            index_citta = 0
                        citta_mod = st.selectbox("Città", all_cities, index=index_citta, key="citta_mod")
                    else:
                        citta_mod = st.selectbox("Città", ["Carica prima il CSV"], key="citta_mod")
                    esperienza_vendita_mod = st.select_slider(
                        "Esperienza nella vendita (anni)", 
                        options=list(range(0, 101)), 
                        value=venditore[5],
                        key="esperienza_vendita_mod"
                    )
                    anno_nascita_mod = st.selectbox(
                        "Anno di Nascita", 
                        options=list(range(1900, 2025)),
                        index=anno_nascita_index(venditore[6]),
                        key="anno_nascita_mod"
                    )
                
                with col3:
                    settori = get_settori(connection)
                    if settori:
                        if venditore[7] in settori:
                            index_settore = settori.index(venditore[7])
                        else:
                            index_settore = 0
                        settore_esperienza_mod = st.selectbox(
                            "Settore di Esperienza", 
                            settori,
                            index=index_settore,
                            key="settore_esperienza_mod"
                        )
                    else:
                        settore_esperienza_mod = st.selectbox(
                            "Settore di Esperienza", 
                            ["Carica prima i settori"],
                            key="settore_esperienza_mod"
                        )
                    partita_iva_mod = st.selectbox(
                        "Partita IVA", 
                        options=["Sì", "No"],
                        index=0 if venditore[8] == "Sì" else 1,
                        key="partita_iva_mod"
                    )
                    agente_isenarco_mod = st.selectbox(
                        "Agente Iscritto Enasarco", 
                        options=["Sì", "No"],
                        index=0 if venditore[9] == "Sì" else 1,
                        key="agente_isenarco_mod"
                    )
                
                st.markdown("---")
                # Rimuovi il titolo per ottimizzare lo spazio
                # st.markdown("### 📄 Aggiorna CV e 📝 Note")
                col4, col5 = st.columns([2, 3])
                with col4:
                    cv_file_mod = st.file_uploader("Carica il nuovo CV (PDF)", type=['pdf'], key="cv_file_mod_tab4")
                with col5:
                    note_mod = st.text_area("Aggiungi o modifica le note sul profilo del venditore", value=venditore[11] if venditore[11] else "", key="note_mod_tab4")
                
                aggiorna_button = st.form_submit_button("Aggiorna Profilo")
                
                if aggiorna_button:
                    cv_path_mod = venditore[10]  # Mantieni il CV esistente se non viene caricato un nuovo file
                    if cv_file_mod is not None:
                        # Salva il file nella cartella 'cv_files' (crea la cartella se non esiste)
                        cv_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cv_files')
                        os.makedirs(cv_dir, exist_ok=True)
                        cv_path_mod = os.path.join(cv_dir, cv_file_mod.name)
                        try:
                            with open(cv_path_mod, "wb") as f:
                                f.write(cv_file_mod.getbuffer())
                            st.success(f"CV salvato in: `{cv_path_mod}`")  # Messaggio di conferma
                        except Exception as e:
                            st.error(f"Errore nel salvataggio del CV: {e}")
                    
                    # Aggiorna tutti i campi
                    successo, messaggio = update_venditore(
                        connection, 
                        venditore_id=venditore[0],
                        nome_cognome=nome_cognome_mod,
                        email=email_mod,
                        telefono=telefono_mod,
                        citta=citta_mod,
                        esperienza_vendita=esperienza_vendita_mod,
                        anno_nascita=anno_nascita_mod,
                        settore_esperienza=settore_esperienza_mod,
                        partita_iva=partita_iva_mod,
                        agente_isenarco=agente_isenarco_mod,
                        cv_path=cv_path_mod,
                        note=note_mod.strip()
                    )
                    
                    if successo:
                        st.success(messaggio)
                        note_aggiornate = verifica_note(connection, venditore[0])
                        st.info(f"Note aggiornate: {note_aggiornate}")
                        # Aggiorna lo stato dei venditori
                        st.session_state.venditori_data = search_venditori(connection)
                        # Aggiorna i dati del venditore selezionato con i dati più recenti
                        updated_records = search_venditori(
                            connection, 
                            nome=nome_cognome_mod, 
                            citta=citta_mod, 
                            settore=settore_esperienza_mod, 
                            partita_iva=partita_iva_mod,
                            agente_isenarco=agente_isenarco_mod
                        )
                        # Trova il venditore aggiornato
                        if updated_records:
                            st.session_state.venditore_selezionato_tab4 = updated_records[0]
                        else:
                            st.session_state.venditore_selezionato_tab4 = None
                    else:
                        st.error(messaggio)

    # Scheda 5: Backup e Ripristino
    elif st.session_state.active_tab == "Backup e Ripristino":
        st.header("🔒 Backup e Ripristino del Database")
        st.markdown("---")

        # Sezione Backup Manuale
        st.markdown("### 📦 Esegui Backup Manuale del Database")
        if st.button("Crea Backup Manuale"):
            with st.spinner("Eseguendo il backup..."):
                successo, risultato = backup_database_python(connection)  # Utilizza la nuova funzione
                if successo:
                    # Crea un nome file con data e ora
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_filename = f"backup_manual_{timestamp}.zip"

                    # Prepara il download del backup
                    st.success("Backup creato con successo!")
                    st.download_button(
                        label="📥 Scarica Backup",
                        data=risultato,
                        file_name=backup_filename,
                        mime="application/zip"
                    )
                    
                    # Aggiorna l'ultimo backup
                    current_time = datetime.now()
                    with open('last_backup.txt', 'w') as f:
                        f.write(current_time.strftime("%Y-%m-%d %H:%M:%S"))
                else:
                    st.error(f"Errore durante il backup: {risultato}")

        st.markdown("---")

        # Sezione Ripristino del Database
        st.markdown("### 🔄 Ripristina il Database da un Backup")
        with st.form("form_ripristino"):
            backup_file = st.file_uploader("Carica il file di backup ZIP contenente i CSV delle tabelle", type=["zip"])
            ripristina_button = st.form_submit_button("Ripristina Database")

            if ripristina_button:
                if backup_file is not None:
                    try:
                        backup_zip_bytes = backup_file.read()
                        with st.spinner("Ripristinando il database..."):
                            successo, messaggio = restore_database_python(connection, backup_zip_bytes)  # Utilizza la nuova funzione
                            if successo:
                                st.success(messaggio)
                                # Aggiorna l'ultimo backup
                                current_time = datetime.now()
                                with open('last_backup.txt', 'w') as f:
                                    f.write(current_time.strftime("%Y-%m-%d %H:%M:%S"))
                            else:
                                st.error(messaggio)
                    except Exception as e:
                        st.error(f"Errore durante il ripristino: {e}")
                else:
                    st.error("🔴 Devi caricare un file di backup valido.")

    # Scheda 6: Esporta/Importa Venditori
    elif st.session_state.active_tab == "Esporta/Importa Venditori":
        st.header("📤 Esporta e 📥 Importa Venditori")
        st.markdown("---")

        # Sezione Esportazione
        st.subheader("➜ Esporta Venditori")

        # Opzioni di esportazione
        formato_export = st.selectbox(
            "Seleziona il formato di esportazione",
            ["CSV", "Excel"],
            key="formato_export"
        )

        # Pulsante per esportare tutti i venditori
        if st.button("Esporta Tutti i Venditori"):
            with st.spinner("Eseguendo l'esportazione..."):
                records = search_venditori(connection)
                if records:
                    # Converti i record in DataFrame
                    df_export = pd.DataFrame(records, columns=[
                        'id', 'nome_cognome', 'email', 'telefono', 'citta',
                        'esperienza_vendita', 'anno_nascita', 'settore_esperienza',
                        'partita_iva', 'agente_isenarco', 'cv', 'note', 'data_creazione'
                    ])
                    
                    if formato_export == "CSV":
                        # Usa sep=';' per allineare il delimitatore
                        csv = df_export.to_csv(index=False, sep=';').encode('utf-8')
                        st.download_button(
                            label="📥 Scarica CSV",
                            data=csv,
                            file_name='venditori_export.csv',
                            mime='text/csv'
                        )
                    elif formato_export == "Excel":
                        # Converti in bytes utilizzando BytesIO
                        buffer = BytesIO()
                        df_export.to_excel(buffer, index=False, engine='openpyxl')
                        buffer.seek(0)
                        st.download_button(
                            label="📥 Scarica Excel",
                            data=buffer,
                            file_name='venditori_export.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )
                    st.success("Esportazione completata con successo!")
                else:
                    st.info("Nessun venditore da esportare.")

        st.markdown("---")

        # Sezione Importazione
        st.subheader("⬅️ Importa Venditori")

        # Caricamento del file
        formato_import = st.selectbox(
            "Seleziona il formato di importazione",
            ["CSV", "Excel"],
            key="formato_import"
        )
        import_file = st.file_uploader("Carica il file ZIP contenente i CSV delle tabelle", type=["zip"])

        if import_file is not None:
            try:
                backup_zip = zipfile.ZipFile(BytesIO(import_file.read()), 'r')
                table_files = [file for file in backup_zip.namelist() if file.endswith('.csv')]

                if not table_files:
                    st.error("Il file ZIP non contiene file CSV validi.")
                else:
                    st.write(f"Totale tabelle da importare: {len(table_files)}")
                    
                    # Mostra una preview dei dati
                    for file in table_files[:1]:  # Mostra solo la preview della prima tabella
                        with backup_zip.open(file) as f:
                            df_preview = pd.read_csv(f)
                            st.write(f"Preview del file `{file}`:")
                            st.dataframe(df_preview.head())

                    if st.button("Importa Database"):
                        with st.spinner("Importando il database..."):
                            try:
                                # Leggi tutti i CSV dal ZIP
                                backup_zip_bytes = import_file.read()
                                successo, messaggio = restore_database_python(connection, backup_zip_bytes)
                                if successo:
                                    st.success(messaggio)
                                    # Aggiorna i dati visualizzati
                                    st.session_state.venditori_data = search_venditori(connection)
                                else:
                                    st.error(messaggio)
                            except Exception as e:
                                st.error(f"Errore durante l'importazione: {e}")
            except zipfile.BadZipFile:
                st.error("Il file caricato non è un file ZIP valido.")
            except Exception as e:
                st.error(f"Errore durante la lettura del file ZIP: {e}")

if __name__ == "__main__":
    main()
