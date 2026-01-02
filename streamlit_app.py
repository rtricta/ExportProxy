import streamlit as st
import pandas as pd
import requests
from pyjstat import pyjstat
from datetime import datetime

# --- CONFIGURATION & MAPPING ---
# This dictionary maps your companies to their specific "Smoking Gun" HS codes and manufacturing regions.
COMPANY_MAP = {
    "Borregaard (Norway)": {
        "source": "SSB",
        "codes": ["38040000"], # Lignosulfonates (The purest signal)
        "region": "30",        # Viken/Østfold (Sarpsborg is here)
        "desc": "Lignosulfonates (Lignin) from Sarpsborg"
    },
    "Norbit (Norway)": {
        "source": "SSB",
        "codes": ["90158000"], # Hydrographic/Surveying instruments
        "region": "50",        # Trøndelag (Trondheim/Røros)
        "desc": "Sonar & Subsea mapping systems from Trøndelag"
    },
    "B&C Speakers (Italy)": {
        "source": "EUROSTAT",
        "codes": ["85182900"], # Loudspeakers (not in enclosure)
        "region": "IT",        # Italy (National level for Eurostat simple query)
        "desc": "Raw Speaker Drivers (Florence Hub)"
    },
    "Powersoft (Italy)": {
        "source": "EUROSTAT",
        "codes": ["85184000"], # Audio Amplifiers
        "region": "IT",        # Italy
        "desc": "Rack Amplifiers (Florence/Bologna Hub)"
    }
}

# --- SSB (NORWAY) API FUNCTION ---
def fetch_ssb_data(hs_codes):
    """
    Queries SSB Table 08799: External trade in goods.
    """
    url = "https://data.ssb.no/api/v0/en/table/08799"
    
    # Payload designed for Table 08799
    # Note: 'ImpEks' -> '2' is Exports.
    payload = {
        "query": [
            {
                "code": "Varekoder",
                "selection": {
                    "filter": "item",
                    "values": hs_codes
                }
            },
            {
                "code": "ImpEks",
                "selection": {
                    "filter": "item",
                    "values": ["2"] # 2 = Exports
                }
            },
            {
                "code": "Tid",
                "selection": {
                    "filter": "top",
                    "values": ["60"] # Last 60 months (5 years)
                }
            }
        ],
        "response": {"format": "json-stat2"}
    }
    
    try:
        res = requests.post(url, json=payload)
        res.raise_for_status()
        dataset = pyjstat.Dataset.read(res.text)
        df = dataset.write('dataframe')
        
        # Cleanup: specific to SSB response format
        if not df.empty:
            df['date'] = pd.to_datetime(df['month'], format='%YM%m')
            df = df.sort_values('date')
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Error fetching SSB data: {e}")
        return pd.DataFrame()

# --- APP LAYOUT ---
st.title("🚢 Trade Volume Detective")
st.markdown("Track export volumes for **Borregaard, Norbit, B&C, and Powersoft** using official government trade data.")

# Sidebar selection
target = st.sidebar.selectbox("Select Company Target", list(COMPANY_MAP.keys()))
info = COMPANY_MAP[target]

st.header(f"Target: {target}")
st.info(f"**Tracking Product:** {info['desc']}\n\n**HS Code:** {', '.join(info['codes'])}")

# --- EXECUTION LOGIC ---
if st.button("Run Export Analysis"):
    with st.spinner(f"Querying {info['source']} Database..."):
        
        if info['source'] == "SSB":
            df = fetch_ssb_data(info['codes'])
            
            if not df.empty:
                # Filter for Value (usually 'value' col contains revenue proxy)
                # SSB returns Value in NOK usually, or Quantity.
                metric_col = "value" if "value" in df.columns else df.columns[-1]
                
                # Plotting
                st.subheader("Monthly Export Value (NOK)")
                st.line_chart(df.set_index("date")[metric_col])
                
                st.write("### Raw Data Sample")
                st.dataframe(df.tail(5))
                
                # Analysis Tip
                st.success(f"💡 **Analyst Note:** Look for seasonality. For {target}, does Q4 usually spike? Compare this chart to their reported Revenue.")
            else:
                st.warning("No data returned. The HS code might have changed or volume is too low to report publicly this month.")

        elif info['source'] == "EUROSTAT":
            st.warning("⚠️ **Eurostat API Notice:**")
            st.markdown("""
            Direct access to Eurostat via simple API calls is complex due to bulk download limits. 
            For **B&C** and **Powersoft**, the best free method is:
            1. Go to [Eurostat Comext Browser](https://ec.europa.eu/eurostat/databrowser/view/DS-016890/default/table?lang=en).
            2. Filter Reporter: **Italy**.
            3. Filter Product: **85182900** (B&C) or **85184000** (Powersoft).
            4. Download the CSV and drop it into your 'Tancook' app.
            
            *The Python script for Eurostat requires the 'eurostat' library and 50+ lines of cleanup code, which I can provide if you want to go deeper.*
            """)

st.sidebar.markdown("---")
st.sidebar.caption("Data Sources: SSB (Norway), Eurostat (EU).")
