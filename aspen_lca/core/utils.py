# core/utils.py
import streamlit as st

def mostra_selettori_flussi(st):
    all_flows_data = []
    all_selections = {}

    st.subheader("Energy Flows (SI) e categoria")
    for idx, flow_data in enumerate(st.session_state.energy_flows_data):
        flow_id = f"energy_{flow_data['name']}"
        categoria = st.selectbox(
            f"{flow_data['name']}: {flow_data['value']:.4f} {flow_data['unit']}",
            options=["Reference Flow", "Technosphere", "Biosphere", "Avoided Product"],
            index=1,
            key=f"select_{flow_id}_{st.session_state.last_file}"
        )
        all_selections[flow_id] = categoria
        all_flows_data.append({
            'id': flow_id,
            'name': flow_data['name'],
            'type': categoria,
            'value': flow_data['value'],
            'unit': flow_data['unit'],
            'category': 'energy'
        })

    st.subheader("Material Inputs (SI) e categoria")
    for idx, flow_data in enumerate(st.session_state.material_inputs_data):
        flow_id = f"minput_{flow_data['name']}"
        categoria = st.selectbox(
            f"{flow_data['name']}: {flow_data['value']:.4f} {flow_data['unit']}",
            options=["Reference Flow", "Technosphere", "Biosphere"],
            index=1,
            key=f"select_{flow_id}_{st.session_state.last_file}"
        )
        all_selections[flow_id] = categoria
        all_flows_data.append({
            'id': flow_id,
            'name': flow_data['name'],
            'type': categoria,
            'value': flow_data['value'],
            'unit': flow_data['unit'],
            'category': 'material'
        })

    st.subheader("Material Outputs (SI) e categoria")
    for idx, flow_data in enumerate(st.session_state.material_outputs_data):
        flow_id = f"moutput_{flow_data['name']}"
        categoria = st.selectbox(
            f"{flow_data['name']}: {flow_data['value']:.4f} {flow_data['unit']}",
            options=["Reference Flow", "Biosphere", "Waste", "Avoided Product"],
            index=1,
            key=f"select_{flow_id}_{st.session_state.last_file}"
        )
        all_selections[flow_id] = categoria
        all_flows_data.append({
            'id': flow_id,
            'name': flow_data['name'],
            'type': categoria,
            'value': flow_data['value'],
            'unit': flow_data['unit'],
            'category': 'material'
        })

    return all_flows_data, all_selections

def mostra_tabella_normalizzata(all_flows_data, reference_flow_data, st):
    from core.normalization import normalizza_flussi
    df = normalizza_flussi(all_flows_data, reference_flow_data)
    st.markdown("### 📊 Normalized Life Cycle Inventory")
    st.info(f"Normalizzazione basata su: {reference_flow_data['name']} = {reference_flow_data['value']:.4f} {reference_flow_data['unit']}")
    st.dataframe(df, use_container_width=True, hide_index=True)
    # Conteggi di categoria
    categorie = [row['type'] for row in all_flows_data]
    counts = {k: categorie.count(k) for k in set(categorie)}
    st.info("Conteggio categorie: " + ", ".join(f"{k}: {v}" for k,v in counts.items()))
