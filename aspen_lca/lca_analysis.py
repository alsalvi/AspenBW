import streamlit as st

# Se usi Brightway:
import bw2data
import bw2io
from bw2data.project import projects
projects.set_current("Aspen_LCA_Project")  # o il nome che preferisci

st.set_page_config(page_title="LCA Analysis", layout="centered")
st.title("LCA Analysis")

# Recupera i dati passati dalla pagina precedente
lci_flows = st.session_state.get('lci_flows', [])
lci_selections = st.session_state.get('lci_selections', {})
lci_df = st.session_state.get('lci_df', None)

if not lci_flows or lci_df is None:
    st.warning("Non hai ancora estratto e classificato i flussi Aspen. Torna alla pagina principale e procedi da lì.")
    st.stop()

st.markdown("### Flussi di inventario disponibili")
st.dataframe(lci_df, use_container_width=True, hide_index=True)

st.header("Carica e gestisci database LCA Brightway")
uploaded_db = st.file_uploader("Trascina qui un database LCA (es: ecospold2 .zip, .bw2package)", type=["zip", "bw2package"])
db_name = st.text_input("Nome database (ad es. ecoinvent3_legacy)")

if st.button("Importa database") and uploaded_db and db_name:
    with st.spinner("Import del database in corso..."):
        tmp_path = f"tmp_{uploaded_db.name}"
        with open(tmp_path, "wb") as f:
            f.write(uploaded_db.read())
        if ".bw2package" in uploaded_db.name:
            importer = bw2io.BW2PackageImporter(tmp_path)
            importer.import_databases()
        else:
            importer = bw2io.SingleOutputEcospold2Importer(tmp_path, db_name)
            importer.apply_strategies()
            importer.write_database()
        st.success(f"Database {db_name} importato.")

st.markdown("#### Database disponibili in Brightway:")
st.write(list(bw2data.databases))
