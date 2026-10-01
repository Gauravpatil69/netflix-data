import csv
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="Netflix | Viewing Insights",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

NETFLIX_RED = "#E50914"
INK = "#080808"
PANEL = "#151515"
WHITE = "#F5F5F1"
MUTED = "#A6A6A6"

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');
    .stApp { background: #080808; color: #F5F5F1; font-family: 'DM Sans', sans-serif; }
    [data-testid="stSidebar"] { background: #111; border-right: 1px solid #292929; }
    [data-testid="stSidebar"] * { color: #F5F5F1; }
    .block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1440px; }
    .brand { color: #E50914; font-weight: 800; letter-spacing: .14em; font-size: .82rem; }
    .hero-title { color: #F5F5F1; font-size: clamp(2.2rem, 4vw, 3.5rem); font-weight: 800; letter-spacing: -.055em; line-height: 1.05; margin: .45rem 0 .5rem; }
    .hero-copy { color: #A6A6A6; font-size: 1rem; margin-bottom: 1.5rem; }
    .section-label { color: #A6A6A6; text-transform: uppercase; letter-spacing: .12em; font-size: .72rem; font-weight: 700; margin: 1.4rem 0 .7rem; }
    div[data-testid="stPlotlyChart"] { background: #111; border: 1px solid #292929; border-radius: 12px; padding: .5rem; }
    .stMultiSelect [data-baseweb="tag"] { background: #E50914; }
    .stDateInput input { background: #191919; }
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

st.markdown("<div class='brand'>YOUR NEXT BINGE, IN NUMBERS</div>", unsafe_allow_html=True)
st.markdown("<div class='hero-title'>Netflix Viewing Insights</div>", unsafe_allow_html=True)
st.markdown("<div class='hero-copy'>A focused look at revenue, content categories, devices, and payment preferences.</div>", unsafe_allow_html=True)

if filtered.empty:
    st.info("No records match these filters. Update your selections to see the charts.")
    st.stop()

st.markdown("<div class='section-label'>Revenue performance</div>", unsafe_allow_html=True)
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
        fig.update_traces(line=dict(width=3), marker=dict(size=7), hovertemplate="%{x|%b %Y}<br>₹%{y:,.0f}<extra></extra>")
        fig.update_layout(
            template="plotly_dark", height=390, margin=dict(l=20, r=20, t=65, b=20),
            paper_bgcolor=PANEL, plot_bgcolor=PANEL, font=dict(color=WHITE, family="DM Sans"),
            title=dict(font=dict(size=17)), xaxis_title=None, yaxis_title="Revenue (₹)",
            showlegend=False,
        )
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=True, gridcolor="#303030", tickprefix="₹")
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
        fig.add_annotation(text=f"₹{total_revenue:,.0f}", x=.5, y=.5, showarrow=False, font=dict(size=19, color=WHITE))
        fig.update_layout(
            template="plotly_dark", height=390, margin=dict(l=20, r=20, t=65, b=20),
            paper_bgcolor=PANEL, plot_bgcolor=PANEL, font=dict(color=WHITE, family="DM Sans"),
            title=dict(font=dict(size=17)), legend=dict(orientation="h", y=-.1, x=.5, xanchor="center"),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.markdown("<div class='section-label'>How viewers watch and pay</div>", unsafe_allow_html=True)
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

