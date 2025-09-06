# core/mapping.py

from __future__ import annotations

from typing import List, Dict, Any, Iterable, Tuple, Optional
import hashlib

import streamlit as st
import bw2data as bd


# Badge HTML per categoria flusso
def _flow_type_badge(ftype: str) -> str:
    color = {
        'Technosphere': {'bg': '#005aff', 'fg': '#ffffff', 'ch': 'T'},
        'Biosphere': {'bg': '#009900', 'fg': '#ffffff', 'ch': 'B'},
        'Reference Flow': {'bg': '#ffb446', 'fg': '#000000', 'ch': 'R'},
        'Avoided Product': {'bg': '#fff532', 'fg': '#000000', 'ch': 'A'},
        'Waste': {'bg': '#828282', 'fg': '#ffffff', 'ch': 'W'},
    }.get(ftype, {'bg': '#b0b0b0', 'fg': '#000000', 'ch': (ftype[:1] if ftype else '?').upper()})

    return (
        f"<span style='display:inline-flex;align-items:center;"
        f"background:{color['bg']};color:{color['fg']};border-radius:6px;"
        f"padding:2px 8px;font-weight:600;font-family:Arial,sans-serif;'>"
        f"{color['ch']}</span>"
    )


def _format_activity_label(n: Dict[str, Any]) -> str:
    name = n.get("name", "") or ""
    loc = n.get("location", None)
    loc_str = (str(loc) if loc is not None else "")
    loc_part = f" [{loc_str}]" if loc_str else ""
    cats = " | ".join(n.get("categories", []) or [])
    unit = n.get("unit", "") or ""
    unit_part = f" — {unit}" if unit else ""
    return f"{name}{loc_part} ({cats}){unit_part}"


@st.cache_data(show_spinner=False, ttl=3600)
def _index_db_nodes(db_name: str) -> List[Dict[str, Any]]:
    db = bd.Database(db_name)
    out: List[Dict[str, Any]] = []
    for n in db:
        name = n.get("name", "") or ""
        cats = " ".join(n.get("categories", []) or [])
        loc = str(n.get("location", "") or "")
        unit = n.get("unit", "") or ""
        out.append({
            "database": n["database"],
            "code": n["code"],
            "name": name,
            "location": loc,
            "categories": list(n.get("categories", []) or []),
            "unit": unit,
            "search_key": f"{name} {cats} {loc} {unit}".lower(),
        })
    return out


@st.cache_data(show_spinner=False, ttl=600)
def _search_indexed(db_name: str, query: str) -> List[Dict[str, Any]]:
    q = (query or "").strip().lower()
    if not q:
        return []
    nodes = _index_db_nodes(db_name)
    res = [n for n in nodes if q in n["search_key"]]
    res.sort(key=lambda n: ((n.get("name") or "").lower(), n.get("location") or "", tuple(n.get("categories") or ())))
    return res


def cerca_attivita(db_names: Iterable[str] | str, query: str) -> List[Dict[str, Any]]:
    q = (query or "").strip()
    if not q:
        return []
    if isinstance(db_names, str):
        db_iter = [db_names]
    else:
        db_iter = list(db_names)

    seen: set[Tuple[str, str]] = set()
    merged: List[Dict[str, Any]] = []
    for db_name in db_iter:
        for n in _search_indexed(db_name, q):
            key = (n["database"], n["code"])
            if key not in seen:
                merged.append(n)
                seen.add(key)

    merged.sort(key=lambda n: ((n.get("name") or "").lower(), n.get("location") or "", tuple(n.get("categories") or ())))
    return merged


def _stable_keys(base: str, chosen_db: str) -> Dict[str, str]:
    digest = hashlib.sha1(f"{base}|{chosen_db}".encode()).hexdigest()[:8]
    return {
        "db": f"db_{base}",
        "query": f"q_{base}",
        "results": f"res_{base}",
        "select": f"select_{base}_{digest}",
        "button": f"btn_{base}_{digest}",
        "pending": f"pending_{base}_{digest}",
        "density": f"density_{base}_{digest}",
    }


def _mark_pending(flag_key: str):
    st.session_state[flag_key] = True


