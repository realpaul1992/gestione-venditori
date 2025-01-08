import streamlit as st
import requests  # per eventuali chiamate REST al backend FastAPI
import pandas as pd
import os
from datetime import datetime, timedelta
import plotly.express as px
import base64
from io import BytesIO
import zipfile

# Import delle funzioni dal tuo db_connection.py
from db_connection import (
    create_connection,
    get_settori,
    get_available_cities,   # Assicurati di averla definita in db_connection.py
    search_venditori,       # Restituisce lista di dizionari
    delete_venditore,
    initialize_settori,
    backup_database_python,
    restore_database_python
)

###############################################################################
# 1) Crea la connessione e inizializza i settori
###############################################################################
@st.cache_resource
def get_connection():
    connection = create_connection()
    if connection:
        initialize_settori(connection)
    return connection

###############################################################################
# 2) Esegui, se necessario, il backup automatico
###############################################################################
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
            last_backup_time = current_time - timedelta(days=1)
    else:
        last_backup_time = current_time - timedelta(days=1)

    # Se è passato più di 24 ore, esegui un backup
    if current_time - last_backup_time > timedelta(hours=24):
        st.sidebar.info("Eseguendo backup automatico...")
        successo, risultato = backup_database_python(connection)
        if successo:
            timestamp = current_time.strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_auto_{timestamp}.zip"
            st.sidebar.success(f"Backup automatico creato alle {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            st.sidebar.download_button(
                label="📥 Scarica Backup Automatico",
                data=risultato,
                file_name=backup_filename,
                mime='application/zip'
            )
            with open(last_backup_file, 'w') as f:
                f.write(current_time.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            st.sidebar.error(f"Backup automatico fallito: {risultato}")

###############################################################################
# 3) Funzione di supporto per calcolare l'indice dell'anno di nascita
###############################################################################
def anno_nascita_index(anno):
    anni = list(range(1900, 2025))
    if anno in anni:
        return anni.index(anno)
    else:
        return 0

###############################################################################
# 4) Funzione principale Streamlit
###############################################################################
def main():
    st.set_page_config(
        page_title="Gestione Venditori",
        layout="wide",
        initial_sidebar_state="expanded",
        page_icon="📈"
    )

    # Logo
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo.svg')
    if os.path.exists(logo_path):
        st.image(logo_path, width=250)
    else:
        st.warning("Logo aziendale non trovato. Assicurati che 'logo.svg' sia nella directory.")

    # Inizializzazioni in session_state
    if 'venditori_data' not in st.session_state:
        st.session_state.venditori_data = []
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = 'Inserisci Venditore'
    if 'delete_confirm_id' not in st.session_state:
        st.session_state.delete_confirm_id = None
    if 'display_count' not in st.session_state:
        st.session_state.display_count = 10

    # Connessione al DB
    connection = get_connection()
    if not connection:
        st.error("Impossibile connettersi al database.")
        st.stop()

    # Caricamento CSV delle città (se lo usi localmente)
    # Altrimenti potresti usare get_available_cities(connection) direttamente
    # qui se preferisci la lista di città dal DB. A te la scelta.
    # Esempio: all_cities = get_available_cities(connection)
    # Se vuoi caricare dal CSV:
    all_cities = []

    # Esegui backup automatico
    automatic_backup(connection)

    # Opzioni schede
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

    # Funzioni di supporto eliminazione
    def handle_delete(venditore_id):
        st.session_state.delete_confirm_id = venditore_id

    def confirm_delete(venditore_id):
        successo, messaggio = delete_venditore(connection, venditore_id)
        if successo:
            st.success(messaggio)
            # Rimuovi dalla venditori_data
            st.session_state.venditori_data = [
                v for v in st.session_state.venditori_data if v["id"] != venditore_id
            ]
        else:
            st.error(messaggio)
        st.session_state.delete_confirm_id = None

    ############################################################################
    # ======================  SCHEDA 1: INSERISCI VENDITORE ====================
    ############################################################################
    if st.session_state.active_tab == "Inserisci Venditore":
        st.header("📥 Inserisci Nuovo Venditore")
        with st.form("form_inserisci_venditore"):
            col1, col2, col3 = st.columns(3)

            with col1:
                nome_cognome = st.text_input("Nome e Cognome", placeholder="Inserisci il nome completo")
                email = st.text_input("Email", placeholder="Inserisci l'email")
                telefono = st.text_input("Telefono", placeholder="Inserisci il numero di telefono")

            with col2:
                # Se usi le all_cities dal CSV
                # O se preferisci get_available_cities dal DB, usa:
                # available_cities = get_available_cities(connection)
                # e poi citta = st.selectbox("Città", available_cities)
                if all_cities:
                    citta = st.selectbox("Città", all_cities)
                else:
                    citta = st.text_input("Città (nessun CSV caricato)")

                esperienza_vendita = st.select_slider(
                    "Esperienza nella vendita (anni)",
                    options=list(range(0, 101)),
                    value=0
                )
                anno_nascita = st.selectbox("Anno di Nascita", options=list(range(1900, 2025)))

            with col3:
                settori = get_settori(connection)
                if settori:
                    settore_esperienza = st.selectbox("Settore di Esperienza", settori)
                else:
                    settore_esperienza = st.selectbox("Settore di Esperienza", ["Carica prima i settori"])

                partita_iva = st.selectbox("Partita IVA", ["Sì", "No"])
                agente_isenarco = st.selectbox("Agente Iscritto Enasarco", ["Sì", "No"])

            col4, col5 = st.columns([2, 3])
            with col4:
                cv_file = st.file_uploader("Carica CV (PDF)", type=["pdf"])
            with col5:
                note = st.text_area("Note", placeholder="Inserisci eventuali note")

            submit_button = st.form_submit_button("Aggiungi Venditore")

        if submit_button:
            # Esempio di invio dati a un backend FastAPI
            # Invece, se vuoi scrivere direttamente sul DB, devi usare la tua vecchia add_venditore
            # a te la scelta. Qui simuliamo la chiamata a un endpoint /inserisci_venditore
            if (nome_cognome and email and citta and
                    settore_esperienza != "Carica prima i settori"):
                cv_url = None
                if cv_file is not None:
                    # Avviso: senza un vero storage, salverai localmente in una cartella
                    st.warning("Gestione del caricamento CV non implementata su hosting. Uso cv_url=None.")
                    # O caricalo su un servizio di file-hosting e ottieni un link

                # Dati
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
                    "cv": cv_url if cv_url else "",
                    "note": note.strip() if note else ""
                }

                # Esempio: se hai definito le chiavi in st.secrets
                # altrimenti scrivi le costanti manualmente
                API_URL = st.secrets.get("API_URL", "https://gestione-venditori-production.up.railway.app/inserisci_venditore")
                API_TOKEN = st.secrets.get("API_TOKEN", "0ed0d85a-3820-47e8-a310-b6e88e6d06f3")
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {API_TOKEN}"
                }

                try:
                    r = requests.post(API_URL + "/inserisci_venditore", json=data, headers=headers)
                    if r.status_code == 200:
                        st.success("Venditore inserito correttamente!")
                        # Esempio: ricarica i venditori
                        st.session_state.venditori_data = search_venditori(connection)
                    else:
                        error_msg = r.json().get('detail', 'Errore sconosciuto')
                        st.error(f"Errore: {error_msg}")
                except Exception as e:
                    st.error(f"Errore di connessione: {e}")
            else:
                st.error("Compila i campi obbligatori (Nome, Email, Città, Settore).")

    ############################################################################
    # ======================  SCHEDA 2: CERCA VENDITORI  =======================
    ############################################################################
    elif st.session_state.active_tab == "Cerca Venditori":
        st.header("🔍 Cerca Venditori")
        with st.form("form_cerca_venditori"):
            col1, col2, col3 = st.columns(3)
            with col1:
                nome_cerca = st.text_input("Nome e Cognome")
                partita_iva_cerca = st.selectbox("Partita IVA", ["Tutti", "Sì", "No"])
            with col2:
                db_cities = get_available_cities(connection)
                citta_cerca = st.selectbox("Città", ["Tutte"] + db_cities)
                agente_isenarco_cerca = st.selectbox("Agente Iscritto Enasarco", ["Tutti", "Sì", "No"])
            with col3:
                settori_db = get_settori(connection)
                if settori_db:
                    settore_cerca = st.selectbox("Settore di Esperienza", ["Tutti"] + settori_db)
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
            st.subheader(f"Risultati della Ricerca: {len(st.session_state.venditori_data)} Venditori Trovati")
            venditori_display = st.session_state.venditori_data[:st.session_state.display_count]
            for record in venditori_display:
                with st.expander(f"📌 {record['nome_cognome']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Email:** {record['email']}")
                        st.write(f"**Telefono:** {record['telefono']}")
                        st.write(f"**Città:** {record['citta']}")
                        st.write(f"**Esperienza Vendita:** {record['esperienza_vendita']} anni")
                    with col2:
                        st.write(f"**Settore:** {record['settore_esperienza']}")
                        st.write(f"**Partita IVA:** {record['partita_iva']}")
                        st.write(f"**Agente Iscritto Enasarco:** {record['agente_isenarco']}")
                        st.write(f"**Note:** {record['note']}")
                    st.write(f"**Data Creazione:** {record['data_creazione']}")

                    # Azioni
                    ac1, ac2 = st.columns([1, 1])
                    with ac1:
                        if record['cv']:
                            st.warning("CV presente (path/URL): gestione su hosting esterno.")
                        else:
                            st.info("CV: N/A")
                    with ac2:
                        delete_button = st.button("🗑️ Elimina", key=f"delete_{record['id']}")
                        if delete_button:
                            handle_delete(record["id"])

            if st.session_state.display_count < len(st.session_state.venditori_data):
                if st.button("Carica Altro", key="load_more"):
                    st.session_state.display_count += 10
            else:
                st.info("Hai visualizzato tutti i venditori.")
        else:
            st.info("Nessun venditore trovato.")

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

    ############################################################################
    # ====================  SCHEDA 3: DASHBOARD  ===============================
    ############################################################################
    elif st.session_state.active_tab == "Dashboard":
        st.header("📊 Dashboard")
        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            # Numero totale venditori
            try:
                cursor = connection.cursor()
                query_totale = "SELECT COUNT(*) FROM venditori"
                cursor.execute(query_totale)
                result = cursor.fetchone()
                totale_venditori = result[0] if result else 0
                st.subheader(f"Numero Totale di Venditori: **{totale_venditori}**")
                cursor.close()
            except Exception as e:
                st.error(f"Errore nel calcolo del numero venditori: {e}")

        with col2:
            # Numero di venditori per settore
            try:
                cursor = connection.cursor()
                query_settori = """
                    SELECT settore_esperienza, COUNT(*) as totale
                    FROM venditori
                    GROUP BY settore_esperienza
                """
                cursor.execute(query_settori)
                settori_data = cursor.fetchall()
                df_settori = pd.DataFrame(settori_data, columns=['settore_esperienza', 'totale'])
                fig_settori = px.bar(
                    df_settori,
                    x='settore_esperienza',
                    y='totale',
                    title="Numero di Venditori per Settore",
                    labels={'settore_esperienza': 'Settore', 'totale': 'Totale'},
                    color='settore_esperienza',
                    template='plotly_white'
                )
                st.plotly_chart(fig_settori, use_container_width=True)
                cursor.close()
            except Exception as e:
                st.error(f"Errore dashboard settori: {e}")

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            # Distribuzione esperienze
            try:
                cursor = connection.cursor()
                query_esperienza = """
                    SELECT esperienza_vendita, COUNT(*) as totale
                    FROM venditori
                    GROUP BY esperienza_vendita
                    ORDER BY esperienza_vendita
                """
                cursor.execute(query_esperienza)
                esp_data = cursor.fetchall()
                df_esp = pd.DataFrame(esp_data, columns=['esperienza_vendita', 'totale'])
                fig_esp = px.histogram(
                    df_esp,
                    x='esperienza_vendita',
                    y='totale',
                    title="Distribuzione Esperienze di Vendita",
                    nbins=20,
                    template='plotly_white'
                )
                st.plotly_chart(fig_esp, use_container_width=True)
                cursor.close()
            except Exception as e:
                st.error(f"Errore dashboard esperienza: {e}")

        with c2:
            # Città con più venditori
            try:
                cursor = connection.cursor()
                query_citta = """
                    SELECT citta, COUNT(*) as totale
                    FROM venditori
                    GROUP BY citta
                    ORDER BY totale DESC
                    LIMIT 10
                """
                cursor.execute(query_citta)
                citta_data = cursor.fetchall()
                df_citta = pd.DataFrame(citta_data, columns=['citta', 'totale'])
                fig_citta = px.pie(
                    df_citta,
                    names='citta',
                    values='totale',
                    title="Città con più Venditori",
                    hole=0.3,
                    template='plotly_white'
                )
                st.plotly_chart(fig_citta, use_container_width=True)
                cursor.close()
            except Exception as e:
                st.error(f"Errore dashboard citta: {e}")

    ############################################################################
    # ================= SCHEDA 4: GESTISCI SETTORI E PROFILI ===================
    ############################################################################
    elif st.session_state.active_tab == "Gestisci Settori e Profili Venditori":
        st.header("🔧 Gestisci Settori e Profili Venditori")
        st.markdown("---")

        # Aggiungi Settore
        st.subheader("➕ Aggiungi Nuovo Settore")
        with st.form("form_aggiungi_settore"):
            nuovo_settore = st.text_input("Nome del nuovo settore", placeholder="Inserisci il nome del settore")
            aggiungi_settore_btn = st.form_submit_button("Aggiungi Settore")
        if aggiungi_settore_btn:
            if nuovo_settore.strip():
                # Esempio di aggiunta diretta su DB. Oppure richiesta a FastAPI
                from db_connection import add_settore
                res = add_settore(connection, nuovo_settore.strip())
                if res:
                    st.success(f"Settore '{nuovo_settore}' aggiunto con successo!")
                else:
                    st.warning(f"Settore '{nuovo_settore}' esiste già o errore.")
            else:
                st.error("Il campo settore non può essere vuoto.")

        st.markdown("---")

        # Ricerca Venditore -> Aggiornamento Profili
        st.subheader("🔄 Modifica Profilo Venditore")
        if 'venditore_selezionato_tab4' not in st.session_state:
            st.session_state.venditore_selezionato_tab4 = None

        with st.form("form_cerca_venditore_tab4"):
            st.markdown("### 🔎 Ricerca Venditore")
            nome_cerca_mod = st.text_input("Nome e Cognome", placeholder="Inserisci il nome da cercare")
            citta_cerca_mod = st.text_input("Città", placeholder="Inserisci la città da cercare")
            cerca_btn_mod = st.form_submit_button("Cerca Venditore")
        if cerca_btn_mod:
            nome_param = nome_cerca_mod if nome_cerca_mod else None
            citta_param = citta_cerca_mod if citta_cerca_mod else None

            found_venditori = search_venditori(
                connection,
                nome=nome_param,
                citta=citta_param,
                settore=None,
                partita_iva=None,
                agente_isenarco=None
            )
            if found_venditori:
                venditori_list = {f"{v['nome_cognome']} (ID: {v['id']})": v for v in found_venditori}
                vend_selez = st.selectbox("Seleziona Venditore da Modificare", list(venditori_list.keys()))
                if vend_selez:
                    st.session_state.venditore_selezionato_tab4 = venditori_list[vend_selez]
                    st.success(f"Venditore selezionato: {vend_selez}")
            else:
                st.info("Nessun venditore trovato.")

        if st.session_state.venditore_selezionato_tab4:
            venditore_sel = st.session_state.venditore_selezionato_tab4
            st.markdown("---")
            st.subheader("📝 Aggiorna Profilo Venditore")

            # Visualizza CV se presente
            if venditore_sel["cv"]:
                st.info(f"CV path/URL: {venditore_sel['cv']}")
            else:
                st.info("Nessun CV associato.")

            with st.form("form_aggiorna_venditore_tab4"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    nome_mod = st.text_input("Nome e Cognome", venditore_sel["nome_cognome"])
                    email_mod = st.text_input("Email", venditore_sel["email"])
                    tel_mod = st.text_input("Telefono", venditore_sel["telefono"])
                with c2:
                    citta_mod = st.text_input("Città", venditore_sel["citta"])
                    esp_mod = st.select_slider("Esperienza (anni)", options=list(range(0,101)), value=venditore_sel["esperienza_vendita"])
                    anno_nasc_mod = st.selectbox("Anno di Nascita", list(range(1900, 2025)), index=anno_nascita_index(venditore_sel["anno_nascita"]))
                with c3:
                    settori_db = get_settori(connection)
                    if settori_db:
                        if venditore_sel["settore_esperienza"] in settori_db:
                            idx_settore = settori_db.index(venditore_sel["settore_esperienza"])
                        else:
                            idx_settore = 0
                        settore_mod = st.selectbox("Settore di Esperienza", settori_db, index=idx_settore)
                    else:
                        settore_mod = st.selectbox("Settore di Esperienza", ["Carica prima i settori"])
                    piva_mod = st.selectbox("Partita IVA", ["Sì", "No"], 0 if venditore_sel["partita_iva"]=="Sì" else 1)
                    agente_mod = st.selectbox("Enasarco", ["Sì", "No"], 0 if venditore_sel["agente_isenarco"]=="Sì" else 1)

                st.markdown("---")
                c4, c5 = st.columns([2,3])
                with c4:
                    cv_upload_mod = st.file_uploader("Carica nuovo CV", type=["pdf"])
                with c5:
                    note_mod = st.text_area("Note", venditore_sel["note"] if venditore_sel["note"] else "")

                aggiorna_btn = st.form_submit_button("Aggiorna Profilo")

            if aggiorna_btn:
                # Se vuoi aggiornare via FastAPI, puoi fare come "Inserisci venditore"
                # Se vuoi farlo localmente con un update_venditore, devi importarlo
                st.warning("Aggiornamento venditore localmente non implementato in questo snippet!")
                # A te la scelta di implementare la logica come preferisci (REST o local).


    ############################################################################
    # =====================  SCHEDA 5: BACKUP E RIPRISTINO  ====================
    ############################################################################
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
                else:
                    st.error(f"Errore durante il backup: {risultato}")

        st.markdown("---")
        st.markdown("### 🔄 Ripristina il Database da un Backup")
        with st.form("form_ripristino"):
            backup_file = st.file_uploader("Carica il file di backup ZIP", type=["zip"])
            ripristina_button = st.form_submit_button("Ripristina Database")
        if ripristina_button:
            if backup_file:
                try:
                    backup_zip_bytes = backup_file.read()
                    with st.spinner("Ripristinando il database..."):
                        successo, messaggio = restore_database_python(connection, backup_zip_bytes)
                        if successo:
                            st.success(messaggio)
                        else:
                            st.error(messaggio)
                except Exception as e:
                    st.error(f"Errore durante il ripristino: {e}")
            else:
                st.error("Devi caricare un file ZIP valido.")

    ############################################################################
    # =============  SCHEDA 6: ESPORTA/IMPORTA VENDITORI  ======================
    ############################################################################
    elif st.session_state.active_tab == "Esporta/Importa Venditori":
        st.header("📤 Esporta e 📥 Importa Venditori")
        st.markdown("---")

        st.subheader("➜ Esporta Venditori")
        formato_export = st.selectbox("Seleziona il formato di esportazione", ["CSV", "Excel"])
        if st.button("Esporta Tutti i Venditori"):
            with st.spinner("Eseguendo l'esportazione..."):
                records = search_venditori(connection)  # Ottieni tutti
                if records:
                    df_export = pd.DataFrame(records)
                    if formato_export == "CSV":
                        csv_data = df_export.to_csv(index=False, sep=';').encode('utf-8')
                        st.download_button(
                            label="📥 Scarica CSV",
                            data=csv_data,
                            file_name="venditori_export.csv",
                            mime="text/csv"
                        )
                    else:  # Excel
                        buffer = BytesIO()
                        df_export.to_excel(buffer, index=False, engine='openpyxl')
                        buffer.seek(0)
                        st.download_button(
                            label="📥 Scarica Excel",
                            data=buffer,
                            file_name="venditori_export.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    st.success("Esportazione completata con successo!")
                else:
                    st.info("Nessun venditore da esportare.")

        st.markdown("---")
        st.subheader("⬅️ Importa Venditori (Backup ZIP con CSV)")
        import_file = st.file_uploader("Carica file ZIP contenente CSV", type=["zip"])
        if import_file:
            try:
                backup_zip = zipfile.ZipFile(BytesIO(import_file.read()), 'r')
                table_files = [file for file in backup_zip.namelist() if file.endswith(".csv")]
                if not table_files:
                    st.error("Il file ZIP non contiene CSV validi.")
                else:
                    st.write(f"Trovati {len(table_files)} file CSV nel ZIP.")
                    # Anteprima
                    for file in table_files[:1]:
                        with backup_zip.open(file) as f:
                            df_preview = pd.read_csv(f)
                            st.write(f"Anteprima del file `{file}`:")
                            st.dataframe(df_preview.head())
                    if st.button("Importa Database"):
                        with st.spinner("Importando..."):
                            backup_zip_bytes = import_file.read()
                            successo, messaggio = restore_database_python(connection, backup_zip_bytes)
                            if successo:
                                st.success(messaggio)
                            else:
                                st.error(messaggio)
            except zipfile.BadZipFile:
                st.error("Il file caricato non è un ZIP valido.")
            except Exception as e:
                st.error(f"Errore nel leggere il file ZIP: {e}")

if __name__ == "__main__":
    main()
