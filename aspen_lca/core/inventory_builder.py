# core/inventory_builder.py

from __future__ import annotations

from typing import Dict, Tuple, Any, Optional, Union

import bw2data as bd

# Tipi utili: supporta sia vecchia tupla (db, code) sia nuovo dict con density
MappingValue = Union[Tuple[str, str], Dict[str, Any]]
MappingType = Dict[str, MappingValue]  # {Flow: (db, code)} oppure {Flow: {"database","code","unit","density"}}

def ensure_database(db_name: str) -> bd.Database:
    """
    Crea o recupera un database Brightway per l'inventario custom.
    Non modifica database importati (es. ecoinvent).
    """
    if db_name not in bd.databases:
        bd.Database(db_name).register()
    return bd.Database(db_name)

def create_process_node(
    db: bd.Database,
    name: str,
    location: Optional[str],
    unit: str,
    reference_product: str,
    code: Optional[str] = None,
    chimaera: bool = True,
    extra: Optional[dict] = None,
):
    """
    Crea un nodo di processo; per default crea un nodo chimaera (process+reference product).
    - chimaera True: type='processwithreferenceproduct', con unit e reference product
    - chimaera False: type='process'
    """
    attributes = {
        "name": name,
        "database": db.name,
        "location": location if location else "GLO",
    }
    if chimaera:
        attributes.update({
            "type": "processwithreferenceproduct",
            "unit": unit,
            "reference product": reference_product,
        })
    else:
        attributes.update({"type": "process"})
    if code:
        attributes["code"] = code
    if extra:
        attributes.update(extra)

    node = db.new_node(**attributes)
    node.save()
    return node

def _resolve_target_product(db_name: str, code: str):
    """Risolve un prodotto/attività target via (database, code)."""
    return bd.get_node(database=db_name, code=code)

def _add_technosphere_consumption_edge(process_node, target_node, amount: float):
    e = process_node.new_edge(
        type="technosphere",
        amount=float(amount),
        input=target_node,
        output=process_node,
    )
    e.save()
    return e

def _add_technosphere_substitution_edge(process_node, target_node, amount: float):
    e = process_node.new_edge(
        type="substitution",
        amount=float(amount),
        input=target_node,
        output=process_node,
    )
    e.save()
    return e

def _add_technosphere_production_edge(process_node, amount: float):
    e = process_node.new_edge(
        type="production",
        amount=float(amount),
        input=process_node,   # per chimaera, il proprio prodotto
        output=process_node,
    )
    e.save()
    return e

def _add_biosphere_edge(process_node, biosphere_flow_node, amount: float):
    e = process_node.new_edge(
        type="biosphere",
        amount=float(amount),
        input=biosphere_flow_node,
        output=process_node,
    )
    e.save()
    return e

# Normalizzazione etichette unità per evitare falsi mismatch
_UNIT_ALIASES = {
    "kg": "kilogram",
    "kilograms": "kilogram",
    "mj": "megajoule",
    "megajoules": "megajoule",
    "kwh": "kilowatt hour",
    "kw·h": "kilowatt hour",
    "kw h": "kilowatt hour",
    "m3": "cubic meter",
    "m^3": "cubic meter",
    "cubic metre": "cubic meter",
}
def _norm_unit(u: Optional[str]) -> str:
    u = (u or "").strip().lower()
    return _UNIT_ALIASES.get(u, u)

def _units_warning_if_mismatch(row_unit: str, target_unit: Optional[str]) -> Optional[str]:
    """Confronto con normalizzazione alias (kg~kilogram, MJ~megajoule, kWh~kilowatt hour, m3~cubic meter)."""
    if not target_unit:
        return None
    a = _norm_unit(row_unit)
    b = _norm_unit(target_unit)
    if a and b and a != b:
        return f"Unit mismatch: LCI row unit '{row_unit}' vs target product unit '{target_unit}'."
    return None