def mapping_flussi_activita(df_flussi, default_db=None):
    if "mappatura" not in st.session_state:
        st.session_state["mappatura"] = {}
    if "mappatura_db" not in st.session_state:
        st.session_state["mappatura_db"] = {}

    available_dbs = sorted(list(bd.databases))
    if not available_dbs:
        st.info("Nessun database Brightway disponibile nel progetto corrente.")
        return st.session_state["mappatura"]

    # default_db -> stringa singola
    if default_db is None:
        default_db_value = next((d for d in available_dbs if str(d).startswith("ecoinvent")), available_dbs)
    elif isinstance(default_db, (list, tuple)) and len(default_db) > 0:
        default_db_value = str(default_db)
    else:
        default_db_value = str(default_db)

    # Escludi Reference Flow e pulisci mappature orfane
    df_mappabili = df_flussi[df_flussi["Type"] != "Reference Flow"].copy()
    # FIX: usare accessor .str.strip() sulla Series
    df_mappabili["_group_norm"] = df_mappabili["Group"].astype(str).str.strip().str.lower()
    flussi_ammessi = set(df_mappabili["Flow"].tolist())
    st.session_state["mappatura"] = {
        k: v for k, v in st.session_state.get("mappatura", {}).items() if k in flussi_ammessi
    }

    # Messaggio esplicativo
    st.info("Note: the reference flow does not require mapping.")

    groups = [
        ("input: utilities", "Input: Utilities"),
        ("input: materials", "Input: Materials"),
        ("outputs", "Outputs"),
    ]

    for group_key, group_title in groups:
        group_rows = df_mappabili[df_mappabili["_group_norm"] == group_key]
        if group_rows.empty:
            continue

        st.subheader(group_title)

        for _, row in group_rows.iterrows():
            flusso = row["Flow"]
            amount = row.get("Amount", "")
            unit = row.get("Unit", "")
            ftype = (row.get("Type") or "").strip()

            badge = _flow_type_badge(ftype)
            st.markdown(f"{badge} {flusso}", unsafe_allow_html=True)
            st.caption(f"{amount} {unit}")

            base = f"{group_key}:{flusso}"

            # Preselezione database
            prev_db = st.session_state["mappatura_db"].get(flusso, default_db_value)
            col_db, col_q = st.columns([1, 2], gap="small")

            with col_db:
                st.caption("Database")
                try:
                    db_index = available_dbs.index(prev_db)
                except ValueError:
                    db_index = 0
                chosen_db = st.selectbox(
                    "Database",
                    available_dbs,
                    index=db_index,
                    key=f"db_{base}",
                    label_visibility="collapsed",
                )

            # Reset ricerca se cambia DB
            if prev_db != chosen_db:
                st.session_state.pop(f"q_{base}", None)
                st.session_state.pop(f"res_{base}", None)
                st.session_state["mappatura_db"][flusso] = chosen_db

            keys = _stable_keys(base, chosen_db)

            with col_q:
                st.caption("Search activity")
                c_query, c_btn = st.columns([6, 2], gap="small")
                with c_query:
                    query = st.text_input(
                        "Search activity",
                        value=st.session_state.get(keys["query"], ""),
                        key=keys["query"],
                        placeholder="Min 3 characters (name, category or location)",
                        label_visibility="collapsed",
                        on_change=_mark_pending,
                        args=(keys["pending"],),
                    )
                with c_btn:
                    do_search_click = st.button("Search", key=keys["button"], use_container_width=True)

                # Ricerca se: click o Invio (flag pending)
                do_search = do_search_click or st.session_state.pop(keys["pending"], False)
                results_slot = st.container()

                if do_search:
                    q_clean = (query or "").strip()
                    if len(q_clean) < 3:
                        st.info("Type at least 3 characters to search.")
                        st.session_state[keys["results"]] = []
                    else:
                        with results_slot:
                            with st.spinner("Searching in LCA database…"):
                                st.session_state[keys["results"]] = _search_indexed(chosen_db, q_clean)

                risultati = st.session_state.get(keys["results"], [])

                with results_slot:
                    if risultati:
                        prev_key = st.session_state["mappatura"].get(flusso)
                        prev_db_code: Optional[Tuple[str, str]] = None
                        if isinstance(prev_key, (tuple, list)) and len(prev_key) >= 2:
                            prev_db_code = (prev_key, prev_key[1])
                        elif isinstance(prev_key, dict):
                            prev_db_code = (prev_key.get("database"), prev_key.get("code"))

                        no_map_option = {
                            "_no_map": True,
                            "database": None,
                            "code": None,
                            "name": "— No mapping —",
                            "location": "",
                            "categories": [],
                            "unit": "",
                        }
                        options_list = [no_map_option] + risultati

                        default_index = 0
                        if prev_db_code:
                            for i, n in enumerate(risultati, start=1):
                                if (n.get("database"), n.get("code")) == prev_db_code:
                                    default_index = i
                                    break

                        def _format_option(opt):
                            return "— No mapping —" if opt.get("_no_map") else _format_activity_label(opt)

                        scelta_node = st.selectbox(
                            "Select activity",
                            options=options_list,
                            index=default_index,
                            key=keys["select"],
                            format_func=_format_option,
                        )

                        # Aggiorna mappatura
                        if isinstance(scelta_node, dict) and scelta_node.get("_no_map"):
                            st.session_state["mappatura"].pop(flusso, None)
                        else:
                            mapped_unit = (scelta_node.get("unit") or "").strip()
                            st.session_state["mappatura"][flusso] = {
                                "database": scelta_node["database"],
                                "code": scelta_node["code"],
                                "unit": mapped_unit,
                            }

                            # Se l'unità target è volumetrica, richiedi densità obbligatoria
                            unit_lower = mapped_unit.lower()
                            needs_density = unit_lower in ("cubic meter", "m3", "m^3", "cubic metre")
                            if needs_density:
                                density_val = st.number_input(
                                    "Density (kg/m³) for this mapped flow",
                                    min_value=0.0,
                                    step=0.1,
                                    format="%.4f",
                                    key=keys["density"],
                                    help="Mandatory when mapped activity unit is volumetric (m³).",
                                )
                                st.session_state["mappatura"][flusso]["density"] = float(density_val)
                                if density_val <= 0.0:
                                    st.warning(
                                        "Set a valid density (> 0) to proceed with inventory build for this flow.",
                                        icon="⚠️",
                                    )
                    else:
                        if (st.session_state.get(keys["query"], "") or "").strip():
                            st.info("No activity found.")
                        else:
                            st.info("Insert a search query and press Enter or click Search.")

    # Validazione finale densità obbligatoria per mappature a m³
    missing = []
    for k, v in st.session_state["mappatura"].items():
        if isinstance(v, dict):
            u = (v.get("unit") or "").strip().lower()
            if u in ("cubic meter", "m3", "m^3", "cubic metre"):
                d = v.get("density", 0.0)
                try:
                    d = float(d)
                except Exception:
                    d = 0.0
                if d <= 0.0:
                    missing.append(k)
    if missing:
        st.warning(
            "Missing or invalid density (kg/m³) for flows mapped to volumetric units: " + ", ".join(missing),
            icon="⚠️",
        )

    return st.session_state["mappatura"]
