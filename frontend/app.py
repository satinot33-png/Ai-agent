from flask import Flask, jsonify

app = Flask(__name__)

# 7 AI Agent untuk Export
AGENTS = [
    {"id": 1, "nama": "AI Asia", "negara": "", "status": "off"},
    {"id": 2, "nama": "AI Eropa", "negara": "", "status": "off"},
    {"id": 3, "nama": "AI Afrika", "negara": "", "status": "off"},
    {"id": 4, "nama": "AI Amerika", "negara": "", "status": "off"},
    {"id": 5, "nama": "AI Australia", "negara": "", "status": "off"},
    {"id": 6, "nama": "AI Timur Tengah", "negara": "", "status": "off"},
    {"id": 7, "nama": "AI Cari Bayer", "negara": "", "status": "off"}
]

@app.route('/')
def home():
    return jsonify({"pesan": "Java Global Commodities - 7 AI Agent Aktif!", "jumlah_ai": len(AGENTS)})

@app.route('/agents')
def daftar_agents():
    return jsonify(AGENTS)

@app.route('/jalankan-semua')
def jalankan_semua():
    for a in AGENTS:
        a["status"] = "on"
    return jsonify({"pesan": "Semua AI Dijalankan!", "data": AGENTS})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
