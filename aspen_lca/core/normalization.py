# core/normalization.py
import pandas as pd

def normalizza_flussi(all_flows_data, reference_flow_data):
    reference_value = reference_flow_data['value']
    if reference_value == 0:
        raise ValueError("Reference Flow value is 0. Normalization is not possible.")

    normalized_data = []
    for flow in all_flows_data:
        raw_value = flow['value']
        category = flow.get('category')
        util_type = flow.get('util_type', '').strip().upper() if flow.get('util_type') else None
        flow_id = flow.get('id', '')  # es. energy_ELECTRIC, minput_AIR, moutput_ASHPROD

        # Normalizzazione base
        normalized_amount = raw_value / reference_value if reference_value else 0.0
        unit = "kg"

        if category == 'energy':
            # Gruppo utilities (ingressi energetici)
            group = 'Input: Utilities'
            if util_type == "ELECTRICITY":
                # W → kWh sul rapporto
                normalized_amount = (raw_value / reference_value) / 3.6e6
                unit = "kWh"
            elif util_type == "WATER":
                normalized_amount = raw_value / reference_value
                unit = "kg"
            else:
                # energia termica: W → MJ sul rapporto
                normalized_amount = (raw_value / reference_value) / 1e6
                unit = "MJ"
        else:
            # Materiali: distinguo input/output usando il prefisso di id
            if str(flow_id).startswith('minput_'):
                group = 'Input: materials'
            elif str(flow_id).startswith('moutput_'):
                group = 'Outputs'
            else:
                group = 'Outputs'  # fallback conservativo
            normalized_amount = raw_value / reference_value
            unit = "kg"

        normalized_data.append({
            'Flow': flow['name'],
            'Type': flow['type'],
            'Amount': f"{normalized_amount:.6f}",
            'Unit': unit,
            'Utility Type': util_type if category == 'energy' else '',
            'Group': group,          # <<< nuovo
            'FlowID': flow_id,       # opzionale per debug/tracking
        })
    return pd.DataFrame(normalized_data)
