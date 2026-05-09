from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app) 


@app.route('/token', methods=['POST'])
def login():

    username = request.form.get('username')
    password = request.form.get('password')

  
    if username == "admin" and password == "123":
        return jsonify({
            "access_token": "token-rahasia-jal",
            "token_type": "bearer"
        })
    else:
        return jsonify({"detail": "Username atau Password salah"}), 401


@app.route('/detection/geojson', methods=['GET'])
def get_detection():
    file_path = 'hasil_deteksi.json'
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            data = json.load(f)
        return jsonify(data)
    return jsonify({"type": "FeatureCollection", "features": []})


@app.route('/facilities/geojson', methods=['GET'])
def get_facilities():
    
    return jsonify({"type": "FeatureCollection", "features": []})


@app.route('/facilities', methods=['POST'])
def add_facility():
    
    return jsonify({"status": "success", "message": "Data berhasil disimpan"})

if __name__ == '__main__':
    app.run(port=8000, debug=True) 