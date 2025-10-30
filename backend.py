from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # optional: allow cross-origin requests from Streamlit

# Store latest readings globally
latest_data = {
    "upstream": 0.0,
    "downstream": 0.0,
    "difference": 0.0
}

# ---------------- GET endpoint for Streamlit ----------------
@app.route("/data", methods=["GET"])
def get_data():
    return jsonify(latest_data)

# ---------------- POST endpoint for ESP32 ----------------
@app.route("/update", methods=["POST"])
def update_data():
    global latest_data
    try:
        data = request.get_json()
        upstream = data.get("upstream")
        downstream = data.get("downstream")
        difference = data.get("difference")

        # Validate numbers
        if upstream is None or downstream is None or difference is None:
            return jsonify({"status": "error", "message": "Invalid data"}), 400

        latest_data = {
            "upstream": float(upstream),
            "downstream": float(downstream),
            "difference": float(difference)
        }

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ---------------- MAIN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
