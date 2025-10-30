import streamlit as st
import plotly.graph_objects as go
import time, csv, os, pandas as pd
from datetime import datetime
import requests
from streamlit_autorefresh import st_autorefresh


# ---------------- CONFIG ----------------
os.makedirs("logs", exist_ok=True)
st.set_page_config(page_title="💧 DALOY Monitoring App", layout="wide")  # full screen

# ---------------- STYLE ----------------
st.markdown("""
<style>
body, .main { background-color: #a7d8f0 !important; color: black !important; }
.block-container { background-color: #a7d8f0 !important; padding: 25px; max-width: 95% !important; }
.reading-box { background-color: #ffffff; border: 3px solid #0d47a1; border-radius: 12px; padding: 20px; text-align: center; color: black !important; }
.reading-grid { display: flex; justify-content: space-around; margin-top: 15px; flex-wrap: wrap; gap: 10px; }
.reading-item { flex: 1; min-width: 180px; background-color: #e3f2fd; border: 2px solid #0d47a1; border-radius: 8px; padding: 15px; font-weight: bold; text-align: center; color: black !important; }
.remark-box { background-color: #e3f2fd; border: 2px solid #0d47a1; border-radius: 10px; padding: 15px; margin-top: 15px; text-align: center; font-size: 17px; color: black !important; }
button[kind="primary"] { background-color: #0d47a1 !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

# ---------------- BACKEND CONFIG ----------------
def fetch_data():
    try:
        FIREBASE_URL = "https://daloy-alert-default-rtdb.asia-southeast1.firebasedatabase.app/canal_readings.json"
        response = requests.get(FIREBASE_URL, timeout=5)

        if response.status_code == 200:
            data = response.json()

            if not data:
                st.info("No data found in Firebase yet. Waiting for ESP32 to send readings...")
                return None, None, None

            # Get the most recent record
            last_key = list(data.keys())[-1]
            latest = data[last_key]

            downstream = latest.get("downstream")
            upstream = latest.get("upstream")
            difference = latest.get("difference")

            if downstream is not None and upstream is not None and difference is not None:
                return upstream, downstream, difference

            st.warning("Incomplete data in latest Firebase record.")
            return None, None, None

        else:
            st.error(f"Firebase responded with status: {response.status_code}")
            return None, None, None

    except Exception as e:
        st.error(f"Error fetching data from Firebase: {e}")
        return None, None, None



# ---------------- SESSION INITIALIZATION ----------------
if "view" not in st.session_state:
    st.session_state.view = "dashboard"
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
    elif status == "🚨 FULL BLOCKAGE":
        return "🌊 Full blockage detected! Immediate maintenance required."
    else:
        return ""

def log_to_csv(timestamp, upstream, downstream, difference, status):
    filename = f"logs/daloy_log_{datetime.now().strftime('%Y-%m-%d')}.csv"
    try:
        with open(filename, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, upstream, downstream, difference, status])
    except PermissionError:
        st.warning(f"⚠️ Log file {filename} is in use — skipping this entry.")

# ---------------- DASHBOARD VIEW ----------------
def show_dashboard():
    # Auto-refresh every 2 seconds
    st_autorefresh(interval=2000, key="datarefresh")  # 👈 add this here

    st.title("💧 DALOY Monitoring App")
    st.subheader("Real-Time Kanal Flood Monitoring Dashboard")

    upstream, downstream, difference = fetch_data()
    timestamp = datetime.now()


    if upstream is not None and downstream is not None and difference is not None:

        status_display, color = get_status(difference)
        remark = get_remark(status_display)

        st.session_state.timestamps.append(timestamp)
        st.session_state.upstream_data.append(upstream)
        st.session_state.downstream_data.append(downstream)
        st.session_state.difference_data.append(difference)
        st.session_state.status_data.append(status_display)

        log_to_csv(timestamp, upstream, downstream, difference, status_display)

        st.markdown(f"""
        <div class="reading-box" style="background-color:{color};">
            <h2>{status_display}</h2>
            <div class="reading-grid">
                <div class="reading-item">🌊 Upstream<br>{upstream:.2f} cm</div>
                <div class="reading-item">💧 Downstream<br>{downstream:.2f} cm</div>
                <div class="reading-item">🔁 Difference<br>{difference:.2f} cm</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"<div class='remark-box'>{remark}</div>", unsafe_allow_html=True)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=st.session_state.timestamps, y=st.session_state.upstream_data,
                                 mode="lines+markers", name="🌊 Upstream", line=dict(color="blue", width=3)))
        fig.add_trace(go.Scatter(x=st.session_state.timestamps, y=st.session_state.downstream_data,
                                 mode="lines+markers", name="💧 Downstream", line=dict(color="darkgreen", width=3)))
        fig.add_trace(go.Scatter(x=st.session_state.timestamps, y=st.session_state.difference_data,
                                 mode="lines+markers", name="🔁 Difference", line=dict(color="red", width=3)))
        fig.update_layout(
            title=f"💧 Kanal Water Levels ({status_display})",
            xaxis_title="Time",
            yaxis_title="Water Level (cm)",
            paper_bgcolor="#a7d8f0",
            plot_bgcolor="#ffffff",
            font=dict(color="black"),
            height=450
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("Waiting for data... Make sure the ESP32 is connected and sending readings.")

    # auto-refresh every 2 seconds
    time.sleep(2)
    st.rerun()

    if st.button("📊 Show Log CSV with Spikes", key="log_view_button"):
        st.session_state["view"] = "log"
        st.rerun()

# ---------------- LOG VIEW ----------------
def show_log_view():
    st.title("📄 Log Viewer - DALOY Readings")
    csv_file = f"logs/daloy_log_{datetime.now().strftime('%Y-%m-%d')}.csv"
    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file, names=["Timestamp","Upstream","Downstream","Difference","Status"])
        df["Spike"] = df["Difference"] >= 1.0

        def highlight_spikes(row):
            color = "#ffcccc" if row["Spike"] else ""
            return ["background-color: " + color] * len(row)

        st.dataframe(df.style.apply(highlight_spikes, axis=1), use_container_width=True)
    else:
        st.info("No log data found yet.")

    if st.button("⬅️ Back to Dashboard", key="back_to_dashboard"):
        st.session_state["view"] = "dashboard"
        st.rerun()

# ---------------- PAGE CONTROL ----------------
if st.session_state.view == "dashboard":
    show_dashboard()
else:
    show_log_view()
