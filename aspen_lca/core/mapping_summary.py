# core/mapping_summary.py

from __future__ import annotations

import pandas as pd
import bw2data as bd
import streamlit as st


@st.cache_data(show_spinner=False, ttl=3600)
def _get_act_by_code(db_name: str, code: str):
    try:
        n = bd.get_node(database=db_name, code=code)
        return {"name": n.get("name", "-"), "location": n.get("location", "-")}
    except Exception:
        return {"name": "-", "location": "-"}


def mostra_tabella_riepilogo(df_flussi, mapping):
    rows = []
    for _, row in df_flussi.iterrows():
        flusso = row["Flow"]
        mappatura = mapping.get(flusso)

        mapped_name = "-"
        region = "-"
        density = ""

        if mappatura is not None:
            # Supporta vecchio formato (tuple) e nuovo (dict)
            if isinstance(mappatura, (tuple, list)) and len(mappatura) >= 2:
                db_name, code = mappatura, mappatura[1]
                meta = _get_act_by_code(db_name, code)
                mapped_name = meta["name"]
                region = meta["location"]
            elif isinstance(mappatura, dict):
                db_name = mappatura.get("database")
                code = mappatura.get("code")
                density_val = mappatura.get("density", "")
                try:
                    density = f"{float(density_val):.4f}" if density_val not in (None, "") else ""
                except Exception:
                    density = str(density_val) if density_val is not None else ""
                if db_name and code:
                    meta = _get_act_by_code(db_name, code)
                    mapped_name = meta["name"]
                    region = meta["location"]

        rows.append({
            "Nome Flusso Aspen": flusso,
            "Attività Mappata": mapped_name,
            "Region": region,
            "Amount Normalizzato": row.get("Amount", ""),
            "Unità": row.get("Unit", ""),
            "Density (kg/m³)": density,
        })

    df_summary = pd.DataFrame(rows)
    st.dataframe(df_summary, use_container_width=True)