def _parse_mapping_entry(entry: MappingValue) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[float]]:
    """
    Ritorna (db_name, code, target_unit, density) a partire da vecchio (db, code) o nuovo dict.
    """
    if isinstance(entry, (tuple, list)) and len(entry) >= 2:
        return entry, entry[1], None, None
    if isinstance(entry, dict):
        db = entry.get("database")
        code = entry.get("code")
        unit = entry.get("unit")
        dens = entry.get("density")
        try:
            dens = float(dens) if dens is not None else None
        except Exception:
            dens = None
        return db, code, unit, dens
    return None, None, None, None

def _convert_if_needed(amount: float, row_unit: Optional[str], target_unit: Optional[str], density: Optional[float], flow_name: str, warnings: list) -> float:
    """
    Converte amount se row_unit è kg e target_unit è m³, usando la densità fornita in mapping.
    Se densità mancante o non valida, aggiunge warning ed evita di convertire.
    """
    a = _norm_unit(row_unit)
    b = _norm_unit(target_unit)
    if a == "kilogram" and b == "cubic meter":
        if density and density > 0.0:
            return amount / float(density)
        else:
            warnings.append(f"Missing or invalid density for flow '{flow_name}' mapped to volumetric unit; cannot convert kg→m³.")
    return amount

def edge_from_row(
    process_node,
    row: Any,
    mapping: MappingType,
    products_cache: Dict[Tuple[str, str], Any],
) -> Dict[str, Any]:
    """
    Traduce una riga del DataFrame LCI normalizzato in uno o più edges Brightway.
    row atteso con colonne: Flow, Type, Amount, Amount_float, Unit, Group, Direction.
    mapping: {Flow: (db, code)} oppure {Flow: {"database","code","unit","density"}}
    """
    flow = row["Flow"]
    ftype = row["Type"]
    direction = row.get("Direction", None)
    row_unit = row.get("Unit", None)
    amount = float(row.get("Amount_float", float(row["Amount"])))
    created = []
    warnings = []

    # 1) Reference Flow: SEMPRE crea la produzione, senza alcuna dipendenza dal mapping
    if ftype == "Reference Flow":
        _add_technosphere_production_edge(process_node, amount)
        created.append(("production", flow, amount))
        return {"created": created, "warnings": warnings}

    # 2) Per gli altri tipi, richiedi mappatura (se assente, salta con warning)
    map_entry = mapping.get(flow)
    if ftype in ("Biosphere", "Technosphere", "Avoided Product", "Waste") and not map_entry:
        warnings.append(f"Flow '{flow}' not mapped; skipping.")
        return {"created": created, "warnings": warnings}

    # Se non serve mappatura ma manca (caso raro), interrompi con warning
    if not map_entry:
        warnings.append(f"Flow '{flow}' has no mapping; skipping.")
        return {"created": created, "warnings": warnings}

    db_name, code, target_unit_from_map, density = _parse_mapping_entry(map_entry)
    if not db_name or not code:
        warnings.append(f"Invalid mapping for flow '{flow}'; skipping.")
        return {"created": created, "warnings": warnings}

    key = (db_name, code)
    if key not in products_cache:
        products_cache[key] = _resolve_target_product(db_name, code)
    target = products_cache[key]

    # Determina l'unità target (preferisci metadati del nodo, altrimenti quella salvata nel mapping)
    target_unit = target.get("unit") or target_unit_from_map

    # Conversione condizionata kg -> m3 con densità da mapping (solo per flussi mappati)
    amount_converted = _convert_if_needed(amount, row_unit, target_unit, density, flow, warnings)

    # Aggiungi warning mismatch SOLO se non è un caso di alias equivalente e se non si è convertito
    if amount_converted == amount:
        wm = _units_warning_if_mismatch(row_unit or "", target_unit or "")
        if wm:
            warnings.append(wm)

    # Routing per tipo flusso
    if ftype == "Biosphere":
        # Uptake (input) -> amount negativo; Emissione (output o None) -> amount positivo
        dirn = (direction or "").strip().lower()
        signed_amount = -amount_converted if dirn == "input" else amount_converted
        _add_biosphere_edge(process_node, target, signed_amount)
        created.append(("biosphere", flow, signed_amount))
        return {"created": created, "warnings": warnings}


    if ftype == "Avoided Product":
        _add_technosphere_substitution_edge(process_node, target, amount_converted)
        created.append(("substitution", flow, amount_converted))
        return {"created": created, "warnings": warnings}

    if ftype == "Waste":
        # Modella i rifiuti in uscita come consumo di un servizio di trattamento,
        # adeguando il segno dell'amount alla convenzione del provider (RP).
        dirn = (direction or "").strip().lower()
        if dirn not in ("", "output"):
            warnings.append(
                f"Waste flow '{flow}' with Direction='{direction}' treated as output (treatment consumption)."
            )

        # Rileva il segno della produzione di riferimento del provider
        rp_amount = 0.0
        try:
            # Prende il primo exchange di produzione; per i 'treatment of ...' ecoinvent è tipicamente < 0
            prod_exchanges = list(target.production())
            if prod_exchanges:
                rp_amount = float(prod_exchanges.get("amount", 0.0))
        except Exception:
            rp_amount = 0.0

        # Se il provider ha RP negativo (treatment), il consumo deve essere positivo
        signed_amount = abs(amount_converted) if rp_amount < 0 else -abs(amount_converted)

        _add_technosphere_consumption_edge(process_node, target, signed_amount)
        created.append(("technosphere-waste-treatment", flow, signed_amount))
        return {"created": created, "warnings": warnings}


    if ftype == "Technosphere":
        if direction == "input":
            _add_technosphere_consumption_edge(process_node, target, amount_converted)
            created.append(("technosphere-consumption", flow, amount_converted))
        elif direction == "output":
            # Produzione verso un prodotto esterno (co‑prodotto)
            e = process_node.new_edge(
                type="production",
                amount=float(amount_converted),
                input=target,
                output=process_node,
            )
            e.save()
            created.append(("technosphere-production-external", flow, amount_converted))
        else:
            _add_technosphere_consumption_edge(process_node, target, amount_converted)
            created.append(("technosphere-consumption-fallback", flow, amount_converted))
        return {"created": created, "warnings": warnings}

    warnings.append(f"Row for flow '{flow}' with Type '{ftype}' not handled; skipped.")
    return {"created": created, "warnings": warnings}

