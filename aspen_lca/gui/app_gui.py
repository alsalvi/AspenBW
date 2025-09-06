import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import tempfile

from core.validation import ambiente_valido, valida_reference_flow
from core.extraction import estrai_flussi
from core.normalization import normalizza_flussi
from core.database_management import gestione_database_brightway
from core.mapping import mapping_flussi_activita
from core.mapping_summary import mostra_tabella_riepilogo
from core.lcia_selection import show_lcia_selector
from core.inventory_builder import build_inventory
from core.lcia_runner import run_lcia


import plotly.graph_objects as go

# Import Brightway
import bw2analyzer as ba
import bw2data as bd
import bw2io as bi
import bw2calc as bc
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

st.set_page_config(page_title="Aspen-Brightway LCA Interface", layout="centered")
st.title("Aspen-Brightway LCA Interface")

# Verifica ambiente
if not ambiente_valido(st):
    st.stop()

uploaded_file = st.file_uploader(
    label="Drag and drop the Aspen file (.bkp) or click here to select it...",
    type=["bkp"],
    accept_multiple_files=False,
    help="Load an Aspen Plus Backup file (.bkp) to automatically extract the flows"
)

def get_options(flow_type, flow_direction):
    if flow_type == "energy":
        return ["-- Select category --", "Technosphere", "Biosphere", "Avoided Product"]
    elif flow_type == "material" and flow_direction == "input":
        return ["-- Select category --", "Technosphere", "Biosphere", "Reference Flow"]
    elif flow_type == "material" and flow_direction == "output":
        return ["-- Select category --", "Biosphere", "Avoided Product", "Reference Flow", "Waste"]
    else:
        return ["-- Select category --"]

if uploaded_file is not None:
    st.success(f"Uloaded file: {uploaded_file.name}")
    if ("bkp_bytes" not in st.session_state) or (st.session_state.get("last_file") != uploaded_file.name):
        st.session_state.bkp_bytes = uploaded_file.read()
        st.session_state.last_file = uploaded_file.name
        st.session_state.flussi_estratti = False
        st.session_state.error_estrazione = False
        st.session_state.energy_flows_data = []
        st.session_state.material_inputs_data = []
        st.session_state.material_outputs_data = []
    extract_clicked = st.button("Extract Flows")
else:
    st.info("Load an Aspen Plus .bkp file and press 'Extract Flows' to continue.")
    st.stop()

