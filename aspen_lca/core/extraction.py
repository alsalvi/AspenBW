# core/extraction.py

import pythoncom

def estrai_flussi(tmp_path, st):
    import win32com.client as win32
    import time

    aspen = None
    try:
        # Inizializza COM e crea istanza Aspen Plus
        pythoncom.CoInitialize()
        aspen = win32.Dispatch('Apwn.Document')
        aspen.InitFromArchive2(tmp_path)
        st.info("File .bkp caricato e simulazione avviata...")

        # Imposta le unità SI dove possibile (opzionale)
        try:
            units_node = aspen.Tree.FindNode('\\Data\\Setup\\Global\\Input')
            if units_node:
                for i in range(units_node.Elements.Count):
                    el = units_node.Elements(i)
                    if el and hasattr(el, 'Name') and el.Name in ['GLOBALDATASET', 'INSET', 'OUTSET']:
                        el.Value = 'SI'
        except Exception:
            pass

        # Avvio simulazione con timeout di 60 secondi
        aspen.Engine.Run()
        max_wait = 60
        wait_time = 0
        while wait_time < max_wait:
            time.sleep(2)
            wait_time += 2
            if hasattr(aspen.Engine, 'IsRunning') and not aspen.Engine.IsRunning:
                break
            if hasattr(aspen.Engine, 'ErrorCount') and aspen.Engine.ErrorCount > 0:
                raise RuntimeError(f"Errori Aspen: {aspen.Engine.ErrorCount}")
        if wait_time >= max_wait:
            raise RuntimeError("Timeout Aspen Plus")

        aspen.Save()

        ####################
        # Estrazione utilità
        ####################
        energy_flows = []
        utilities_node = aspen.Tree.FindNode('\\Data\\Utilities')
        if utilities_node:
            for i in range(utilities_node.Elements.Count):
                el = utilities_node.Elements(i)
                if el is not None and hasattr(el, 'Name'):
                    utility_name = el.Name
                    util_type = None
                    amount = None
                    unit = None

                    # Leggi tipo utility UTIL_TYPE
                    try:
                        util_type_node = aspen.Tree.FindNode(f'\\Data\\Utilities\\{utility_name}\\Output\\UTIL_TYPE')
                        if util_type_node:
                            util_type = util_type_node.Value
                    except Exception:
                        util_type = None

                    # Per sicurezza converti a maiuscolo stringa per confronto
                    util_type_upper = str(util_type).strip().upper() if util_type else None

                    try:
                        if util_type_upper == "WATER":
                            # Amount in kg/s da UTL_TRATE
                            trate_node = aspen.Tree.FindNode(f'\\Data\\Utilities\\{utility_name}\\Output\\UTL_TRATE')
                            if trate_node is not None:
                                amount = trate_node.Value
                                unit = "kg/s"
                        elif util_type_upper == "ELECTRICITY":
                            # Amount in W da UTL_EPOWER
                            epower_node = aspen.Tree.FindNode(f'\\Data\\Utilities\\{utility_name}\\Output\\UTL_EPOWER')
                            if epower_node is not None:
                                amount = epower_node.Value
                                unit = "W"
                        elif util_type_upper in ["STEAM", "OIL", "GAS", "COAL", "REFRIGERATION", "GENERAL"]:
                            # Amount in W = UTL_HCOOL * UTL_TRATE
                            hcool_node = aspen.Tree.FindNode(f'\\Data\\Utilities\\{utility_name}\\Output\\UTL_HCOOL')
                            trate_node = aspen.Tree.FindNode(f'\\Data\\Utilities\\{utility_name}\\Output\\UTL_TRATE')
                            if hcool_node is not None and trate_node is not None:
                                amount = hcool_node.Value * trate_node.Value
                                unit = "W"
                    except Exception:
                        amount = None
                        unit = None

                    # Se amount valido, memorizza
                    if amount is not None:
                        energy_flows.append({
                            'name': utility_name,
                            'value': float(amount),
                            'unit': unit,
                            'util_type': util_type
                        })

        ##################
        # Estrazione streams (materiali)
        ##################
        minputs = []
        moutputs = []
        streams_node = aspen.Tree.FindNode('\\Data\\Streams')

        def is_empty(val):
            return val is None or str(val).strip() == ''

        if streams_node:
            for i in range(streams_node.Elements.Count):
                stream = streams_node.Elements(i)
                if stream and hasattr(stream, 'Name'):
                    stream_name = stream.Name
                    output_node = aspen.Tree.FindNode(f'\\Data\\Streams\\{stream_name}\\Output')

                    source = None
                    destination = None
                    mass_flow = None

                    if output_node:
                        for j in range(output_node.Elements.Count):
                            attr = output_node.Elements(j)
                            if attr and hasattr(attr, 'Name'):
                                if attr.Name == 'SOURCE':
                                    source = getattr(attr, 'Value', None)
                                elif attr.Name == 'DESTINATION':
                                    destination = getattr(attr, 'Value', None)
                                elif attr.Name == 'RES_MASSFLOW':
                                    try:
                                        mass_flow = getattr(attr, 'Value', None)
                                    except:
                                        pass

                    if mass_flow is None:
                        try:
                            mass_flow_node = aspen.Tree.FindNode(f'\\Data\\Streams\\{stream_name}\\Output\\RES_MASSFLOW')
                            if mass_flow_node and mass_flow_node.Value is not None:
                                mass_flow = mass_flow_node.Value
                        except:
                            pass

                    d = {
                        'name': stream_name,
                        'value': float(mass_flow) if mass_flow else 0.0,
                        'unit': 'kg/s'
                    }

                    if is_empty(source) and not is_empty(destination):
                        minputs.append(d)
                    elif not is_empty(source) and is_empty(destination):
                        moutputs.append(d)

        return energy_flows, minputs, moutputs, None

    except Exception as e:
        # Restituisci l'errore per gestione GUI
        return [], [], [], str(e)

    finally:
        # Chiudi Aspen e COM cleanup
        try:
            if aspen is not None:
                aspen.Close()
        except Exception:
            pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass
