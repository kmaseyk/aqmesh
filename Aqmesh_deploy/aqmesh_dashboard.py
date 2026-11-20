import pandas as pd
import plotly.express as px
import streamlit as st
from pathlib import Path

# ---- Settings ---------------------------------------------------------------
DATA_DIR = Path("data")                 # folder with gas_master.csv and pm_master.csv
CUTOFF = pd.Timestamp("2026-11-13 14:00:00")   # gas sensors stabilised from this time
CACHE_SECONDS = 600                            # re-read the CSV files at most every 10 minutes

st.set_page_config(page_title="AQMesh air quality", layout="wide")


# ---- Data loading -----------------------------------------------------------
@st.cache_data(ttl=CACHE_SECONDS)
def load_gas():
    cols = {"reading_datestamp": "date_time", "co_prescaled": "co", "no_prescaled": "no",
            "no2_prescaled": "no2", "eo_prescaled": "voc", "uart_prescaled": "co2"}
    df = pd.read_csv(DATA_DIR / "gas_master.csv", usecols=list(cols),
                     parse_dates=["reading_datestamp"]).rename(columns=cols)
    df = df[df["date_time"] >= CUTOFF].sort_values("date_time")
    gases = [c for c in df.columns if c != "date_time"]
    df[gases] = df[gases].where(df[gases] > -800)      # AQMesh flag codes (-999 etc.) -> missing
    df["nox"] = df["no"] + df["no2"]
    return df


@st.cache_data(ttl=CACHE_SECONDS)
def load_pm():
    cols = {"reading_datestamp": "date_time", "pm1_prescale": "pm1", "pm2_5_prescale": "pm2_5",
            "pm4_prescale": "pm4", "pm10_prescale": "pm10"}
    df = pd.read_csv(DATA_DIR / "pm_master.csv", usecols=list(cols),
                     parse_dates=["reading_datestamp"]).rename(columns=cols)
    df = df[df["date_time"] >= CUTOFF].sort_values("date_time")
    pms = [c for c in df.columns if c != "date_time"]
    df[pms] = df[pms].where(df[pms] > -800)
    return df


# ---- Plot helper ------------------------------------------------------------
def line_plot(df, series, ylabel, colors=None):
    """series maps column name -> legend label; colors maps legend label -> colour."""
    plot_df = df[["date_time", *series]].rename(columns=series)
    fig = px.line(plot_df, x="date_time", y=list(series.values()), color_discrete_map=colors)
    fig.update_layout(
        xaxis_title="Date and time",
        yaxis_title=ylabel,
        legend_title_text="",
        legend=dict(orientation="h", y=-0.25),
        showlegend=len(series) > 1,
        margin=dict(t=10),
    )
    st.plotly_chart(fig)


# ---- Page -------------------------------------------------------------------
st.title("AQMesh air quality data")
st.write(
    "Readings from an AQMesh air quality pod on the OpenLiving Lab riparian mast. "
    "Data is logged every 15 minutes and updated hourly. "
    "Gas concentrations are in parts per billion (ppb), except CO2, which is in parts per "
    "million (ppm). Particulate matter (PM) is in µg/m³. "
)

try:
    gas, pm = load_gas(), load_pm()
except FileNotFoundError as err:
    st.error(f"Data file not found: {err.filename}. Check DATA_DIR at the top of the script.")
    st.stop()

st.caption(f"Latest gas reading: {gas['date_time'].max():%d %b %Y, %H:%M}")

st.subheader("Carbon dioxide (CO2)")
line_plot(gas, {"co2": "CO2"}, "CO2 (ppm)")

st.subheader("Carbon monoxide (CO)")
line_plot(gas, {"co": "CO"}, "CO (ppb)")

st.subheader("Volatile organic compounds (VOC, ethylene oxide sensor)")
line_plot(gas, {"voc": "VOC"}, "VOC (ppb)")

st.subheader("Nitrogen oxides (NOx)")
line_plot(gas, {"nox": "NOx", "no2": "NO2", "no": "NO"}, "Concentration (ppb)",
          colors={"NOx": "black", "NO2": "steelblue", "NO": "darkgrey"})

st.subheader("Particulate matter (PM)")
line_plot(pm, {"pm1": "PM1", "pm2_5": "PM2.5", "pm4": "PM4", "pm10": "PM10"}, "PM (µg/m³)")
