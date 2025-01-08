import streamlit as st
import requests  # Import di requests per inviare richieste HTTP
from db_connection import (
    create_connection, 
    search_venditori, 
    get_settori, 
    get_available_cities,  
    initialize_settori,
    backup_database_python,  # Per backup
    restore_database_python, # Per ripristino
    delete_venditore
)
import pandas as pd
import os
from datetime import datetime, timedelta
import plotly.express as px  # Per grafici avanzati
import base64  # Per eventuale download CV
from io import BytesIO
import zipfile  # Per gestire file ZIP

# =================== CONFIGURAZIONE BACKEND FASTAPI ===================
API_URL = "https://gestione-venditori-production.up.railway.app"  # <-- Inserisci l'URL base del backend
API_TOKEN = "0ed0d85a-3820-47e8-a310-b6e88e6d06f3"                  # <-- Inserisci il token segreto (se richiesto)

# =================== FUNZIONI DI SUPPORTO ===================
@st.cache_resource
def get_connection():
    connection = create_connection()
    if connection:
        initialize_settori(connection)
    return connection

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
        successo, risultato = backup_database_python(connection)
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
        return 0  # Default a 1900 se non trovato

# =================== MAIN DELL'APPLICAZIONE ===================
def main():
    # Configura la pagina Streamlit
    st.set_page_config(
        page_title="Gestione Venditori",
        layout="wide",
        initial_sidebar_state="expanded",
        page_icon="📈"
    )

    # Inserisci il logo aziendale
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo.svg')
    if os.path.exists(logo_path):
        st.image(logo_path, width=250)
    else:
        st.warning("Logo aziendale non trovato. Assicurati che 'logo.svg' sia nella directory corrente.")

    # Inizializza variabili di sessione
    if 'venditori_data' not in st.session_state:
        st.session_state.venditori_data = []
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = 'Inserisci Venditore'
    if 'delete_confirm_id' not in st.session_state:
        st.session_state.delete_confirm_id = None
    if 'display_count' not in st.session_state:
        st.session_state.display_count = 10

    # Ottieni la connessione al DB locale (se necessario per la dashboard/ricerca)
    connection = get_connection()
    if not connection:
        st.error("Impossibile connettersi al database locale.")
        st.stop()

    # Carica tutte le città dal CSV (solo per l'interfaccia)
    all_cities = load_all_cities()

    # Schede
    schede = [
        "Inserisci Venditore",
        "Cerca Venditori",
        "Dashboard",
        "Gestisci Settori e Profili Venditori",
        "Backup e Ripristino",
        "Esporta/Importa Venditori"
    ]

    st.sidebar.title("📋 Navigazione")
    st.session_state.active_tab = st.sidebar.radio(
        "Seleziona la sezione:",
        schede,
        index=schede.index(st.session_state.active_tab),
        key="schede_radio"
    )

    # Backup Automatico
    automatic_backup(connection)

    # Funzione per gestire l'eliminazione
    def handle_delete(venditore_id):
        st.session_state.delete_confirm_id = venditore_id

    # Funzione per confermare l'eliminazione
    def confirm_delete(venditore_id):
        successo, messaggio = delete_venditore(connection, venditore_id)
        if successo:
            st.success(messaggio)
            # Rimuove il venditore dai dati visualizzati
            st.session_state.venditori_data = [
                v for v in st.session_state.venditori_data if v['id'] != venditore_id
            ]
        else:
            st.error(messaggio)
        st.session_state.delete_confirm_id = None

    # =============== Scheda 1: Inserisci Venditore ===============
    if st.session_state.active_tab == "Inserisci Venditore":
        st.header("📥 Inserisci Nuovo Venditore")
        with st.form("form_inserisci_venditore"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                nome_cognome = st.text_input("Nome e Cognome", placeholder="Inserisci il nome completo")
                email = st.text_input("Email", placeholder="Inserisci l'email")
                telefono = st.text_input("Telefono", placeholder="Inserisci il numero di telefono")
            
            with col2:
                citta = st.selectbox(
                    "Città", 
                    all_cities if all_cities else ["Carica prima il CSV"]
                )
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
            
            col4, col5 = st.columns([2, 3])
            with col4:
                cv_file = st.file_uploader("Carica il CV (PDF)", type=["pdf"])
            with col5:
                note = st.text_area("Note", placeholder="Inserisci eventuali note")
            
            submit_button = st.form_submit_button("Aggiungi Venditore")
            if submit_button:
                if (nome_cognome and email and citta != "Carica prima il CSV"
                    and settore_esperienza != "Carica prima i settori"):
                    
                    cv_url = ""
                    if cv_file is not None:
                        st.warning(
                            "Caricare i CV richiede un'infrastruttura di storage separata. "
                            "Il campo CV non verrà inviato."
                        )
                    
                    # Costruiamo il JSON da inviare a FastAPI
                    data = {
                        "nome_cognome": nome_cognome,
                        "email": email,
                        "telefono": telefono,
                        "citta": citta,
                        "esperienza_vendita": esperienza_vendita,
                        "anno_nascita": anno_nascita,
                        "settore_esperienza": settore_esperienza,
                        "partita_iva": partita_iva,
                        "agente_isenarco": agente_isenarco,
                        "cv": cv_url,
                        "note": note.strip() if note else ""
                    }
                    
                    # Intestazioni
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {API_TOKEN}"
                    }
                    
                    try:
                        # Endpoint esatto: /inserisci_venditore
                        url = f"{API_URL}/inserisci_venditore"
                        response = requests.post(url, json=data, headers=headers)
                        
                        if response.status_code == 200:
                            st.success("Venditore inserito o aggiornato con successo!")
                            # Aggiorna i venditori localmente
                            st.session_state.venditori_data = search_venditori(connection)
                        else:
                            # Stampa dettaglio dell'errore
                            error_detail = response.json().get('detail', 'Errore sconosciuto')
                            st.error(f"Errore: {error_detail}")
                    except requests.exceptions.RequestException as e:
                        st.error(f"Errore di connessione con FastAPI: {e}")
                else:
                    st.error("🔴 Nome, Email, Città e Settore sono obbligatori.")

    # =============== Scheda 2: Cerca Venditori ===============
    elif st.session_state.active_tab == "Cerca Venditori":
        st.header("🔍 Cerca Venditori")
        with st.form("form_cerca_venditori"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                nome_cerca = st.text_input("Nome e Cognome", placeholder="Inserisci il nome da cercare")
                partita_iva_cerca = st.selectbox("Partita IVA", ["Tutti", "Sì", "No"])
            
            with col2:
                available_cities = get_available_cities(connection)
                citta_cerca = st.selectbox("Città", ["Tutte"] + available_cities)
                agente_isenarco_cerca = st.selectbox("Agente Iscritto Enasarco", ["Tutti", "Sì", "No"])
            
            with col3:
                settori = get_settori(connection)
                if settori:
                    settore_cerca = st.selectbox("Settore di Esperienza", ["Tutti"] + settori)
                else:
                    settore_cerca = st.selectbox("Settore di Esperienza", ["Carica prima i settori"])
            
            cerca_button = st.form_submit_button("Cerca")
        
        if cerca_button:
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
            st.session_state.venditori_data = records
            st.session_state.display_count = 10
        else:
            if 'venditori_data' not in st.session_state:
                st.session_state.venditori_data = []

        st.markdown("---")

        if st.session_state.venditori_data:
            st.subheader(f"Risultati: {len(st.session_state.venditori_data)} Venditori Trovati")
            venditori_display = st.session_state.venditori_data[:st.session_state.display_count]

            for record in venditori_display:
                with st.expander(f"📌 {record['nome_cognome']}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**Email:** {record['email']}")
                        st.markdown(f"**Telefono:** {record['telefono']}")
                        st.markdown(f"**Città:** {record['citta']}")
                        st.markdown(f"**Esperienza Vendita:** {record['esperienza_vendita']} anni")
                    
                    with col2:
                        st.markdown(f"**Settore:** {record['settore_esperienza']}")
                        st.markdown(f"**Partita IVA:** {record['partita_iva']}")
                        st.markdown(f"**Agente Iscritto Enasarco:** {record['agente_isenarco']}")
                        st.markdown(f"**Note:** {record['note']}")

                    data_creazione_str = record['data_creazione'].strftime('%Y-%m-%d %H:%M:%S')
                    st.markdown(f"**Data Creazione:** {data_creazione_str}")
                    
                    action_col1, action_col2 = st.columns([1, 1])
                    with action_col1:
                        if record['cv']:
                            st.markdown(f"**CV:** [Scarica]({record['cv']})")
                        else:
                            st.info("**CV:** N/A")
                    with action_col2:
                        delete_button = st.button("🗑️ Elimina", key=f"delete_{record['id']}")
                        if delete_button:
                            handle_delete(record['id'])
            
            if st.session_state.display_count < len(st.session_state.venditori_data):
                if st.button("Carica Altro", key="load_more"):
                    st.session_state.display_count += 10
            else:
                st.info("Hai visualizzato tutti i venditori.")
        else:
            st.info("Nessun venditore trovato.")

        # Conferma Eliminazione
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

    # =============== Scheda 3: Dashboard ===============
    elif st.session_state.active_tab == "Dashboard":
        st.header("📊 Dashboard")
        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            try:
                cursor = connection.cursor()
                query_totale = "SELECT COUNT(*) as totale FROM venditori"
                cursor.execute(query_totale)
                df_totale = cursor.fetchone()
                totale_venditori = df_totale[0] if df_totale else 0
                st.subheader(f"Numero Totale di Venditori: **{totale_venditori}**")
                cursor.close()
            except Exception as e:
                st.error(f"Errore nel calcolo venditori. Dettaglio: {e}")

        with col2:
            try:
                cursor = connection.cursor()
                query_settori = """
                    SELECT settore_esperienza AS settore, COUNT(id) AS totale
                    FROM venditori
                    GROUP BY settore_esperienza
                """
                cursor.execute(query_settori)
                records_settori = cursor.fetchall()
                df_settori = pd.DataFrame(records_settori, columns=['settore', 'totale'])
                fig_settori = px.bar(
                    df_settori, x='settore', y='totale',
                    title="Venditori per Settore",
                    labels={'settore': 'Settore', 'totale': 'Totale'},
                    color='settore', template='plotly_white'
                )
                st.plotly_chart(fig_settori, use_container_width=True)
                cursor.close()
            except Exception as e:
                st.error(f"Errore nel report settori. Dettaglio: {e}")

        st.markdown("---")

        col3, col4 = st.columns(2)
        with col3:
            try:
                cursor = connection.cursor()
                query_esp = "SELECT esperienza_vendita, COUNT(*) as totale FROM venditori GROUP BY esperienza_vendita ORDER BY esperienza_vendita"
                cursor.execute(query_esp)
                rec_esp = cursor.fetchall()
                df_esp = pd.DataFrame(rec_esp, columns=['esperienza_vendita', 'totale'])
                fig_esp = px.histogram(
                    df_esp, x='esperienza_vendita', y='totale',
                    title="Distribuzione Esperienza",
                    labels={'esperienza_vendita': 'Anni', 'totale': 'Totale'},
                    nbins=20, template='plotly_white'
                )
                st.plotly_chart(fig_esp, use_container_width=True)
                cursor.close()
            except Exception as e:
                st.error(f"Errore nel report esperienza. Dettaglio: {e}")

        with col4:
            try:
                cursor = connection.cursor()
                query_c = """
                    SELECT citta, COUNT(*) as totale
                    FROM venditori
                    GROUP BY citta
                    ORDER BY totale DESC
                    LIMIT 10
                """
                cursor.execute(query_c)
                rec_c = cursor.fetchall()
                df_c = pd.DataFrame(rec_c, columns=['citta', 'totale'])
                fig_c = px.pie(
                    df_c, names='citta', values='totale',
                    title="Città con più venditori",
                    hole=0.3, template='plotly_white'
                )
                st.plotly_chart(fig_c, use_container_width=True)
                cursor.close()
            except Exception as e:
                st.error(f"Errore nel report città. Dettaglio: {e}")

    # =============== Scheda 4: Gestisci Settori e Profili ===============
    elif st.session_state.active_tab == "Gestisci Settori e Profili Venditori":
        st.header("🔧 Gestisci Settori e Profili Venditori")
        st.markdown("---")

        st.subheader("➕ Aggiungi Nuovo Settore")
        with st.form("form_aggiungi_settore"):
            nuovo_settore = st.text_input("Nome del nuovo settore", placeholder="Inserisci il nome")
            aggiungi_settore = st.form_submit_button("Aggiungi Settore")
            if aggiungi_settore:
                if nuovo_settore.strip():
                    # Costruiamo il JSON
                    data_settore = {"settore": nuovo_settore.strip()}
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {API_TOKEN}"
                    }
                    try:
                        url_settore = f"{API_URL}/aggiungi_settore"
                        response = requests.post(url_settore, json=data_settore, headers=headers)
                        if response.status_code == 200:
                            st.success(f"Settore '{nuovo_settore}' aggiunto con successo!")
                            # Aggiorna i settori localmente
                            settori = get_settori(connection)
                        else:
                            error_detail = response.json().get('detail', 'Errore sconosciuto')
                            st.error(f"Errore: {error_detail}")
                    except requests.exceptions.RequestException as e:
                        st.error(f"Errore di connessione: {e}")
                else:
                    st.error("Il campo del settore non può essere vuoto.")

        st.markdown("---")

        st.subheader("🔄 Modifica Profilo Venditore")
        if 'venditore_selezionato_tab4' not in st.session_state:
            st.session_state.venditore_selezionato_tab4 = None

        with st.form("form_cerca_venditore_tab4"):
            st.markdown("### 🔎 Ricerca Venditore")
            nome_cerca_modifica = st.text_input("Nome e Cognome")
            citta_cerca_modifica = st.selectbox("Città", ["Tutte"] + all_cities)
            cerca_button_modifica = st.form_submit_button("Cerca Venditore")

        if cerca_button_modifica:
            nome_param = nome_cerca_modifica if nome_cerca_modifica else None
            citta_param = citta_cerca_modifica if citta_cerca_modifica != "Tutte" else None
            rec_modifica = search_venditori(
                connection,
                nome=nome_param,
                citta=citta_param,
                settore=None,
                partita_iva=None,
                agente_isenarco=None
            )
            if rec_modifica:
                venditori_list = {
                    f"{v['nome_cognome']} (ID: {v['id']})": v for v in rec_modifica
                }
                venditore_sel = st.selectbox("Seleziona il Venditore da Modificare", list(venditori_list.keys()))
                if venditore_sel:
                    venditore_record = venditori_list[venditore_sel]
                    st.session_state.venditore_selezionato_tab4 = venditore_record
                    st.success(f"Venditore selezionato: {venditore_sel}")
            else:
                st.info("Nessun venditore trovato.")

        if st.session_state.venditore_selezionato_tab4:
            venditore = st.session_state.venditore_selezionato_tab4
            st.markdown("---")
            st.subheader("📝 Aggiorna Profilo Venditore")

            # Scarica CV
            if venditore['cv'] and venditore['cv'].strip():
                try:
                    resp_cv = requests.get(venditore['cv'])
                    if resp_cv.status_code == 200:
                        st.download_button(
                            label="📄 Scarica CV Esistente",
                            data=resp_cv.content,
                            file_name=os.path.basename(venditore['cv']),
                            mime="application/pdf"
                        )
                except Exception as e:
                    st.error(f"Errore CV: {e}")
            else:
                st.info("**CV Esistente:** N/A")

            with st.form("form_aggiorna_profilo_tab4"):
                st.markdown("### 👤 Informazioni Venditore")
                col1, col2, col3 = st.columns(3)
                with col1:
                    nome_cognome_mod = st.text_input("Nome e Cognome", venditore['nome_cognome'])
                    email_mod = st.text_input("Email", venditore['email'])
                    telefono_mod = st.text_input("Telefono", venditore['telefono'])
                with col2:
                    if all_cities and venditore['citta'] in all_cities:
                        index_citta = all_cities.index(venditore['citta'])
                    else:
                        index_citta = 0
                    citta_mod = st.selectbox("Città", all_cities, index=index_citta)
                    esperienza_mod = st.select_slider(
                        "Esperienza (anni)",
                        options=list(range(0, 101)),
                        value=venditore['esperienza_vendita']
                    )
                    anno_nascita_mod = st.selectbox(
                        "Anno di Nascita",
                        options=list(range(1900, 2025)),
                        index=anno_nascita_index(venditore['anno_nascita'])
                    )
                with col3:
                    settori_loc = get_settori(connection)
                    if settori_loc and venditore['settore_esperienza'] in settori_loc:
                        index_settore = settori_loc.index(venditore['settore_esperienza'])
                    else:
                        index_settore = 0
                    settore_esperienza_mod = st.selectbox(
                        "Settore di Esperienza",
                        settori_loc,
                        index=index_settore
                    )
                    partita_iva_mod = st.selectbox(
                        "Partita IVA", 
                        ["Sì", "No"],
                        index=0 if venditore['partita_iva'] == "Sì" else 1
                    )
                    agente_isenarco_mod = st.selectbox(
                        "Agente Iscritto Enasarco",
                        ["Sì", "No"],
                        index=0 if venditore['agente_isenarco'] == "Sì" else 1
                    )

                st.markdown("---")
                col4, col5 = st.columns([2, 3])
                with col4:
                    cv_file_mod = st.file_uploader("Carica Nuovo CV (PDF)", type=["pdf"])
                with col5:
                    note_mod = st.text_area("Note del Venditore", value=venditore['note'] or "")

                aggiorna_button = st.form_submit_button("Aggiorna Profilo")
                if aggiorna_button:
                    cv_url_mod = ""
                    if cv_file_mod:
                        st.warning("Non gestiamo il caricamento del CV in questa demo.")
                    
                    data_update = {
                        "nome_cognome": nome_cognome_mod,
                        "email": email_mod,
                        "telefono": telefono_mod,
                        "citta": citta_mod,
                        "esperienza_vendita": esperienza_mod,
                        "anno_nascita": anno_nascita_mod,
                        "settore_esperienza": settore_esperienza_mod,
                        "partita_iva": partita_iva_mod,
                        "agente_isenarco": agente_isenarco_mod,
                        "cv": cv_url_mod,
                        "note": note_mod.strip()
                    }
                    
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {API_TOKEN}"
                    }
                    try:
                        url_update = f"{API_URL}/inserisci_venditore"
                        response = requests.post(url_update, json=data_update, headers=headers)
                        if response.status_code == 200:
                            st.success("Profilo venditore aggiornato con successo!")
                            st.session_state.venditori_data = search_venditori(connection)
                        else:
                            error_detail = response.json().get('detail', 'Errore sconosciuto')
                            st.error(f"Errore: {error_detail}")
                    except requests.exceptions.RequestException as e:
                        st.error(f"Errore di connessione: {e}")

    # =============== Scheda 5: Backup e Ripristino ===============
    elif st.session_state.active_tab == "Backup e Ripristino":
        st.header("🔒 Backup e Ripristino del Database")
        st.markdown("---")

        st.markdown("### 📦 Esegui Backup Manuale del Database")
        if st.button("Crea Backup Manuale"):
            with st.spinner("Eseguendo il backup..."):
                successo, risultato = backup_database_python(connection)
                if successo:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_filename = f"backup_manual_{timestamp}.zip"
                    st.success("Backup creato con successo!")
                    st.download_button(
                        label="📥 Scarica Backup",
                        data=risultato,
                        file_name=backup_filename,
                        mime="application/zip"
                    )
                    with open('last_backup.txt', 'w') as f:
                        f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                else:
                    st.error(f"Errore durante il backup: {risultato}")

        st.markdown("---")
        st.markdown("### 🔄 Ripristina il Database da un Backup")
        with st.form("form_ripristino"):
            backup_file = st.file_uploader("Carica il file ZIP contenente i CSV delle tabelle", type=["zip"])
            ripristina_button = st.form_submit_button("Ripristina Database")
            if ripristina_button:
                if backup_file:
                    try:
                        backup_zip_bytes = backup_file.read()
                        with st.spinner("Ripristinando il database..."):
                            successo, messaggio = restore_database_python(connection, backup_zip_bytes)
                            if successo:
                                st.success(messaggio)
                                with open('last_backup.txt', 'w') as f:
                                    f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                            else:
                                st.error(messaggio)
                    except Exception as e:
                        st.error(f"Errore nel ripristino: {e}")
                else:
                    st.error("Devi caricare un file di backup valido.")

    # =============== Scheda 6: Esporta/Importa Venditori ===============
    elif st.session_state.active_tab == "Esporta/Importa Venditori":
        st.header("📤 Esporta e 📥 Importa Venditori")
        st.markdown("---")

        st.subheader("➜ Esporta Venditori")
        formato_export = st.selectbox("Seleziona il formato di esportazione", ["CSV", "Excel"])
        if st.button("Esporta Tutti i Venditori"):
            with st.spinner("Eseguendo l'esportazione..."):
                records = search_venditori(connection)
                if records:
                    df_export = pd.DataFrame(records, columns=[
                        'id', 'nome_cognome', 'email', 'telefono', 'citta',
                        'esperienza_vendita', 'anno_nascita', 'settore_esperienza',
                        'partita_iva', 'agente_isenarco', 'cv', 'note', 'data_creazione'
                    ])
                    if formato_export == "CSV":
                        csv_bytes = df_export.to_csv(index=False, sep=';').encode('utf-8')
                        st.download_button(
                            label="📥 Scarica CSV",
                            data=csv_bytes,
                            file_name='venditori_export.csv',
                            mime='text/csv'
                        )
                    elif formato_export == "Excel":
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
        st.subheader("⬅️ Importa Venditori")
        formato_import = st.selectbox("Seleziona il formato di importazione", ["CSV", "Excel"])
        import_file = st.file_uploader("Carica il file ZIP con i CSV", type=["zip"])

        if import_file:
            try:
                backup_zip = zipfile.ZipFile(BytesIO(import_file.read()), 'r')
                table_files = [file for file in backup_zip.namelist() if file.endswith('.csv')]
                if not table_files:
                    st.error("Il file ZIP non contiene file CSV validi.")
                else:
                    st.write(f"Totale tabelle da importare: {len(table_files)}")
                    for file in table_files[:1]:
                        with backup_zip.open(file) as f:
                            df_preview = pd.read_csv(f)
                            st.write(f"Preview del file `{file}`:")
                            st.dataframe(df_preview.head())

                    if st.button("Importa Database"):
                        with st.spinner("Importando il database..."):
                            try:
                                backup_zip_bytes = import_file.read()
                                successo, messaggio = restore_database_python(connection, backup_zip_bytes)
                                if successo:
                                    st.success(messaggio)
                                    st.session_state.venditori_data = search_venditori(connection)
                                else:
                                    st.error(messaggio)
                            except Exception as e:
                                st.error(f"Errore durante l'importazione: {e}")
            except zipfile.BadZipFile:
                st.error("Il file caricato non è un ZIP valido.")
            except Exception as e:
                st.error(f"Errore nel leggere il file ZIP: {e}")

if __name__ == "__main__":
    main()
