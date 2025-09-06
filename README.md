# Aspen-Brightway LCA Interface (up to LCIA)

Streamlit app to:
- Load an Aspen Plus .bkp file and extract process flows.
- Normalize flows against a selected Reference Flow and display the LCI.
- Manage Brightway projects/databases (including optional ecoinvent import with credentials).
- Map flows to Brightway activities and run LCIA on selected categories.

Note: the “Process contributions” section is excluded in this version.
## Requirements

- OS: Windows (required to interface Aspen Plus via COM/pywin32).
- Aspen Plus installed and licensed.
- Conda (Miniconda/Anaconda) for environment management.
- Access to an LCI database (e.g., ecoinvent) is recommended for mapping and LCIA; import happens inside the app.

## Quick start (Conda, Windows)

1) Create and activate the Conda environment
- conda create -n aspen_bw python=3.11 -y
- conda activate aspen_bw

2) Install dependencies
- pip install streamlit pandas numpy plotly matplotlib
- pip install bw2data bw2calc bw2io bw2analyzer
- pip install pywin32 pythoncom

Notes:
- pywin32/pythoncom are required for COM integration with Aspen Plus on Windows.
- Brightway will create local data directories on first use; don’t commit these to version control.

3) Optional tools
- Testing/dev tools (e.g., pytest) can be added as needed.
- The app can import ecoinvent via the UI with user credentials and a chosen system model.

## Run the app

From the project root (where app_gui.py lives):
- streamlit run app_gui.py

App workflow:
- Upload an Aspen Plus .bkp file.
- Extract flows and assign categories (Reference Flow, Technosphere, Biosphere, Avoided Product, Waste).
- Review normalized LCI and optionally create/activate a Brightway project.
- Optionally import ecoinvent and map flows to Brightway activities.
- Build the foreground inventory and run LCIA for selected methods/categories.
  
## Project structure

- app_gui.py: Streamlit UI and orchestration (extraction, normalization, mapping, build inventory, LCIA).
- core/extraction.py: Aspen Plus COM integration and flow parsing.
- core/normalization.py: Flow normalization against the Reference Flow and group/unit assignment.
- core/mapping.py: Search/select Brightway activities per flow; density support for kg→m³ conversion.
- core/inventory_builder.py: Foreground process creation and edges (production, technosphere, biosphere, substitution, waste) with corrected sign conventions.
- core/lcia_selection.py: UI for LCIA method/category selection.
- core/lcia_runner.py: LCIA execution for the selected categories on 1 functional unit of the foreground process.

## Brightway data notes

- Brightway projects/databases are created/managed by the app; do not commit Brightway data directories.
- Ecoinvent import requires valid credentials and choosing a system model (cutoff, consequential, APOS).
  
## Recommended .gitignore entries

- __pycache__/
- *.py[cod]
- .venv/ venv/ env/ .env/ ENV/
- .pytest_cache/
- .streamlit/secrets.toml
- dist/ build/ *.egg-info/
- Any local Brightway data directories (user-level data, not for source control)


## Start command

- streamlit run app_gui.py

