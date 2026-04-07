#!/usr/bin/env python3
import re
import json
import subprocess
import sqlite3
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '../db/phishdns.db')

# Patrones de dominios sospechosos (phishing)
PATRONES_SOSPECHOSOS = [
    (r'login.*\.(?!paypal|google|microsoft|apple|amazon)', 'phishing_login'),
    (r'secure.*\.(?!paypal|google|microsoft)', 'phishing_secure'),
    (r'verify.*\.(?!google|microsoft|apple)', 'phishing_verify'),
    (r'update.*\.(?!microsoft|apple|google)', 'phishing_update'),
    (r'account.*\.(?!google|microsoft)', 'phishing_account'),
    (r'banking|banc[oa]', 'phishing_bank'),
    (r'paypal.*\.(?!com|net|org)', 'phishing_paypal'),
    (r'\.tk$|\.ml$|\.ga$|\.cf$|\.gq$', 'dominio_gratuito'),
    (r'\d{10,}', 'dominio_numerico'),
]

# Lista blanca de dominios seguros
DOMINIOS_SEGUROS = [
    'google.com', 'microsoft.com', 'apple.com', 'amazon.com',
    'paypal.com', 'github.com', 'stackoverflow.com', 'reddit.com',
    'twitter.com', 'facebook.com', 'instagram.com', 'linkedin.com'
]

def resolver_dominio(dominio):
    """Resuelve un dominio a IP usando dig"""
    try:
        result = subprocess.run(['dig', '+short', dominio], 
                                capture_output=True, text=True, timeout=5)
        return result.stdout.strip().split('\n')[0] if result.stdout else None
    except:
        return None

def clasificar_dominio(dominio):
    """Clasifica un dominio como seguro o sospechoso"""
    dominio_clean = dominio.lower().strip()
    
    # Verificar lista blanca
    for seguro in DOMINIOS_SEGUROS:
        if dominio_clean.endswith(seguro):
            return 'seguro'
    
    # Verificar patrones sospechosos
    for patron, tipo in PATRONES_SOSPECHOSOS:
        if re.search(patron, dominio_clean, re.IGNORECASE):
            return tipo
    
    return 'desconocido'

def guardar_registro(dominio, clasificacion, ip=None):
    """Guarda el dominio en la base de datos"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dominios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dominio TEXT UNIQUE,
            clasificacion TEXT,
            ip TEXT,
            fecha TEXT,
            consultas INTEGER DEFAULT 1
        )
    ''')
    
    cursor.execute('''
        INSERT INTO dominios (dominio, clasificacion, ip, fecha)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(dominio) DO UPDATE SET
            consultas = consultas + 1,
            fecha = excluded.fecha
    ''', (dominio, clasificacion, ip, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def consultar_dominio(dominio):
    """Consulta un dominio (resuelve, clasifica y guarda)"""
    print(f"[*] Consultando: {dominio}")
    
    ip = resolver_dominio(dominio)
    clasificacion = clasificar_dominio(dominio)
    
    guardar_registro(dominio, clasificacion, ip)
    
    return {
        'dominio': dominio,
        'ip': ip,
        'clasificacion': clasificacion,
        'timestamp': datetime.now().isoformat()
    }

def dominios_sospechosos():
    """Retorna lista de dominios sospechosos en DB"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT dominio, clasificacion, ip, fecha, consultas
        FROM dominios
        WHERE clasificacion != 'seguro'
        ORDER BY fecha DESC
        LIMIT 100
    ''')
    
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
    return resultados

if __name__ == '__main__':
    # Test rápido
    test_dominios = [
        'google.com',
        'login.secure.paypal.com.xyz',
        'facebook.com',
        'verify-account-apple.com',
        'banking-secure-update.tk'
    ]
    
    for d in test_dominios:
        resultado = consultar_dominio(d)
        print(f"  → {resultado['clasificacion']} - IP: {resultado['ip']}")
