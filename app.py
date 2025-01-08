import streamlit as st
import requests
from db_connection import (
    create_connection,
    search_venditori,
    get_settori,
    get_available_cities,
    initialize_settori,
    backup_database_python,
    restore_database_python,
    delete_venditore,
)
import pandas as pd
import os
from datetime import datetime, timedelta
import plotly.express as px
from io import BytesIO
import zipfile

# =====================
# CONFIGURAZIONI BACKEND FASTAPI
# =====================
API_URL = "https://gestione-venditori-production.up.railway.app"  # <-- URL base della tua FastAPI
API_TOKEN = "0ed0d85a-3820-47e8-a310-b6e88e6d06f3"                  # <-- Token API (se richiesto)

# =====================
# FUNZIONI DI SUPPORTO
# =====================
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
            st.warning("Il file 'italian_cities.csv' non è stato trovato.")
            return []
        
        df = pd.read_csv(csv_path, delimiter=';', encoding='utf-8')
        df.columns = df.columns.str.strip()
        
        if 'denominazione_ita' not in df.columns:
            st.warning("Manca colonna 'denominazione_ita' nel CSV.")
            return []
        
        cities = df['denominazione_ita'].dropna().unique().tolist()
        return sorted(cities)
    except Exception as e:
        st.error(f"Errore lettura CSV: {e}")
        return []

