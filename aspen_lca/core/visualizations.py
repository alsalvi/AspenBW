# core/visualizations.py

import plotly.graph_objects as go
import pandas as pd


def render_material_sankey(df: pd.DataFrame) -> go.Figure | None:
    """
    Build a Sankey diagram for material flows with legend and high-contrast labels.

    Expects df to include columns: Flow, Type, Amount, Amount_float, Unit, Category, Direction.
    Returns a Plotly Figure or None if there are no material flows.
    """
    # Filter only material flows
    material_flows = df[df['Category'] == 'material'].copy()
    if material_flows.empty:
        return None

    # Colors by flow Type
    category_colors = {
        'Biosphere': 'rgba(0,153,0,0.45)',
        'Technosphere': 'rgba(0,90,255,0.45)',
        'Reference Flow': 'rgba(255,180,70,0.65)',
        'Avoided Product': 'rgba(255,245,50,0.55)',
        'Waste': 'rgba(130,130,130,0.45)',
    }

    # Nodes: process + one node per input and output flow
    labels: list[str] = ["process"]

    input_flows = material_flows[material_flows['Direction'] == 'input']
    output_flows = material_flows[material_flows['Direction'] == 'output']

    # Node labels with amounts and units
    def in_label(r):
        return f"{r['Flow']}\n{r['Amount']}{r['Unit']}"

    def out_label(r):
        return f"{r['Flow']}\n{abs(r['Amount_float']):.4f}{r['Unit']}"

    for _, row in input_flows.iterrows():
        labels.append(in_label(row))
    for _, row in output_flows.iterrows():
        labels.append(out_label(row))

    node_indices = {label: i for i, label in enumerate(labels)}

    # Build links
    sources: list[int] = []
    targets: list[int] = []
    values: list[float] = []
    colors: list[str] = []

    # Inputs -> process
    for _, row in input_flows.iterrows():
        flow_label = in_label(row)
        sources.append(node_indices[flow_label])
        targets.append(node_indices['process'])
        values.append(float(row['Amount_float']))
        colors.append(category_colors.get(str(row['Type']), 'rgba(50,50,50,0.25)'))

    # process -> Outputs
    for _, row in output_flows.iterrows():
        flow_label = out_label(row)
        sources.append(node_indices['process'])
        targets.append(node_indices[flow_label])
        values.append(abs(float(row['Amount_float'])))
        colors.append(category_colors.get(str(row['Type']), 'rgba(50,50,50,0.25)'))

    # Sankey with white nodes (for contrast) and black text
    sankey = go.Sankey(
        node=dict(
            pad=20,
            thickness=28,
            line=dict(color="rgba(0,0,0,0.15)", width=1),
            label=labels,
            color="#ffffff",
            customdata=labels,
            hovertemplate="%{customdata}<extra></extra>",
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=colors,
            hovertemplate="<b>%{value:.4f}</b> (normalized)<extra></extra>",
        ),
        textfont=dict(color="#000000", size=16),  # enforce plain black font
    )

    fig = go.Figure(data=[sankey])

    # Global plain black font and white background, no title
    fig.update_layout(
        font=dict(family="Arial, sans-serif", color="#000000", size=16),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        margin=dict(l=50, r=50, t=60, b=40),
    )

    # Legend via dummy Scatter traces (Sankey lacks native legend)
    present_types = [t for t in material_flows['Type'].unique().tolist() if t in category_colors]
    legend_order = ['Biosphere', 'Technosphere', 'Reference Flow', 'Avoided Product', 'Waste']
    present_types_sorted = [t for t in legend_order if t in present_types]

    for t in present_types_sorted:
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker=dict(size=12, color=category_colors[t]),
            legendgroup=str(t),
            showlegend=True,
            name=str(t),
            hoverinfo='skip'
        ))

    # Hide axes introduced by the dummy scatter traces
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)

    # Legend on the right
    fig.update_layout(
        legend=dict(
            orientation='v',
            yanchor='top', y=0.98,
            xanchor='left', x=1.02,
            bordercolor='rgba(0,0,0,0.1)', borderwidth=1
        )
    )

    return fig
