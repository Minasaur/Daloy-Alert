import streamlit as st
import plotly.graph_objects as go
import csv, os, pandas as pd
from datetime import datetime
import requests
from streamlit_autorefresh import st_autorefresh

# ---------------- CONFIG ----------------
os.makedirs("logs", exist_ok=True)
st.set_page_config(page_title="💧 DALOY Monitoring App", layout="wide")

# ---------------- STYLE ----------------
st.markdown("""
<style>
body, .main { background-color: #a7d8f0 !important; color: black !important; }
h1, h2, h3, h4, h5, h6, p, div, span { color: black !important; }
.block-container { background-color: #a7d8f0 !important; padding: 25px; max-width: 95% !important; }
.reading-box { border: 3px solid #0d47a1; border-radius: 12px; padding: 20px; text-align: center; color: black !important;}
.reading-grid { display: flex; justify-content: space-around; margin-top: 15px; flex-wrap: wrap; gap: 10px; }
.reading-item { flex: 1; min-width: 180px; background-color: #e3f2fd; border: 2px solid #0d47a1;
                border-radius: 8px; padding: 15px; font-weight: bold; text-align: center; color: black !important; }
.remark-box { background-color: #e3f2fd; border: 2px solid #0d47a1;
              border-radius: 10px; padding: 15px; margin-top: 15px;
              text-align: center; font-size: 17px; color: black !important; }
</style>
""", unsafe_allow_html=True)

# ---------------- BACKEND CONFIG ----------------
def fetch_data():
    try:
        BASE_URL = "https://daloy-alert-default-rtdb.asia-southeast1.firebasedatabase.app/canal_readings"
        esp1 = requests.get(f"{BASE_URL}/ESP1.json", timeout=5).json()
        esp2 = requests.get(f"{BASE_URL}/ESP2.json", timeout=5).json()

        if not esp1 or not esp2:
            return None, None, None

        upstream = float(esp1.get("upstream", 0))
        downstream = float(esp2.get("downstream", 0))
        difference = abs(upstream - downstream)

        return upstream, downstream, difference

    except Exception as e:
        st.warning(f"Error fetching data from Firebase: {e}")
        return None, None, None

# ---------------- SESSION INITIALIZATION ----------------
if "timestamps" not in st.session_state:
    st.session_state.timestamps = []
    st.session_state.upstream_data = []
    st.session_state.downstream_data = []
    st.session_state.difference_data = []
    st.session_state.status_data = []

# ---------------- HELPER FUNCTIONS ----------------
def get_status(difference):
    if difference >= 2.5:
        return "🚨 FULL BLOCKAGE", "#ff4d4d"
    elif difference >= 1.0:
        return "⚠️ PARTIAL BLOCKAGE", "#fff176"
    else:
        return "✅ NORMAL FLOW", "#81c784"

def get_remark(status):
    if status == "✅ NORMAL FLOW":
        return "💧 Flow is stable — no obstruction detected."
    elif status == "⚠️ PARTIAL BLOCKAGE":
        return "⚠️ Partial blockage detected. Monitor canal condition."
    else:
        return "🌊 Full blockage detected! Immediate maintenance required."

def log_to_csv(timestamp, upstream, downstream, difference, status):
    if status != "🚨 FULL BLOCKAGE":
        return
    filename = f"logs/daloy_log_{datetime.now().strftime('%Y-%m-%d')}.csv"
    file_exists = os.path.exists(filename)
    try:
        with open(filename, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Timestamp","Status","Upstream","Downstream","Difference"])
            writer.writerow([timestamp.strftime("%Y-%m-%d %H:%M:%S"), status, upstream, downstream, difference])
    except PermissionError:
        st.warning("Unable to write to CSV. Close any open file.")

# ---------------- DASHBOARD VIEW ----------------
def show_dashboard():
    # Static page content
    st.title("💧 DALOY Monitoring App")
    st.subheader("Real-Time Kanal Flood Monitoring Dashboard")

    # Placeholders for dynamic content
    reading_placeholder = st.empty()
    remark_placeholder = st.empty()
    chart_placeholder = st.empty()

    # Autorefresh every 2 seconds
    st_autorefresh(interval=2000, key="datarefresh")

    # Fetch latest sensor data
    upstream, downstream, difference = fetch_data()
    timestamp = datetime.now()

    if upstream is not None and downstream is not None:
        # Determine status and remark
        status_display, color = get_status(difference)
        remark = get_remark(status_display)

        # Update session state for charts
        st.session_state.timestamps.append(timestamp)
        st.session_state.upstream_data.append(upstream)
        st.session_state.downstream_data.append(downstream)
        st.session_state.difference_data.append(difference)
        st.session_state.status_data.append(status_display)

        # Log full blockages
        log_to_csv(timestamp, upstream, downstream, difference, status_display)

        # Update reading box
        reading_placeholder.markdown(f"""
        <div class="reading-box" style="background-color:{color};">
            <h2>{status_display}</h2>
            <div class="reading-grid">
                <div class="reading-item">🌊 Upstream<br>{upstream:.2f} cm</div>
                <div class="reading-item">💧 Downstream<br>{downstream:.2f} cm</div>
                <div class="reading-item">🔁 Difference<br>{difference:.2f} cm</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Update remark box
        remark_placeholder.markdown(f"<div class='remark-box'>{remark}</div>", unsafe_allow_html=True)

        # Update chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=st.session_state.timestamps, y=st.session_state.upstream_data,
                                 mode="lines+markers", name="Upstream"))
        fig.add_trace(go.Scatter(x=st.session_state.timestamps, y=st.session_state.downstream_data,
                                 mode="lines+markers", name="Downstream"))
        fig.add_trace(go.Scatter(x=st.session_state.timestamps, y=st.session_state.difference_data,
                                 mode="lines+markers", name="Difference"))

        fig.update_layout(
            title="Kanal Water Levels",
            xaxis_title="Time",
            yaxis_title="Water Level (cm)",
            height=450
        )

        chart_placeholder.plotly_chart(fig, width='stretch')

    else:
        reading_placeholder.info("Waiting for ESP32 data…")

# ---------------- DATA LOGGING VIEW ----------------
def show_data_logging():
    st.title("📄 DATA LOGGING - Full Blockages Only")
    csv_file = f"logs/daloy_log_{datetime.now().strftime('%Y-%m-%d')}.csv"

    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
        if not df.empty:
            expected_cols = ["Timestamp","Status","Upstream","Downstream","Difference"]
            df = df[[col for col in expected_cols if col in df.columns]]
            st.dataframe(df, width='stretch')
        else:
            st.info("No full blockage logs yet today.")
    else:
        st.info("No full blockage logs yet today.")

# ---------------- PAGE CONTROL ----------------
tab = st.tabs(["Dashboard", "DATA LOGGING"])
with tab[0]:
    show_dashboard()
with tab[1]:
    show_data_logging()