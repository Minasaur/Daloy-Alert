from flask import Flask, request, jsonify

app = Flask(__name__)
latest_data = {}

@app.route("/data", methods=["POST"])
def receive_data():
    global latest_data
    latest_data = request.json  # ESP32 must POST JSON
    return jsonify({"status": "ok"})

@app.route("/data", methods=["GET"])
def send_data():
    return jsonify(latest_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
