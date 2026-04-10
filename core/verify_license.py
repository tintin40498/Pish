#!/usr/bin/env python3
import requests
import json
import os
import sys
from datetime import datetime

CONFIG_FILE = os.path.join(os.path.dirname(__file__), '..', 'config.json')
API_URL = os.environ.get('PISH_API_URL', 'http://localhost:5000')

def cargar_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def guardar_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def verificar_licencia():
    config = cargar_config()
    licencia_key = config.get('licencia_key')
    email = config.get('email')
    
    if not licencia_key or not email:
        print("❌ No hay licencia configurada. Ejecutá: python3 core/verify_license.py config")
        return False
    
    print(f"🔍 Verificando licencia para {email}...")
    
    try:
        res = requests.post(f'{API_URL}/api/v1/verificar_licencia', 
                           json={'licencia_key': licencia_key, 'email': email},
                           timeout=10)
        data = res.json()
        
        if data.get('ok'):
            print(f"✅ Licencia válida - Plan: {data.get('plan')}")
            print(f"   Válida hasta: {data.get('valida_hasta')}")
            config['ultima_verificacion'] = datetime.now().isoformat()
            guardar_config(config)
            return True
        else:
            print(f"❌ {data.get('error', 'Licencia inválida')}")
            return False
    except Exception as e:
        print(f"⚠️ Error verificando licencia: {e}")
        ultima_verif = config.get('ultima_verificacion')
        if ultima_verif:
            ultima = datetime.fromisoformat(ultima_verif)
            if (datetime.now() - ultima).days < 1:
                print("   Usando caché (última verificación válida por 24h)")
                return True
        return False

def configurar_licencia():
    print("🛡️ Configurar licencia de Pish")
    email = input("Email: ")
    licencia_key = input("Clave de licencia: ")
    
    guardar_config({
        'email': email,
        'licencia_key': licencia_key,
        'ultima_verificacion': datetime.now().isoformat()
    })
    
    print("✅ Configuración guardada")
    return verificar_licencia()

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'config':
        configurar_licencia()
    else:
        if not verificar_licencia():
            sys.exit(1)
