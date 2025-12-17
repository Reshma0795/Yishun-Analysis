# logic/plot_style.py
from __future__ import annotations
import plotly.graph_objects as go

def apply_modern_bar_style(
    fig: go.Figure,
    *,
    title: str | None = None,
    yaxis_title: str = "Percent (%)",
    legend_title: str | None = None,
    legend_orientation: str = "h",   # "h" for top horizontal
    legend_y: float = 1.08,
    legend_x: float = 0.0,
    legend_xanchor: str = "left",
    legend_yanchor: str = "bottom",
    show_grid_y: bool = True,
    show_grid_x: bool = False,
):
    # Clean white background (remove blue)
    fig.update_layout(
        title=title,
        title_x=0.02,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=40, r=25, t=60, b=45),
        bargap=0.32,
        bargroupgap=0.12,
        legend=dict(
            title=legend_title,
            orientation=legend_orientation,
            y=legend_y,
            x=legend_x,
            xanchor=legend_xanchor,
            yanchor=legend_yanchor,
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="rgba(0,0,0,0.08)",
            borderwidth=1,
            font=dict(size=11),
        ),
        font=dict(size=12),
    )

    # Axes
    fig.update_xaxes(showgrid=show_grid_x, zeroline=False, tickfont=dict(size=11))
    fig.update_yaxes(
        title=yaxis_title,
        showgrid=show_grid_y,
        gridcolor="rgba(0,0,0,0.08)",
        zeroline=False,
        ticksuffix="%",
        tickfont=dict(size=11),
    )

    return fig
