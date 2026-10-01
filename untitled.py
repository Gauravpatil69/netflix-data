import csv
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="Netflix | Viewing Insights",
    page_icon="N",
    layout="wide",
    initial_sidebar_state="expanded",
)

NETFLIX_RED = "#E50914"
PANEL = "#141414"
WHITE = "#F5F5F1"
MUTED = "#A6A6A6"

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');
    .stApp {
        background: radial-gradient(ellipse at 50% -15%, rgba(229,9,20,.17), transparent 42%), #080808;
        color: #F5F5F1; font-family: 'DM Sans', sans-serif;
    }
    [data-testid="stSidebar"] { background: #101010; border-right: 1px solid #292929; }
    [data-testid="stSidebar"] * { color: #F5F5F1; }
    .block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1480px; }
    .brand { color: #E50914; font-weight: 800; letter-spacing: .18em; font-size: .75rem; }
    .hero {
        position: relative; overflow: hidden; padding: 2rem 2.2rem 1.8rem;
        border: 1px solid #343030; border-radius: 18px;
        background: linear-gradient(110deg, rgba(32,20,20,.98), rgba(16,16,16,.96) 58%, rgba(48,8,12,.92));
        box-shadow: 0 18px 55px rgba(0,0,0,.3);
    }
    .hero:after { content: ''; position: absolute; right: -55px; top: -130px; width: 330px; height: 330px; border: 1px solid rgba(229,9,20,.22); border-radius: 50%; box-shadow: 0 0 0 34px rgba(229,9,20,.035), 0 0 0 70px rgba(229,9,20,.025); }
    .hero-title { color: #F5F5F1; font-size: clamp(2.15rem, 4vw, 3.5rem); font-weight: 800; letter-spacing: -.055em; line-height: 1.05; margin: .45rem 0 .55rem; }
    .hero-copy { color: #B5B1B1; font-size: .98rem; margin: 0; max-width: 680px; }
    .section-heading { color: #F5F5F1; font-size: 1.18rem; font-weight: 700; letter-spacing: -.02em; margin: 1.75rem 0 .15rem; }
    .section-caption { color: #898989; font-size: .83rem; margin: 0 0 .85rem; }
    .kpi-card { min-height: 118px; padding: 1.05rem 1.2rem; background: linear-gradient(145deg,#181818,#101010); border: 1px solid #2c2c2c; border-radius: 14px; position: relative; overflow: hidden; }
    .kpi-card:before { content: ''; position: absolute; top: 0; left: 0; height: 2px; width: 44px; background: #E50914; }
    .kpi-label { color: #A6A6A6; text-transform: uppercase; letter-spacing: .1em; font-size: .68rem; font-weight: 700; }
    .kpi-value { color: #F5F5F1; font-size: 1.8rem; font-weight: 800; letter-spacing: -.045em; margin-top: .5rem; line-height: 1.1; }
    div[data-testid="stPlotlyChart"] { background: #111; border: 1px solid #292929; border-radius: 15px; padding: .45rem; box-shadow: 0 10px 32px rgba(0,0,0,.18); }
    .stMultiSelect [data-baseweb="tag"] { background: #E50914; }
    .stDateInput input { background: #191919; }
    div[data-testid="stCaptionContainer"] { color: #898989; }
    hr { border-color: #292929; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_data():
    """Load the project's CSV, whose rows are wrapped as one quoted field."""
    csv_path = Path(__file__).with_name("netflix.csv")
    raw = pd.read_csv(csv_path, quoting=csv.QUOTE_NONE, dtype=str)
    raw.columns = [str(column).strip().strip('"') for column in raw.columns]
    for column in raw.columns:
        raw[column] = raw[column].astype(str).str.strip().str.strip('"')

    for column in ["Rating", "Watch_Count", "Watch_Time_Minutes", "Monthly_Revenue"]:
        if column in raw.columns:
            raw[column] = pd.to_numeric(raw[column], errors="coerce")
    if "Watch_Date" in raw.columns:
        raw["Watch_Date"] = pd.to_datetime(raw["Watch_Date"], errors="coerce")
    return raw


try:
    netflix = load_data()
except (FileNotFoundError, pd.errors.ParserError) as error:
    st.error(f"Could not load netflix.csv: {error}")
    st.stop()

with st.sidebar:
    st.markdown(f"<div class='brand'>NETFLIX INSIGHTS</div>", unsafe_allow_html=True)
    st.markdown("## Refine the view")
    st.caption("Choose the audience and viewing period for these charts.")

    filtered = netflix.copy()
    for label, column in [("Region", "Region"), ("Subscription plan", "Subscription_Plan"), ("Category", "Category")]:
        if column in netflix.columns:
            options = sorted(netflix[column].dropna().unique().tolist())
            selected = st.multiselect(label, options, default=options, key=f"filter_{column}")
            if selected:
                filtered = filtered[filtered[column].isin(selected)]
            else:
                filtered = filtered.iloc[0:0]

    if "Watch_Date" in netflix.columns and netflix["Watch_Date"].notna().any():
        first_date = netflix["Watch_Date"].min().date()
        last_date = netflix["Watch_Date"].max().date()
        date_range = st.date_input("Viewing dates", value=(first_date, last_date), min_value=first_date, max_value=last_date)
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            filtered = filtered[
                filtered["Watch_Date"].dt.date.between(start_date, end_date)
            ]

st.markdown(
    "<div class='hero'><div class='brand'>STREAMING, AT A GLANCE</div>"
    "<div class='hero-title'>Netflix Viewing Insights</div>"
    "<p class='hero-copy'>Explore revenue trends, the content your audience watches, and how they choose to stream and pay.</p></div>",
    unsafe_allow_html=True,
)

if filtered.empty:
    st.info("No records match these filters. Update your selections to see the charts.")
    st.stop()

total_revenue = filtered["Monthly_Revenue"].sum() if "Monthly_Revenue" in filtered.columns else 0
average_rating = filtered["Rating"].mean() if "Rating" in filtered.columns else float("nan")
watch_hours = filtered["Watch_Time_Minutes"].sum() / 60 if "Watch_Time_Minutes" in filtered.columns else 0

metric_columns = st.columns(4, gap="medium")
metrics = [
    ("CUSTOMER RECORDS", f"{len(filtered):,}"),
    ("TOTAL REVENUE", f"INR {total_revenue:,.0f}"),
    ("AVERAGE RATING", f"{average_rating:.1f} / 5" if pd.notna(average_rating) else "—"),
    ("WATCH TIME", f"{watch_hours:,.0f} hrs"),
]
for column, (label, value) in zip(metric_columns, metrics):
    with column:
        st.markdown(
            f"<div class='kpi-card'><div class='kpi-label'>{label}</div>"
            f"<div class='kpi-value'>{value}</div></div>",
            unsafe_allow_html=True,
        )

st.markdown("<div class='section-heading'>Revenue performance</div><div class='section-caption'>Track earnings over time and see which categories contribute most.</div>", unsafe_allow_html=True)
left, right = st.columns([1.35, 1], gap="large")

if "Watch_Date" in filtered.columns and "Monthly_Revenue" in filtered.columns:
    with left:
        trend = filtered.dropna(subset=["Watch_Date"]).copy()
        trend["Month"] = trend["Watch_Date"].dt.to_period("M").dt.to_timestamp()
        trend = trend.groupby("Month", as_index=False)["Monthly_Revenue"].sum()
        fig = px.line(
            trend,
            x="Month",
            y="Monthly_Revenue",
            title="Revenue over time",
            markers=True,
            color_discrete_sequence=[NETFLIX_RED],
        )
        fig.update_traces(line=dict(width=3), marker=dict(size=7), hovertemplate="%{x|%b %Y}<br>INR %{y:,.0f}<extra></extra>")
        fig.update_layout(
            template="plotly_dark", height=390, margin=dict(l=20, r=20, t=65, b=20),
            paper_bgcolor=PANEL, plot_bgcolor=PANEL, font=dict(color=WHITE, family="DM Sans"),
            title=dict(font=dict(size=17)), xaxis_title=None, yaxis_title="Revenue (INR)",
            showlegend=False,
        )
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=True, gridcolor="#303030", tickprefix="INR ")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

if "Category" in filtered.columns and "Monthly_Revenue" in filtered.columns:
    with right:
        category = filtered.groupby("Category", as_index=False)["Monthly_Revenue"].sum().sort_values("Monthly_Revenue", ascending=False)
        fig = px.pie(
            category, names="Category", values="Monthly_Revenue", hole=.68,
            title="Revenue by category",
            color_discrete_sequence=[NETFLIX_RED, "#F5F5F1", "#A10D15", "#777777", "#D94A50", "#444444"],
        )
        fig.update_traces(textposition="inside", textinfo="percent", hole=.68, marker=dict(line=dict(color=PANEL, width=3)))
        total_revenue = category["Monthly_Revenue"].sum()
        fig.add_annotation(text=f"INR {total_revenue:,.0f}", x=.5, y=.5, showarrow=False, font=dict(size=17, color=WHITE))
        fig.update_layout(
            template="plotly_dark", height=390, margin=dict(l=20, r=20, t=65, b=20),
            paper_bgcolor=PANEL, plot_bgcolor=PANEL, font=dict(color=WHITE, family="DM Sans"),
            title=dict(font=dict(size=17)), legend=dict(orientation="h", y=-.1, x=.5, xanchor="center"),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.markdown("<div class='section-heading'>How viewers watch and pay</div><div class='section-caption'>A breakdown of the devices and payment methods in the selected audience.</div>", unsafe_allow_html=True)
device_col, payment_col = st.columns(2, gap="large")
pie_colors = [NETFLIX_RED, "#F5F5F1", "#777777", "#A10D15", "#D94A50", "#444444"]

for container, column, title in [
    (device_col, "Device", "Device usage"),
    (payment_col, "Payment_Method", "Payment methods"),
]:
    if column in filtered.columns:
        with container:
            counts = filtered[column].value_counts(dropna=True).rename_axis(column).reset_index(name="Views")
            fig = px.pie(counts, names=column, values="Views", hole=.58, title=title, color_discrete_sequence=pie_colors)
            fig.update_traces(textposition="inside", textinfo="percent", marker=dict(line=dict(color=PANEL, width=3)))
            fig.update_layout(
                template="plotly_dark", height=350, margin=dict(l=20, r=20, t=65, b=20),
                paper_bgcolor=PANEL, plot_bgcolor=PANEL, font=dict(color=WHITE, family="DM Sans"),
                title=dict(font=dict(size=17)), legend=dict(orientation="h", y=-.08, x=.5, xanchor="center"),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

