import plotly.express as px

def bar_chart(df, x, y, title):
    fig = px.bar(df, x=x, y=y, text=y, title=title)
    fig.update_layout(showlegend=False)
    return fig

def histogram(df, column, bins, title):
    return px.histogram(df, x=column, nbins=bins, title=title)

def cf_distribution(df, cf_cols):
    df2 = df[cf_cols].gt(0).sum(axis=1).value_counts().reset_index()
    df2.columns = ["Num_CFs", "Count"]
    return px.bar(df2, x="Num_CFs", y="Count", text="Count", title="CF Distribution")
