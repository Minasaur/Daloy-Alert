import streamlit as st
import plotly.graph_objects as go
import csv, os, pandas as pd
from datetime import datetime
import requests
from streamlit_autorefresh import st_autorefresh

# ---------------- CONFIG ----------------
os.makedirs("logs", exist_ok=True)
st.set_page_config(page_title="💧 DALOY Monitoring App", layout="wide")
REFRESH_INTERVAL = 5000  # milliseconds (5 seconds)

# ---------------- STYLE ----------------
st.markdown("""
<style>
html, body, [class*="css"]  { color: black !important; background-color: #a7d8f0 !important; }
.block-container { background-color: #a7d8f0 !important; padding: 15px; max-width: 95% !important; }

h1, h2, h3, h4, h5, h6, p, span, label, div { color: black !important; }

.reading-box {
    border: 3px solid #0d47a1; border-radius: 12px; padding: 15px; text-align:center; 
    font-size:18px; font-weight:bold; color:black !important;
}
.reading-grid { display:flex; justify-content:space-around; margin-top:10px; flex-wrap:wrap; gap:10px; }
.reading-item {
    flex:1; min-width:150px; background:#e3f2fd; border:2px solid #0d47a1;
    border-radius:8px; padding:15px; font-weight:bold; text-align:center; color:black !important;
}
.remark-box {
    background:#e3f2fd; border:2px solid #0d47a1; border-radius:10px;
    padding:15px; margin-top:10px; text-align:center; font-size:16px; color:black !important;
}
.status-dot {
    height:12px; width:12px; border-radius:50%; display:inline-block; margin-left:5px;
    animation: blink 1s infinite;
}
@keyframes blink { 0% {opacity:1;} 50% {opacity:0;} 100% {opacity:1;} }
</style>
""", unsafe_allow_html=True)

# ---------------- FIREBASE FETCH ----------------
def fetch_data():
    try:
        url = "https://daloy-alert-default-rtdb.asia-southeast1.firebasedatabase.app/canal_readings.json"
        data = requests.get(url, timeout=5).json()
        if not data: return None, None, None
        upstream = float(data["ESP1"]["upstream"])
        downstream = float(data["ESP2"]["downstream"])
        difference = abs(upstream - downstream)
        return upstream, downstream, difference
    except Exception as e:
        st.warning(f"Firebase error: {e}")
        return None, None, None

# ---------------- SESSION STATE ----------------
if "timestamps" not in st.session_state:
    st.session_state.timestamps = []
    st.session_state.upstream = []
    st.session_state.downstream = []
    st.session_state.diff = []
    st.session_state.last_values = None

# ---------------- STATUS ----------------
def get_status(diff):
    if diff >= 2.5: return "🚨 FULL BLOCKAGE", "#ff4d4d"
    elif diff >= 1.0: return "⚠️ PARTIAL BLOCKAGE", "#fff176"
    return "✅ NORMAL FLOW", "#81c784"

def get_remark(status):
    if "NORMAL" in status: return "💧 Flow is stable — no obstruction detected."
    if "PARTIAL" in status: return "⚠️ Partial blockage detected. Monitor canal condition."
    return "🌊 Full blockage detected! Immediate maintenance required."

# ---------------- LOGGING ----------------
def log_full_blockage(timestamp, upstream, downstream, diff, status):
    if "FULL BLOCKAGE" not in status: return
    file = f"logs/daloy_log_{datetime.now().strftime('%Y-%m-%d')}.csv"
    file_exists = os.path.exists(file)
    try:
        with open(file,"a",newline="",encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists: writer.writerow(["Timestamp","Status","Upstream","Downstream","Difference"])
            writer.writerow([timestamp.strftime("%Y-%m-%d %H:%M:%S"),status,upstream,downstream,diff])
    except PermissionError:
        st.warning("Unable to write to CSV. Close any open file.")

# ---------------- DASHBOARD ----------------
def show_dashboard():
    st.title("💧 DALOY Monitoring App")
    st.subheader("Real-Time Kanal Flood Monitoring Dashboard")

    reading_box = st.empty()
    remark_box = st.empty()
    chart_box = st.empty()

    st_autorefresh(interval=REFRESH_INTERVAL, key="refresh")

    upstream, downstream, diff = fetch_data()
    if upstream is None: 
        reading_box.info("Waiting for ESP32 data…")
        return

    current = (upstream, downstream)
    if st.session_state.last_values == current: return
    st.session_state.last_values = current
    timestamp = datetime.now()

    # store values and limit to 25 points for smooth graph
    MAX_POINTS = 25
    st.session_state.timestamps.append(timestamp)
    st.session_state.upstream.append(upstream)
    st.session_state.downstream.append(downstream)
    st.session_state.diff.append(diff)
    st.session_state.timestamps = st.session_state.timestamps[-MAX_POINTS:]
    st.session_state.upstream = st.session_state.upstream[-MAX_POINTS:]
    st.session_state.downstream = st.session_state.downstream[-MAX_POINTS:]
    st.session_state.diff = st.session_state.diff[-MAX_POINTS:]

    status, color = get_status(diff)
    log_full_blockage(timestamp, upstream, downstream, diff, status)

    live_dot = f"<span class='status-dot' style='background:{color}'></span>"
    reading_box.markdown(f"""
    <div class='reading-box' style='background:{color}'>
        <h2>{status} {live_dot}</h2>
        <div class='reading-grid'>
            <div class='reading-item'>🌊 Upstream<br>{upstream:.2f} cm</div>
            <div class='reading-item'>💧 Downstream<br>{downstream:.2f} cm</div>
            <div class='reading-item'>🔁 Difference<br>{diff:.2f} cm</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    remark_box.markdown(f"<div class='remark-box'>{get_remark(status)}</div>", unsafe_allow_html=True)

    # Plotly chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=st.session_state.timestamps, y=st.session_state.upstream,
                             mode="lines+markers", name="Upstream"))
    fig.add_trace(go.Scatter(x=st.session_state.timestamps, y=st.session_state.downstream,
                             mode="lines+markers", name="Downstream"))
    fig.add_trace(go.Scatter(x=st.session_state.timestamps, y=st.session_state.diff,
                             mode="lines+markers", name="Difference"))
    fig.update_layout(title="Kanal Water Levels",
                      xaxis_title="Time", yaxis_title="Water Level (cm)",
                      height=400, font=dict(color="black"))
    chart_box.plotly_chart(fig, width="stretch")

# ---------------- DATA LOGGING ----------------
def show_logs():
    st.title("📄 DATA LOGGING")
    file = f"logs/daloy_log_{datetime.now().strftime('%Y-%m-%d')}.csv"
    if os.path.exists(file):
        df = pd.read_csv(file)
        st.dataframe(df, width="stretch")
    else:
        st.info("No logs yet today.")

# ---------------- TABS ----------------
tab1, tab2 = st.tabs(["Dashboard", "Data Logs"])
with tab1: show_dashboard()
with tab2: show_logs()