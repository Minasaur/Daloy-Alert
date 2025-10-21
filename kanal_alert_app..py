import serial, streamlit as st, plotly.graph_objects as go
import smtplib
from email.mime.text import MIMEText
import time, threading, queue, csv
from datetime import datetime
import os
os.makedirs("logs", exist_ok=True)


st.set_page_config(page_title="💧 DALOY Monitoring App", layout="centered")
st.title("💧 DALOY Monitoring App")
st.subheader("Real-Time Kanal Flood Monitoring Dashboard")

st.markdown("""
<style>
body, .main { background-color: #a7d8f0 !important; color: black !important; }
.block-container { background-color: #a7d8f0 !important; padding: 25px; }
.reading-box { background-color: #ffffff; border: 3px solid #0d47a1; border-radius: 12px; padding: 20px; text-align: center; color: black !important; }
.reading-grid { display: flex; justify-content: space-around; margin-top: 15px; }
.reading-item { flex: 1; margin: 0 6px; background-color: #e3f2fd; border: 2px solid #0d47a1; border-radius: 8px; padding: 15px; font-weight: bold; text-align: center; color: black !important; }
.remark-box { background-color: #e3f2fd; border: 2px solid #0d47a1; border-radius: 10px; padding: 15px; margin-top: 15px; text-align: center; font-size: 17px; color: black !important; }
</style>
""", unsafe_allow_html=True)

# ---------------- SIDEBAR ----------------
st.sidebar.header("📩 Alert Email")
recipient_email = st.sidebar.text_input("Enter your email to receive alerts:")

# ---------------- EMAIL ----------------
SENDER_EMAIL = "canal.monitoring876@gmail.com"
SENDER_PASSWORD = "qfpc wddz noca dycb"

email_queue = queue.Queue()
def send_email(to_email, subject, body):
    if not to_email:
        return
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print("Email error:", e)

def email_worker():
    while True:
        try:
            to_email, subject, body = email_queue.get()
            send_email(to_email, subject, body)
            email_queue.task_done()
        except Exception as e:
            print("Email worker error:", e)

threading.Thread(target=email_worker, daemon=True).start()

# ---------------- SERIAL ----------------
if 'ser' not in st.session_state:
    try:
        st.session_state.ser = serial.Serial("COM5", 115200, timeout=2)
        st.success("✅ ESP32 connected on COM5")
    except Exception as e:
        st.session_state.ser = None
        st.error(f"⚠️ Could not open COM5: {e}")

ser = st.session_state.ser
if ser is None:
    st.stop()

# ---------------- STORAGE ----------------
if 'timestamps' not in st.session_state:
    st.session_state.timestamps = []
    st.session_state.upstream_data = []
    st.session_state.downstream_data = []
    st.session_state.difference_data = []
    st.session_state.status_data = []
    st.session_state.last_status_sent = None

placeholder = st.empty()
remark_placeholder = st.empty()
chart_placeholder = st.empty()

# ---------------- STATUS THRESHOLDS ----------------
FLOOD_THRESHOLD = 7.0
MODERATE_THRESHOLD = 4.0

def get_status(upstream):
    if upstream >= FLOOD_THRESHOLD:
        return "🚨 FLOODED", "#ff4d4d"
    elif upstream >= MODERATE_THRESHOLD:
        return "⚠️ MODERATE", "#fff176"
    else:
        return "✅ NORMAL", "#81c784"

def get_remark(status):
    if status == "✅ NORMAL":
        return "💧 Water levels are within safe limits."
    elif status == "⚠️ MODERATE":
        return "⚠️ Water level approaching standard."
    elif status == "🚨 FLOODED":
        return "🌊 Overflow observed. Maintenance needed."
    else:
        return ""

def read_serial():
    try:
        if ser.in_waiting:
            line = ser.readline().decode(errors='ignore').strip()
            parts = line.split(",")
            if len(parts) == 2:
                upstream = float(parts[0])
                downstream = float(parts[1])
                return upstream, downstream
        return None, None
    except:
        return None, None


def log_to_csv(timestamp, upstream, downstream, difference, status):
    filename = f"logs/daloy_log_{datetime.now().strftime('%Y-%m-%d')}.csv"
    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, upstream, downstream, difference, status])



# ---------------- DEFAULT ----------------
with placeholder.container():
    st.markdown(f"""
    <div class="reading-box">
        <h2>⚠️ Waiting for ESP32 readings...</h2>
        <div class="reading-grid">
            <div class="reading-item">🌊 Upstream<br>-- cm</div>
            <div class="reading-item">💧 Downstream<br>-- cm</div>
            <div class="reading-item">🔁 Difference<br>-- cm</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with remark_placeholder.container():
    st.markdown(f"<div class='remark-box'>Waiting for ESP32 readings...</div>", unsafe_allow_html=True)

chart_placeholder.empty()

# ---------------- UPDATE LOOP ----------------
while True:
    upstream, downstream = read_serial()
    if upstream is not None and downstream is not None:
        timestamp = time.strftime("%H:%M:%S")
        difference = upstream - downstream

        status_display, color = get_status(upstream)
        st.session_state.timestamps.append(timestamp)
        st.session_state.upstream_data.append(upstream)
        st.session_state.downstream_data.append(downstream)
        st.session_state.difference_data.append(difference)
        st.session_state.status_data.append(status_display)

        remark = get_remark(status_display)

        # Email alerts
        if recipient_email and status_display in ["⚠️ MODERATE", "🚨 FLOODED"]:
            if st.session_state.last_status_sent != status_display:
                email_queue.put((recipient_email, f"{status_display} - Kanal Alert", remark))
                st.session_state.last_status_sent = status_display
        elif status_display == "✅ NORMAL":
            st.session_state.last_status_sent = None

        log_to_csv(timestamp, upstream, downstream, difference, status_display)

        # Update placeholders
        with placeholder.container():
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

        with remark_placeholder.container():
            st.markdown(f"<div class='remark-box'>{remark}</div>", unsafe_allow_html=True)

        # Update chart
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
            height=400
        )
        chart_placeholder.plotly_chart(fig, use_container_width=True)

    time.sleep(1)
