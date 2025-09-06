# core/lcia_runner.py
from __future__ import annotations
from typing import Dict, Any, Tuple, List
import bw2data as bd
import bw2calc as bc

def _as_method_tuples(lcia_selection: Dict[str, Any]) -> List[Tuple]:
    """
    Converte il payload di show_lcia_selector in lista di tuple metodo complete.
    lcia_selection: {'method_name': <str>, 'categories': [tuple method complete]}
    """
    cats = lcia_selection.get("categories", [])
    # cats sono già tuple Brightway (('Method', 'Midpoint', 'Indicator'), ...)
    return [tuple(c) for c in cats]

def run_lcia(process_node, lcia_selection: Dict[str, Any]) -> Dict[str, float]:
    """
    Esegue LCIA per 1 unità funzionale del processo creato (functional edge del chimaera).
    Ritorna dict {method_tuple: score}.
    """
    methods = _as_method_tuples(lcia_selection)
    if not methods:
        return {}

    # Vector di domanda: 1 unità del processo creato (chimaera: il proprio prodotto)
    demand = {process_node: 1.0}

    results: Dict[str, float] = {}

    # Esegui LCIA per ogni categoria selezionata
    for m in methods:
        lca = bc.LCA(demand, method=m)
        lca.lci()
        lca.lcia()
        results[str(m)] = float(lca.score)

    return results