if uploaded_file is not None and (st.session_state.get('flussi_estratti') or ('extract_clicked' in locals() and extract_clicked)):
    if not st.session_state.get('flussi_estratti'):
        with st.spinner("Extracting flows from Aspen Plus. Wait..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.bkp') as tmp:
                tmp.write(st.session_state.bkp_bytes)
                tmp_path = tmp.name
            energia, minput, moutput, errore = estrai_flussi(tmp_path, st)
            if errore is None:
                st.session_state.energy_flows_data = energia
                st.session_state.material_inputs_data = minput
                st.session_state.material_outputs_data = moutput
                st.session_state.flussi_estratti = True
                st.session_state.error_estrazione = False
            else:
                st.session_state.error_estrazione = True
                st.session_state.flussi_estratti = False
                st.error(f"❌ Error during flows extraction: {errore}")

if st.session_state.get('flussi_estratti') and not st.session_state.get('error_estrazione'):
    from core.normalization import normalizza_flussi

    all_flows_data = []
    all_selections = {}

    # Flussi energetici - Input utilities
    st.subheader("Inputs: Utilities")
    for idx, flow_data in enumerate(st.session_state.energy_flows_data):
        flow_id = f"energy_{flow_data['name']}"
        util_type = flow_data.get('util_type', 'N/A')
        display_name = f"{flow_data['name']} [Type: {util_type}] — {flow_data['value']:.4f} {flow_data['unit']}"
        options = get_options("energy", "input")
        categoria = st.selectbox(
            label=display_name,
            options=options,
            index=0,
            key=f"select_{flow_id}_{st.session_state.last_file}"
        )
        all_selections[flow_id] = categoria
        all_flows_data.append({
            'id': flow_id,
            'name': flow_data['name'],
            'type': categoria,
            'value': flow_data['value'],
            'unit': flow_data['unit'],
            'util_type': util_type,
            'category': 'energy',
            'direction': 'input'
        })

    # Flussi materiali input
    st.subheader("Inputs: Materials")
    for idx, flow_data in enumerate(st.session_state.material_inputs_data):
        flow_id = f"minput_{flow_data['name']}"
        options = get_options("material", "input")
        categoria = st.selectbox(
            label=f"{flow_data['name']}: {flow_data['value']:.4f} {flow_data['unit']}",
            options=options,
            index=0,
            key=f"select_{flow_id}_{st.session_state.last_file}"
        )
        all_selections[flow_id] = categoria
        all_flows_data.append({
            'id': flow_id,
            'name': flow_data['name'],
            'type': categoria,
            'value': flow_data['value'],
            'unit': flow_data['unit'],
            'util_type': None,
            'category': 'material',
            'direction': 'input'
        })

    # Flussi materiali output
    st.subheader("Outputs: Materials")
    for idx, flow_data in enumerate(st.session_state.material_outputs_data):
        flow_id = f"moutput_{flow_data['name']}"
        options = get_options("material", "output")
        categoria = st.selectbox(
            label=f"{flow_data['name']}: {flow_data['value']:.4f} {flow_data['unit']}",
            options=options,
            index=0,
            key=f"select_{flow_id}_{st.session_state.last_file}"
        )
        all_selections[flow_id] = categoria
        all_flows_data.append({
            'id': flow_id,
            'name': flow_data['name'],
            'type': categoria,
            'value': flow_data['value'],
            'unit': flow_data['unit'],
            'util_type': None,
            'category': 'material',
            'direction': 'output'
        })

    # Validazione: tutti i flussi devono avere categoria
    flussi_non_categorizzati = [
        flow for flow, cat in all_selections.items()
        if cat == "-- Select category --" or cat is None or cat == ""
    ]
    if flussi_non_categorizzati:
        st.warning("You must assign a category to all flows to continue.")
        st.stop()

    reference_ok, ref_flow_data = valida_reference_flow(all_selections, all_flows_data, st)
    if reference_ok and ref_flow_data:
        import pandas as pd
        df = normalizza_flussi(all_flows_data, ref_flow_data)
        st.session_state['lci_df'] = df

        # Ricostruisci Category/Direction
        id_to_cat = {x['name']: x['category'] for x in all_flows_data}
        id_to_dir = {x['name']: x.get('direction', None) for x in all_flows_data}
        categories = []
        directions = []
        for idx, row in df.iterrows():
            flowname = row['Flow']
            categories.append(id_to_cat.get(flowname, 'material'))
            directions.append(id_to_dir.get(flowname, None))
        df['Category'] = categories
        df['Direction'] = directions
        df['Amount_float'] = df['Amount'].astype(float)

        def show_section(title, df_section, highlight=False):
            if df_section.empty:
                return
            if highlight:
                st.markdown(f"### {title}", unsafe_allow_html=True)
            else:
                st.markdown(f"**{title}**")
            st.dataframe(
                df_section[['Flow', 'Amount', 'Unit']],
                use_container_width=True,
                hide_index=True
            )

        # Titolo principale della LCI
        st.markdown("---")
        st.markdown("## Normalized Life Cycle Inventory")

        # Reference Flow, evidenziato e in alto
        ref_df = df[df['Type'] == 'Reference Flow']
        show_section("Reference Flow", ref_df)

        # Avoided products
        av_df = df[df['Type'] == 'Avoided Product']
        show_section("Avoided products", av_df)

        # Inputs: technosphere
        inputs_technosphere_df = df[
            (df['Direction'] == 'input') &
            (df['Type'] == 'Technosphere')
        ]
        show_section("Inputs: technosphere", inputs_technosphere_df)

        # Inputs: biosphere
        inputs_biosphere_df = df[
            (df['Direction'] == 'input') &
            (df['Type'] == 'Biosphere')
        ]
        show_section("Inputs: biosphere", inputs_biosphere_df)

        # Outputs: biosphere
        outputs_biosphere_df = df[
            (df['Direction'] == 'output') &
            (df['Type'] == 'Biosphere')
        ]
        show_section("Outputs: biosphere", outputs_biosphere_df)

        # Outputs: waste
        waste_df = df[df['Type'] == 'Waste']
        show_section("Outputs: waste", waste_df)

        # ===== Sankey Diagram dei flussi materiali =====
        st.markdown("### Material Flows Sankey Diagram")

        from core.visualizations import render_material_sankey
        fig = render_material_sankey(df)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
            
        # --- Linea di separazione grafica e titolo nuova area ---
        st.markdown("---")
        st.markdown("## Brightway project setup")

        # --- Opzione A: Creazione/attivazione nuovo progetto Brightway ---
        nome_nuovo_progetto = st.text_input("Name of the new Brightway project (e.g.: Aspen_BW)")
        if st.button("Create and activate new project"):
            bi.remote.install_project("ecoinvent-3.10-biosphere", nome_nuovo_progetto)
            bd.projects.set_current(nome_nuovo_progetto)
            st.success(f'The new project "{nome_nuovo_progetto}" was created and activated. Biosphere was imported')
            
        # --- Opzione B: Selezione progetto esistente ---
        st.markdown("Or select and activate an existing project:")
        progetti = [p.name for p in bd.projects]  # Ottieni solo nomi veri
        if progetti:
            progetto_scelto = st.selectbox("Available projects:", progetti, key="sel_proj")
            if progetto_scelto != bd.projects.current:
                bd.projects.set_current(progetto_scelto)
                st.info(f'Activated project: "{progetto_scelto}"')
            st.write(f"✅ Currently active project: {bd.projects.current}")
        else:
            st.info("There are no Brightway projects available.")
            
        # --- Importazione database
        gestione_database_brightway()
        
        # === Mapping to Brightway activities ===
        st.markdown("---")
        st.markdown("## Mapping to Brightway activities")

        # Determina un database di default (preferisci ecoinvent se presente)
        available_dbs = sorted(list(bd.databases))  # richiede: import bw2data as bd
        _default_db = next((d for d in available_dbs if str(d).startswith('ecoinvent')), available_dbs if available_dbs else None)

        # Sezione di mapping (container dedicato per evitare flicker del layout)
        with st.container():
            mappatura = mapping_flussi_activita(st.session_state['lci_df'], default_db=_default_db)
            st.session_state['mappatura'] = mappatura  # stato condiviso per gli step successivi

        # Sezione di riepilogo (si aggiorna a ogni rerun con la mappatura corrente)
        st.markdown('### Mapping summary')
        mostra_tabella_riepilogo(st.session_state['lci_df'], st.session_state['mappatura'])


        # === Build Inventory (foreground DB) ===
        st.markdown("---")
        st.markdown("## Build Inventory")
        col_a, col_b = st.columns([1,1])
        with col_a:
            target_db = st.text_input("Target database (foreground)", value=st.session_state.get('target_db', 'aspen_lci'), key='target_db_input')
        with col_b:
            location = st.text_input("Process location", value=st.session_state.get('process_location', 'GLO'), key='process_location_input')

        # Deduce reference product/unit dal Reference Flow
        ref_rows = st.session_state['lci_df'][st.session_state['lci_df']['Type'] == 'Reference Flow']
        if not ref_rows.empty:
            ref_name = ref_rows['Flow'].iloc[0]
            ref_unit = ref_rows['Unit'].iloc[0]
        else:
            ref_name, ref_unit = ("functional unit", "unit")
            
        process_name = st.text_input("Process name", value=f"Aspen process — {ref_name}")
        reference_product = st.text_input("Reference product", value=ref_name)
        reference_unit = st.text_input("Reference unit", value=ref_unit)

        build_inventory_clicked = st.button("Build inventory", type="primary")
        if build_inventory_clicked:
            with st.spinner("Building inventory..."):
                process_meta = {
                    'name': process_name,
                    'location': location,
                    'unit': reference_unit,
                    'reference_product': reference_product,
                    'chimaera': True,
                }
                res = build_inventory(
                    df_lci=st.session_state['lci_df'],
                    mapping=st.session_state.get('mappatura', {}),
                    target_db=target_db,
                    process_meta=process_meta,
                )
                st.session_state['target_db'] = res['database']
                st.session_state['process_key'] = res['process']
                st.session_state['inventory_built'] = True
                st.success(f"Inventory built in DB '{res['database']}'. Edges created: {res['report']['created_edges']}")
                if res['report']['warnings']:
                    with st.expander("Warnings", expanded=False):
                        for w in res['report']['warnings']:
                            st.warning(w)

        # === LCIA selection and run ===
        if st.session_state.get('inventory_built'):
            st.markdown("---")
            st.markdown("## Life Cycle Impact Assessment (LCIA)")
            show_lcia_selector()
            if st.session_state.get('process_key') and st.session_state.get('lcia_selection_payload', {}).get('categories'):
                run_lcia_clicked = st.button("Run LCIA", type="primary")
                if run_lcia_clicked:
                    with st.spinner("Running LCIA..."):
                        proc = bd.get_node(**st.session_state['process_key']) if isinstance(st.session_state['process_key'], dict) else st.session_state['process_key']
                        results = run_lcia(proc, st.session_state['lcia_selection_payload'])
                        # Mappa metodo (stringa tupla) -> unità da metadata Brightway
                        selected_methods = st.session_state['lcia_selection_payload']['categories']
                        units = {}
                        for cat in selected_methods:
                            mt = tuple(cat)  # le categorie sono già tuple Brightway complete
                            try:
                                units[str(mt)] = bd.Method(mt).metadata.get('unit', '')
                            except Exception:
                                units[str(mt)] = ''

                        if results:
                            for m, score in results.items():
                                unit = units.get(m, '')
                                st.write(f"{m}: {score:.6g} {unit}")
                        else:
                            st.info("No LCIA results. Verify method/categories selection.")

            else:
                st.info("Build inventory and select at least one LCIA category to enable LCIA run.")
           

    
elif st.session_state.get('error_estrazione'):
    st.error("❌ Extraction Error. re-upload the file and try again.")
