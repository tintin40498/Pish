#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask, request, jsonify
from agent.classifier import consultar_dominio, dominios_sospechosos
import sqlite3
import json

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), '../db/phishdns.db')

@app.route('/')
def index():
    return jsonify({
        'service': 'PhishDNS Intelligence API',
        'version': '1.0',
        'endpoints': [
            '/api/v1/check?dominio=ejemplo.com',
            '/api/v1/dominios',
            '/api/v1/sospechosos',
            '/api/v1/estadisticas',
            '/health'
        ]
    })

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/api/v1/check')
def check_domain():
    dominio = request.args.get('dominio')
    if not dominio:
        return jsonify({'error': 'Falta parametro: dominio'}), 400
    
    resultado = consultar_dominio(dominio)
    return jsonify(resultado)

@app.route('/api/v1/dominios')
def get_dominios():
    limit = request.args.get('limit', 100, type=int)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT dominio, clasificacion, ip, fecha, consultas
        FROM dominios
        ORDER BY fecha DESC
        LIMIT ?
    ''', (limit,))
    
    resultados = []
    for row in cursor.fetchall():
        resultados.append({
            'dominio': row[0],
            'clasificacion': row[1],
            'ip': row[2],
            'fecha': row[3],
            'consultas': row[4]
        })
    
    conn.close()
    return jsonify(resultados)

@app.route('/api/v1/sospechosos')
def get_sospechosos():
    return jsonify(dominios_sospechosos())

@app.route('/api/v1/estadisticas')
def get_estadisticas():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM dominios')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT clasificacion, COUNT(*) FROM dominios GROUP BY clasificacion')
    por_clasificacion = {row[0]: row[1] for row in cursor.fetchall()}
    
    cursor.execute('SELECT COUNT(*) FROM dominios WHERE fecha > datetime("now", "-1 day")')
    ultimas_24h = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'total_dominios': total,
        'clasificaciones': por_clasificacion,
        'ultimas_24h': ultimas_24h,
        'porcentaje_sospechosos': round((por_clasificacion.get('phishing_login', 0) + 
                                          por_clasificacion.get('phishing_secure', 0) +
                                          por_clasificacion.get('phishing_verify', 0) +
                                          por_clasificacion.get('dominio_gratuito', 0)) / max(total, 1) * 100, 2)
    })

if __name__ == '__main__':
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    print("🛡️ PhishDNS API Server")
    print("=====================")
    print("API disponible en: http://localhost:5000")
    print("Endpoint de prueba: http://localhost:5000/api/v1/check?dominio=google.com")
    print("")
    app.run(host='0.0.0.0', port=5000, debug=False)
