import streamlit as st
import bw2data as bd
from collections import defaultdict

def show_lcia_selector():
    st.markdown("### LCIA method and categories selection")

    # Raggruppa metodi per nome
    categories_by_method = defaultdict(list)
    for m in bd.methods:
        t = tuple(m)
        if not t:
            continue
        method_name = str(t[0])
        categories_by_method[method_name].append(t)

    method_names = sorted(categories_by_method.keys())

    # Controllo inizializzazione valido
    if 'lcia_method_selected' not in st.session_state:
        st.session_state['lcia_method_selected'] = method_names[0]
    else:
        val = st.session_state['lcia_method_selected']
        if not isinstance(val, str) or val not in method_names:
            st.session_state['lcia_method_selected'] = method_names[0]

    if 'lcia_categories_selected' not in st.session_state:
        st.session_state['lcia_categories_selected'] = []

    col1, col2 = st.columns([1, 2], gap='small')

    with col1:
        current_index = method_names.index(st.session_state['lcia_method_selected'])
        chosen_name = st.selectbox(
            "Metodo LCIA:",
            method_names,
            index=current_index,
            key="lcia_method_selectbox"
        )
        st.session_state['lcia_method_selected'] = chosen_name

    with col2:
        st.caption("Impact categories included in the method (select one or more):")
        cats = list(categories_by_method.get(chosen_name, []))
        cats.sort(key=lambda t: (str(t[1]) if len(t) >= 2 else "", str(t[2]) if len(t) >= 3 else ""))

        selected = list(st.session_state['lcia_categories_selected'])
        new_selected = []

        def label_cat(t):
            mid = t[1] if len(t) >= 2 else ""
            ind = t[2] if len(t) >= 3 else ""
            return f"{mid} — {ind}" if mid and ind else str(t)

        def key_cat(t):
            method = t[0] if len(t) >= 1 else ""
            mid = t[1] if len(t) >= 2 else ""
            ind = t[2] if len(t) >= 3 else ""
            return f"lcia_{hash((method, mid, ind))}"

        for i, cat in enumerate(cats):
            label = label_cat(cat)
            key = key_cat(cat)
            checked = cat in selected
            new_val = st.checkbox(label, value=checked, key=key)
            if new_val:
                new_selected.append(cat)

        st.session_state['lcia_categories_selected'] = new_selected

    with st.expander("LCIA selection summary", expanded=False):
        st.write("Method:", st.session_state['lcia_method_selected'])
        st.write("Selected categories:", [ (c[1], c[2]) if len(c) >= 3 else (c[1], '') for c in st.session_state['lcia_categories_selected']])

    st.session_state['lcia_selection_payload'] = {
        "method_name": st.session_state['lcia_method_selected'],
        "categories": st.session_state['lcia_categories_selected'],
    }

    if len(st.session_state['lcia_categories_selected']) == 0:
        st.info("Select at least one impact category to continue.")
    else:
        st.success(f"Selected categories: {len(st.session_state['lcia_categories_selected'])}")
