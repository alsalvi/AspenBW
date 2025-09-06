# core/database_management.py

import streamlit as st
import bw2data as bd
import bw2io as bi

def gestione_database_brightway():
    """Visualizza i database presenti e permette di importare Ecoinvent via credenziali."""

    st.markdown("### LCA databases available in the current project")
    db_list = list(bd.databases)
    if db_list:
        st.write("Imported databases:")
        for db in db_list:
            st.write(f"- {db}")
    else:
        st.info("⚠️ No database present in the current project.")

    st.markdown("### Import Ecoinvent database (login required)")

    with st.expander("Import Ecoinvent database"):
        eco_version = st.text_input("Ecoinvent version (eg: 3.9)", key="eco_version")
        eco_model = st.selectbox(
            "System model",
            ['cutoff', 'consequential', 'allocation at point of substitution'],
            key="eco_model"
        )
        eco_user = st.text_input("Username Ecoinvent", key="eco_user")
        eco_pass = st.text_input("Password Ecoinvent", type="password", key="eco_pass")

        if st.button("Import Ecoinvent database"):
            try:
                with st.spinner("Importing database, this could take several minutes..."):
                    bi.import_ecoinvent_release(
                        version=eco_version,
                        system_model=eco_model,
                        username=eco_user,
                        password=eco_pass
                    )
                st.success("Database Ecoinvent successfully imported!")
            except Exception as e:
                st.error(f"Importing error: {e}")
