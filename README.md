# Aspen-Brightway LCA Interface (up to LCIA)

Streamlit app to:
- Load an Aspen Plus .bkp file and extract process flows.[1]
- Normalize flows against a selected Reference Flow and display the LCI.[1]
- Manage Brightway projects/databases (including optional ecoinvent import with credentials).[1]
- Map flows to Brightway activities and run LCIA on selected categories.[1]

Note: the “Process contributions” section is excluded in this version.[1]

## Requirements

- OS: Windows (required to interface Aspen Plus via COM/pywin32).[1]
- Aspen Plus installed and licensed.[1]
- Conda (Miniconda/Anaconda) for environment management.[1]
- Access to an LCI database (e.g., ecoinvent) is recommended for mapping and LCIA; import happens inside the app.[1]

## Quick start (Conda, Windows)

1) Create and activate the Conda environment
- conda create -n aspen_bw python=3.11 -y
- conda activate aspen_bw
[1]

2) Install dependencies
- pip install streamlit pandas numpy plotly matplotlib
- pip install bw2data bw2calc bw2io bw2analyzer
- pip install pywin32 pythoncom
[2][3][1]

Notes:
- pywin32/pythoncom are required for COM integration with Aspen Plus on Windows.[4][1]
- Brightway will create local data directories on first use; don’t commit these to version control.[1]

3) Optional tools
- Testing/dev tools (e.g., pytest) can be added as needed.[1]
- The app can import ecoinvent via the UI with user credentials and a chosen system model.[1]

## Run the app

From the project root (where app_gui.py lives):
- streamlit run app_gui.py
[5][2]

App workflow:
- Upload an Aspen Plus .bkp file.[1]
- Extract flows and assign categories (Reference Flow, Technosphere, Biosphere, Avoided Product, Waste).[1]
- Review normalized LCI and optionally create/activate a Brightway project.[1]
- Optionally import ecoinvent and map flows to Brightway activities.[1]
- Build the foreground inventory and run LCIA for selected methods/categories.[1]

## Project structure

- app_gui.py: Streamlit UI and orchestration (extraction, normalization, mapping, build inventory, LCIA).[1]
- core/extraction.py: Aspen Plus COM integration and flow parsing.[1]
- core/normalization.py: Flow normalization against the Reference Flow and group/unit assignment.[1]
- core/mapping.py: Search/select Brightway activities per flow; density support for kg→m³ conversion.[6]
- core/inventory_builder.py: Foreground process creation and edges (production, technosphere, biosphere, substitution, waste) with corrected sign conventions.[7]
- core/lcia_selection.py: UI for LCIA method/category selection.[1]
- core/lcia_runner.py: LCIA execution for the selected categories on 1 functional unit of the foreground process.[1]

## Brightway data notes

- Brightway projects/databases are created/managed by the app; do not commit Brightway data directories.[1]
- Ecoinvent import requires valid credentials and choosing a system model (cutoff, consequential, APOS).[1]

## Recommended .gitignore entries

- __pycache__/
- *.py[cod]
- .venv/ venv/ env/ .env/ ENV/
- .pytest_cache/
- .streamlit/secrets.toml
- dist/ build/ *.egg-info/
- Any local Brightway data directories (user-level data, not for source control)
[1]

## Start command

- streamlit run app_gui.py

[18](https://anaconda.org/anaconda/pywin32)
[19](https://pypi.org/project/pywin32/305/)
[20](https://www.youtube.com/watch?v=8jLkgnDf15w)
