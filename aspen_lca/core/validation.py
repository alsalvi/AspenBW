# core/validation.py
import platform

def ambiente_valido(st):
    """Controlla che lo script sia eseguito su Windows e con pywin32 disponibile"""
    if platform.system() != "Windows":
        st.error("Questo strumento funziona solo su Windows, dove sia installato Aspen Plus con licenza attiva.")
        return False
    try:
        import win32com.client  # Local import per evitare errore su altri OS
    except ImportError:
        st.error("Il modulo pywin32 non è installato. Esegui 'pip install pywin32' e riprova.")
        return False
    return True

def valida_reference_flow(all_selections, all_flows_data, st):
    reference_flows = [flow_id for flow_id, categoria in all_selections.items() if categoria == "Reference Flow"]
    if len(reference_flows) == 0:
        st.warning("⚠️ No flow selected as Reference Flow. Select a Reference Flow to continue.")
        return False, None
    elif len(reference_flows) > 1:
        st.error("❌ Multiple flows selected as Reference Flow! You must select only one.")
        return False, None
    else:
        ref_flow_id = reference_flows[0]
        for flow_data in all_flows_data:
            if flow_data['id'] == ref_flow_id:
                st.success(f"Reference Flow successfully selected: {flow_data['name']}")
                return True, flow_data
        st.error("Reference Flow not found!")
        return False, None