def build_inventory(
    df_lci,
    mapping: MappingType,
    target_db: str,
    process_meta: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Orchestrazione: crea/recupera DB, crea processo, agrega edges da df_lci, ritorna info per LCIA.
    """
    db = ensure_database(target_db)

    name = process_meta.get("name")
    location = process_meta.get("location", "GLO")
    unit = process_meta.get("unit")
    reference_product = process_meta.get("reference_product")
    code = process_meta.get("code")
    chimaera = bool(process_meta.get("chimaera", True))
    extra = process_meta.get("extra", {})

    process_node = create_process_node(
        db=db,
        name=name,
        location=location,
        unit=unit,
        reference_product=reference_product,
        code=code,
        chimaera=chimaera,
        extra=extra,
    )

    products_cache: Dict[Tuple[str, str], Any] = {}
    created_edges = 0
    warnings_all = []

    for _, row in df_lci.iterrows():
        result = edge_from_row(process_node, row, mapping, products_cache)
        created_edges += len(result.get("created", []))
        warnings_all.extend(result.get("warnings", []))

    # Guardia anti-orfani: se per qualsiasi motivo non c'è produzione, crea un edge di produzione minimo
    if len(list(process_node.production())) == 0:
        _add_technosphere_production_edge(process_node, 1.0)
        created_edges += 1
        warnings_all.append("No production exchange found on the foreground process; added a fallback production of 1.0.")

    report = {
        "created_edges": created_edges,
        "warnings": [w for w in warnings_all if w],
    }

    return {
        "database": target_db,
        "process": process_node.key,
        "report": report,
    }