def automatic_backup(connection):
    last_backup_file = 'last_backup.txt'
    current_time = datetime.now()

    if os.path.exists(last_backup_file):
        try:
            with open(last_backup_file, 'r') as f:
                prev_time = f.read().strip()
                last_backup_time = datetime.strptime(prev_time, "%Y-%m-%d %H:%M:%S")
        except:
            last_backup_time = current_time - timedelta(days=1)
    else:
        last_backup_time = current_time - timedelta(days=1)

    if current_time - last_backup_time > timedelta(hours=24):
        st.sidebar.info("Eseguo backup automatico...")
        ok, result = backup_database_python(connection)
        if ok:
            ts = current_time.strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_auto_{ts}.zip"
            st.sidebar.success(f"Backup creato alle {ts}")
            st.sidebar.download_button(
                "Scarica Backup",
                data=result,
                file_name=backup_name,
                mime="application/zip",
            )
            with open(last_backup_file, "w") as f:
                f.write(current_time.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            st.sidebar.error("Backup fallito: " + str(result))

def anno_nascita_index(anno):
    anni = list(range(1900, 2025))
    if anno in anni:
        return anni.index(anno)
    return 0

def main():
    st.set_page_config(page_title="Gestione Venditori", layout="wide", initial_sidebar_state="expanded")

    # Mostra logo
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo.svg')
    if os.path.exists(logo_path):
        st.image(logo_path, width=250)

    if 'venditori_data' not in st.session_state:
        st.session_state.venditori_data = []
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = 'Inserisci Venditore'
    if 'delete_confirm_id' not in st.session_state:
        st.session_state.delete_confirm_id = None
    if 'display_count' not in st.session_state:
        st.session_state.display_count = 10

    conn = get_connection()
    if not conn:
        st.error("Impossibile connettersi al DB locale.")
        st.stop()

    all_cities = load_all_cities()

    tabs = [
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
        tabs,
        index=tabs.index(st.session_state.active_tab),
        key="tabs_radio"
    )

    # Backup automatico
    automatic_backup(conn)

    def handle_delete(venditore_id):
        st.session_state.delete_confirm_id = venditore_id

    def confirm_delete(venditore_id):
        ok, msg = delete_venditore(conn, venditore_id)
        if ok:
            st.success(msg)
            st.session_state.venditori_data = [
                v for v in st.session_state.venditori_data if v['id'] != venditore_id
            ]
        else:
            st.error(msg)
        st.session_state.delete_confirm_id = None

    # 1) Inserisci Venditore
    if st.session_state.active_tab == "Inserisci Venditore":
        st.header("📥 Inserisci Nuovo Venditore")
        with st.form("form_inserisci_venditore"):
            col1, col2, col3 = st.columns(3)
            with col1:
                nome_cognome = st.text_input("Nome e Cognome", placeholder="Mario Rossi")
                email = st.text_input("Email", placeholder="mario.rossi@example.com")
                telefono = st.text_input("Telefono", placeholder="1234567890")
            with col2:
                citta = st.selectbox("Città", all_cities if all_cities else ["Carica prima il CSV"])
                esperienza = st.select_slider("Esperienza (anni)", options=list(range(0, 101)), value=0)
                anno_nascita = st.selectbox("Anno di Nascita", options=list(range(1900, 2025)))
            with col3:
                settori_list = get_settori(conn)
                if settori_list:
                    settore_esp = st.selectbox("Settore di Esperienza", settori_list)
                else:
                    settore_esp = st.selectbox("Settore di Esperienza", ["Carica prima i settori"])
                partita_iva = st.selectbox("Partita IVA", ["Sì", "No"])
                agente_isenarco = st.selectbox("Agente Iscritto Enasarco", ["Sì", "No"])

            col4, col5 = st.columns([2,3])
            with col4:
                cv_file = st.file_uploader("Carica il CV (PDF)", type=["pdf"])
            with col5:
                note = st.text_area("Note", placeholder="Inserisci note")

            submit_btn = st.form_submit_button("Aggiungi Venditore")
            if submit_btn:
                if (nome_cognome and email and citta != "Carica prima il CSV"
                    and settore_esp != "Carica prima i settori"):
                    
                    cv_url = ""
                    if cv_file is not None:
                        st.warning("Caricamento CV non gestito in questa demo.")
                    
                    data_json = {
                        "nome_cognome": nome_cognome,
                        "email": email,
                        "telefono": telefono,
                        "citta": citta,
                        "esperienza_vendita": esperienza,
                        "anno_nascita": anno_nascita,
                        "settore_esperienza": settore_esp,
                        "partita_iva": partita_iva,
                        "agente_isenarco": agente_isenarco,
                        "cv": cv_url,
                        "note": note.strip() if note else ""
                    }
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {API_TOKEN}"
                    }
                    try:
                        resp = requests.post(f"{API_URL}/inserisci_venditore", json=data_json, headers=headers)
                        if resp.status_code == 200:
                            st.success("Venditore inserito/aggiornato con successo!")
                            st.session_state.venditori_data = search_venditori(conn)
                        else:
                            detail = resp.json().get('detail', 'Errore sconosciuto')
                            st.error(f"Errore: {detail}")
                    except requests.exceptions.RequestException as e:
                        st.error(f"Connessione FastAPI fallita: {e}")
                else:
                    st.error("Nome, Email, Città e Settore sono obbligatori.")

    # 2) Cerca Venditori
    elif st.session_state.active_tab == "Cerca Venditori":
        st.header("🔍 Cerca Venditori")
        with st.form("form_cerca_venditori"):
            col1, col2, col3 = st.columns(3)
            with col1:
                nome_cerca = st.text_input("Nome e Cognome")
                iva_cerca = st.selectbox("Partita IVA", ["Tutti", "Sì", "No"])
            with col2:
                citta_lst = get_available_cities(conn)
                citta_cerca = st.selectbox("Città", ["Tutte"] + citta_lst)
                isenarco_cerca = st.selectbox("Agente Iscritto Enasarco", ["Tutti","Sì","No"])
            with col3:
                settori_lst = get_settori(conn)
                if settori_lst:
                    settore_cerca = st.selectbox("Settore di Esperienza", ["Tutti"] + settori_lst)
                else:
                    settore_cerca = st.selectbox("Settore di Esperienza", ["Carica prima i settori"])
            
            btn_cerca = st.form_submit_button("Cerca")

        if btn_cerca:
            nparam = nome_cerca if nome_cerca else None
            cparam = citta_cerca if citta_cerca != "Tutte" else None
            sparam = settore_cerca if settore_cerca != "Tutti" else None
            ivaparam = iva_cerca if iva_cerca != "Tutti" else None
            isnparam = isenarco_cerca if isenarco_cerca != "Tutti" else None

            recs = search_venditori(conn, nparam, cparam, sparam, ivaparam, isnparam)
            st.session_state.venditori_data = recs
            st.session_state.display_count = 10
        else:
            if 'venditori_data' not in st.session_state:
                st.session_state.venditori_data = []

        st.markdown("---")

        if st.session_state.venditori_data:
            st.subheader(f"Risultati: {len(st.session_state.venditori_data)} trovati")
            venditori_list = st.session_state.venditori_data[:st.session_state.display_count]

            for record in venditori_list:
                with st.expander(f"📌 {record['nome_cognome']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Email:** {record['email']}")
                        st.write(f"**Telefono:** {record['telefono']}")
                        st.write(f"**Città:** {record['citta']}")
                        st.write(f"**Esperienza:** {record['esperienza_vendita']} anni")
                    with col2:
                        st.write(f"**Settore:** {record['settore_esperienza']}")
                        st.write(f"**Partita IVA:** {record['partita_iva']}")
                        st.write(f"**Iscritto Enasarco:** {record['agente_isenarco']}")
                        st.write(f"**Note:** {record['note']}")

                    data_cr = record['data_creazione'].strftime("%Y-%m-%d %H:%M:%S")
                    st.write(f"**Data Creazione:** {data_cr}")

                    act1, act2 = st.columns([1,1])
                    with act1:
                        if record['cv']:
                            st.write(f"**CV:** [Scarica]({record['cv']})")
                        else:
                            st.info("N/A")
                    with act2:
                        del_btn = st.button("🗑️ Elimina", key=f"del_{record['id']}")
                        if del_btn:
                            handle_delete(record['id'])
            
            if st.session_state.display_count < len(st.session_state.venditori_data):
                if st.button("Carica Altro", key="load_more"):
                    st.session_state.display_count += 10
            else:
                st.info("Hai visualizzato tutti i risultati.")
        else:
            st.info("Nessun venditore trovato.")

        # Conferma elimina
        if st.session_state.delete_confirm_id is not None:
            vid = st.session_state.delete_confirm_id
            st.warning("Eliminare venditore?", icon="⚠️")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Conferma Eliminazione", key="conf_del"):
                    confirm_delete(vid)
            with c2:
                if st.button("Annulla Eliminazione", key="cancel_del"):
                    st.session_state.delete_confirm_id = None

    # 3) Dashboard
    elif st.session_state.active_tab == "Dashboard":
        st.header("📊 Dashboard")
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            try:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM venditori")
                row = cur.fetchone()
                tot = row[0] if row else 0
                st.subheader(f"Totale Venditori: {tot}")
                cur.close()
            except Exception as e:
                st.error(f"Errore dashboard: {e}")
        with col2:
            try:
                cur = conn.cursor()
                cur.execute("SELECT settore_esperienza, COUNT(*) FROM venditori GROUP BY settore_esperienza")
                rows = cur.fetchall()
                df_s = pd.DataFrame(rows, columns=['settore','totale'])
                fig = px.bar(df_s, x='settore', y='totale', title="Venditori per Settore")
                st.plotly_chart(fig, use_container_width=True)
                cur.close()
            except Exception as e:
                st.error("Errore settori: " + str(e))

        st.markdown("---")
        col3, col4 = st.columns(2)
        with col3:
            try:
                cur = conn.cursor()
                cur.execute("SELECT esperienza_vendita, COUNT(*) FROM venditori GROUP BY esperienza_vendita")
                rows = cur.fetchall()
                df_e = pd.DataFrame(rows, columns=['esp','cnt'])
                fig2 = px.histogram(df_e, x='esp', y='cnt', title="Esperienza")
                st.plotly_chart(fig2, use_container_width=True)
                cur.close()
            except Exception as e:
                st.error(str(e))
        with col4:
            try:
                cur = conn.cursor()
                cur.execute("SELECT citta, COUNT(*) FROM venditori GROUP BY citta ORDER BY COUNT(*) DESC LIMIT 10")
                rows = cur.fetchall()
                df_c = pd.DataFrame(rows, columns=['citta','cnt'])
                fig3 = px.pie(df_c, names='citta', values='cnt', title="Città Principali", hole=0.3)
                st.plotly_chart(fig3, use_container_width=True)
                cur.close()
            except Exception as e:
                st.error(str(e))

    # 4) Gestisci Settori e Profili
    elif st.session_state.active_tab == "Gestisci Settori e Profili Venditori":
        st.header("🔧 Gestisci Settori e Profili Venditori")
        st.markdown("---")

        st.subheader("➕ Aggiungi Nuovo Settore")
        with st.form("form_aggiungi_settore"):
            nuovo_settore = st.text_input("Nome del nuovo settore", "")
            sbt_set = st.form_submit_button("Aggiungi Settore")
            if sbt_set:
                if nuovo_settore.strip():
                    data_ = {"settore": nuovo_settore.strip()}
                    headers = {"Content-Type":"application/json","Authorization":f"Bearer {API_TOKEN}"}
                    try:
                        r = requests.post(f"{API_URL}/aggiungi_settore", json=data_, headers=headers)
                        if r.status_code == 200:
                            st.success(f"Settore '{nuovo_settore}' aggiunto.")
                            _ = get_settori(conn) # Force refresh
                        else:
                            detail = r.json().get('detail','Errore')
                            st.error(detail)
                    except:
                        st.error("Connessione fallback.")
                else:
                    st.error("Campo settore vuoto.")

        st.markdown("---")
        st.subheader("🔄 Modifica Profilo Venditore")

        if 'venditore_selezionato_tab4' not in st.session_state:
            st.session_state.venditore_selezionato_tab4 = None

        with st.form("form_cerca_venditore_tab4"):
            st.markdown("### 🔎 Ricerca Venditore")
            nome_cerca_mod = st.text_input("Nome e Cognome")
            citta_cerca_mod = st.selectbox("Città", ["Tutte"] + all_cities)
            sbt_mod = st.form_submit_button("Cerca Venditore")

        if sbt_mod:
            nparam = nome_cerca_mod if nome_cerca_mod else None
            cparam = citta_cerca_mod if citta_cerca_mod != "Tutte" else None
            recs_mod = search_venditori(conn, nparam, cparam, None, None, None)
            if recs_mod:
                vend_list = {
                    f"{r['nome_cognome']} (ID:{r['id']})": r for r in recs_mod
                }
                vend_sel = st.selectbox("Seleziona Venditore", list(vend_list.keys()))
                if vend_sel:
                    st.session_state.venditore_selezionato_tab4 = vend_list[vend_sel]
                    st.success(f"Venditore selezionato: {vend_sel}")
            else:
                st.info("Nessun venditore trovato.")

        if st.session_state.venditore_selezionato_tab4:
            venditore = st.session_state.venditore_selezionato_tab4
            st.markdown("---")
            st.subheader("📝 Aggiorna Profilo Venditore")

            cv_exist = venditore['cv']
            if cv_exist and cv_exist.strip():
                st.info(f"CV esistente (URL): {cv_exist}")
            else:
                st.info("N/A")

            with st.form("form_modifica_vend"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    nm_mod = st.text_input("Nome e Cognome", venditore['nome_cognome'])
                    em_mod = st.text_input("Email", venditore['email'])
                    tel_mod = st.text_input("Telefono", venditore['telefono'])
                with col2:
                    allc = get_available_cities(conn)
                    if venditore['citta'] in allc:
                        idxc = allc.index(venditore['citta'])
                    else:
                        idxc = 0
                    cit_mod = st.selectbox("Città", allc, index=idxc)
                    esp_mod = st.select_slider("Esperienza", list(range(0,101)), value=venditore['esperienza_vendita'])
                    an_mod = st.selectbox("Anno di Nascita", list(range(1900,2025)), index=anno_nascita_index(venditore['anno_nascita']))
                with col3:
                    sett_loc = get_settori(conn)
                    if venditore['settore_esperienza'] in sett_loc:
                        idx_st = sett_loc.index(venditore['settore_esperienza'])
                    else:
                        idx_st = 0
                    st_mod = st.selectbox("Settore", sett_loc, index=idx_st)
                    iva_mod = st.selectbox("Partita IVA", ["Sì","No"], index=0 if venditore['partita_iva']=="Sì" else 1)
                    ag_mod = st.selectbox("Iscritto Enasarco", ["Sì","No"], index=0 if venditore['agente_isenarco']=="Sì" else 1)
                
                col4, col5 = st.columns([2,3])
                with col4:
                    cv_upd = st.file_uploader("Nuovo CV (PDF)", type=["pdf"])
                with col5:
                    nt_mod = st.text_area("Note", venditore['note'] or "")

                sbt_upd = st.form_submit_button("Aggiorna Profilo")
                if sbt_upd:
                    cv_url_mod = ""
                    if cv_upd:
                        st.warning("Caricamento CV non gestito.")
                    data_upd = {
                        "nome_cognome": nm_mod,
                        "email": em_mod,
                        "telefono": tel_mod,
                        "citta": cit_mod,
                        "esperienza_vendita": esp_mod,
                        "anno_nascita": an_mod,
                        "settore_esperienza": st_mod,
                        "partita_iva": iva_mod,
                        "agente_isenarco": ag_mod,
                        "cv": cv_url_mod,
                        "note": nt_mod.strip()
                    }
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {API_TOKEN}"
                    }
                    try:
                        r = requests.post(f"{API_URL}/inserisci_venditore", json=data_upd, headers=headers)
                        if r.status_code == 200:
                            st.success("Profilo aggiornato!")
                            st.session_state.venditori_data = search_venditori(conn)
                        else:
                            detail = r.json().get('detail', 'Errore')
                            st.error(detail)
                    except:
                        st.error("Connessione fallita.")

    # 5) Backup e Ripristino
    elif st.session_state.active_tab == "Backup e Ripristino":
        st.header("🔒 Backup e Ripristino")
        st.markdown("---")
        if st.button("Crea Backup Manuale"):
            with st.spinner("Backup in corso..."):
                ok, res = backup_database_python(conn)
                if ok:
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    fname = f"backup_manual_{ts}.zip"
                    st.success("Backup creato!")
                    st.download_button("Scarica Backup", data=res, file_name=fname, mime="application/zip")
                else:
                    st.error("Errore: " + str(res))

        st.markdown("---")
        with st.form("form_ripristino"):
            bf = st.file_uploader("Carica ZIP CSV", type=["zip"])
            sb = st.form_submit_button("Ripristina Database")
            if sb:
                if bf:
                    try:
                        zbytes = bf.read()
                        with st.spinner("Ripristino..."):
                            ok, msg = restore_database_python(conn, zbytes)
                            if ok:
                                st.success(msg)
                            else:
                                st.error(msg)
                    except Exception as e:
                        st.error(str(e))
                else:
                    st.error("Nessun file selezionato.")

    # 6) Esporta/Importa Venditori
    elif st.session_state.active_tab == "Esporta/Importa Venditori":
        st.header("📤 Esporta e 📥 Importa Venditori")
        st.markdown("---")

        st.subheader("➜ Esporta Venditori")
        fmt = st.selectbox("Formato", ["CSV","Excel"])
        if st.button("Esporta Tutti i Venditori"):
            rec = search_venditori(conn)
            if rec:
                df_exp = pd.DataFrame(rec, columns=[
                    'id','nome_cognome','email','telefono','citta',
                    'esperienza_vendita','anno_nascita','settore_esperienza',
                    'partita_iva','agente_isenarco','cv','note','data_creazione'
                ])
                if fmt=="CSV":
                    csv_str = df_exp.to_csv(index=False, sep=';').encode('utf-8')
                    st.download_button("Scarica CSV", data=csv_str, file_name="venditori_export.csv", mime="text/csv")
                else:
                    buff = BytesIO()
                    df_exp.to_excel(buff, index=False, engine='openpyxl')
                    buff.seek(0)
                    st.download_button("Scarica Excel", data=buff, file_name="venditori_export.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                st.success("Esportazione completata!")
            else:
                st.info("Nessun venditore da esportare.")

        st.markdown("---")
        st.subheader("⬅️ Importa Venditori")
        fmt_imp = st.selectbox("Formato Import", ["CSV","Excel"])
        fup = st.file_uploader("Carica file ZIP con i CSV", type=["zip"])
        if fup:
            try:
                zfile = zipfile.ZipFile(BytesIO(fup.read()), 'r')
                cfiles = [x for x in zfile.namelist() if x.endswith(".csv")]
                if not cfiles:
                    st.error("Il file ZIP non contiene CSV validi.")
                else:
                    st.write(f"Tabelle trovate: {len(cfiles)}")
                    for cf in cfiles[:1]:
                        with zfile.open(cf) as f:
                            df_prev = pd.read_csv(f)
                            st.write(f"Anteprima '{cf}':")
                            st.dataframe(df_prev.head())
                    if st.button("Importa Database"):
                        with st.spinner("Import in corso..."):
                            try:
                                zip_bytes = fup.read()
                                ok, msg = restore_database_python(conn, zip_bytes)
                                if ok:
                                    st.success(msg)
                                    st.session_state.venditori_data = search_venditori(conn)
                                else:
                                    st.error(msg)
                            except Exception as e:
                                st.error(str(e))
            except zipfile.BadZipFile:
                st.error("File ZIP non valido.")
            except Exception as e:
                st.error(str(e))

if __name__ == "__main__":
    main()
