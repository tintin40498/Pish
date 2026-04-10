#!/usr/bin/env python3
import os
import json
import hashlib
import secrets
import re
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, g
from flask_cors import CORS
import jwt
import psycopg2
from psycopg2.extras import RealDictCursor
import redis

app = Flask(__name__)
CORS(app)

# Configuración
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://pish_user:Pish2026!@localhost/pish_db')
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
JWT_SECRET = os.environ.get('JWT_SECRET', secrets.token_hex(32))
JWT_EXPIRATION_HOURS = 24

def get_db():
    if not hasattr(g, 'db'):
        g.db = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return g.db

def get_redis():
    if not hasattr(g, 'redis'):
        g.redis = redis.from_url(REDIS_URL)
    return g.redis

@app.teardown_appcontext
def close_db(error):
    db = getattr(g, 'db', None)
    if db:
        db.close()
    redis_client = getattr(g, 'redis', None)
    if redis_client:
        redis_client.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def validar_email(email):
    return re.match(r'^[^@]+@[^@]+\.[^@]+$', email) is not None

def requiere_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token requerido'}), 401
        
        token = auth_header[7:]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            g.user_id = payload['user_id']
            g.user_email = payload['email']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expirado'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token inválido'}), 401
        
        return f(*args, **kwargs)
    return decorated

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

@app.route('/api/v1/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    nombre = data.get('nombre', '')
    
    if not email or not password:
        return jsonify({'error': 'Email y contraseña requeridos'}), 400
    
    if not validar_email(email):
        return jsonify({'error': 'Email inválido'}), 400
    
    if len(password) < 8:
        return jsonify({'error': 'La contraseña debe tener al menos 8 caracteres'}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO usuarios (uuid, email, password_hash, nombre)
            VALUES (gen_random_uuid()::text, %s, %s, %s)
            RETURNING id, uuid
        """, (email, hash_password(password), nombre))
        user = cursor.fetchone()
        
        cursor.execute("""
            INSERT INTO suscripciones (usuario_id, plan, estado, fecha_inicio, fecha_vencimiento)
            VALUES (%s, 'free', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '365 days')
        """, (user['id'],))
        
        db.commit()
        
        token = jwt.encode({
            'user_id': user['id'],
            'email': email,
            'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
        }, JWT_SECRET, algorithm='HS256')
        
        return jsonify({
            'ok': True,
            'token': token,
            'user': {'id': user['id'], 'email': email, 'nombre': nombre}
        })
        
    except psycopg2.IntegrityError:
        db.rollback()
        return jsonify({'error': 'El email ya está registrado'}), 400

@app.route('/api/v1/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email y contraseña requeridos'}), 400
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT id, email, nombre, password_hash FROM usuarios WHERE email = %s
    """, (email,))
    user = cursor.fetchone()
    
    if not user or user['password_hash'] != hash_password(password):
        return jsonify({'error': 'Email o contraseña incorrectos'}), 401
    
    cursor.execute("""
        UPDATE usuarios SET last_login_at = CURRENT_TIMESTAMP, last_login_ip = %s
        WHERE id = %s
    """, (request.remote_addr, user['id']))
    db.commit()
    
    token = jwt.encode({
        'user_id': user['id'],
        'email': user['email'],
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }, JWT_SECRET, algorithm='HS256')
    
    return jsonify({
        'ok': True,
        'token': token,
        'user': {'id': user['id'], 'email': user['email'], 'nombre': user['nombre']}
    })

@app.route('/api/v1/perfil', methods=['GET'])
@requiere_token
def perfil():
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("""
        SELECT u.id, u.uuid, u.email, u.nombre, u.created_at,
               s.plan, s.estado, s.fecha_vencimiento,
               l.licencia_key, l.ultima_verificacion
        FROM usuarios u
        LEFT JOIN suscripciones s ON u.id = s.usuario_id AND s.estado = 'active'
        LEFT JOIN licencias l ON s.id = l.suscripcion_id AND l.activa = true
        WHERE u.id = %s
    """, (g.user_id,))
    
    user = cursor.fetchone()
    
    return jsonify({
        'id': user['id'],
        'uuid': user['uuid'],
        'email': user['email'],
        'nombre': user['nombre'],
        'miembro_desde': user['created_at'].isoformat() if user['created_at'] else None,
        'suscripcion': {
            'plan': user['plan'] or 'free',
            'estado': user['estado'] or 'inactive',
            'valida_hasta': user['fecha_vencimiento'].isoformat() if user['fecha_vencimiento'] else None
        },
        'licencia': {
            'key': user['licencia_key'],
            'ultima_verificacion': user['ultima_verificacion'].isoformat() if user['ultima_verificacion'] else None
        }
    })

@app.route('/api/v1/verificar_licencia', methods=['POST'])
def verificar_licencia():
    data = request.json
    licencia_key = data.get('licencia_key')
    email = data.get('email')
    
    if not licencia_key or not email:
        return jsonify({'ok': False, 'error': 'Faltan datos'}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("""
        SELECT l.activa, s.plan, s.fecha_vencimiento, s.estado
        FROM licencias l
        JOIN suscripciones s ON l.suscripcion_id = s.id
        JOIN usuarios u ON s.usuario_id = u.id
        WHERE l.licencia_key = %s AND u.email = %s
    """, (licencia_key, email))
    
    licencia = cursor.fetchone()
    
    if not licencia:
        return jsonify({'ok': False, 'error': 'Licencia no encontrada'}), 404
    
    if licencia['estado'] != 'active':
        return jsonify({'ok': False, 'error': 'Suscripción no activa'}), 403
    
    if not licencia['activa']:
        return jsonify({'ok': False, 'error': 'Licencia desactivada'}), 403
    
    if licencia['fecha_vencimiento'] < datetime.now():
        return jsonify({'ok': False, 'error': 'Licencia vencida'}), 403
    
    cursor.execute("""
        UPDATE licencias SET ultima_verificacion = CURRENT_TIMESTAMP, ultima_ip = %s
        WHERE licencia_key = %s
    """, (request.remote_addr, licencia_key))
    db.commit()
    
    return jsonify({
        'ok': True,
        'plan': licencia['plan'],
        'valida_hasta': licencia['fecha_vencimiento'].isoformat()
    })

if __name__ == '__main__':
    print("🛡️ Pish API Server - Modo Termux")
    print(f"   JWT Secret: {JWT_SECRET[:8]}...")
    app.run(host='0.0.0.0', port=5000, debug=False)

# ========== WEBHOOK DE PAYPAL ==========
@app.route('/api/v1/webhook/paypal', methods=['POST'])
def paypal_webhook():
    """Paypal llama a este endpoint cuando alguien paga"""
    data = request.json
    event_type = data.get('event_type')
    
    if event_type == 'PAYMENT.SALE.COMPLETED':
        payer_email = data.get('resource', {}).get('payer', {}).get('email')
        subscription_id = data.get('resource', {}).get('billing_agreement_id')
        amount = data.get('resource', {}).get('amount', {}).get('total')
        plan = 'pro' if float(amount) == 49 else 'business' if float(amount) == 199 else 'free'
        
        db = get_db()
        cursor = db.cursor()
        
        # Buscar usuario por email
        cursor.execute("SELECT id FROM usuarios WHERE email = %s", (payer_email,))
        user = cursor.fetchone()
        
        if user:
            # Desactivar suscripciones anteriores
            cursor.execute("UPDATE suscripciones SET estado = 'expired' WHERE usuario_id = %s", (user['id'],))
            
            # Crear nueva suscripción
            fecha_vencimiento = datetime.now() + timedelta(days=30)
            cursor.execute("""
                INSERT INTO suscripciones (usuario_id, plan, estado, paypal_subscription_id, fecha_inicio, fecha_vencimiento)
                VALUES (%s, %s, 'active', %s, CURRENT_TIMESTAMP, %s)
            """, (user['id'], plan, subscription_id, fecha_vencimiento))
            
            susc_id = cursor.lastrowid
            
            # Generar nueva licencia
            licencia_key = secrets.token_hex(32)
            cursor.execute("""
                INSERT INTO licencias (suscripcion_id, licencia_key, activa)
                VALUES (%s, %s, true)
            """, (susc_id, licencia_key))
            
            # Registrar pago
            cursor.execute("""
                INSERT INTO pagos (suscripcion_id, paypal_transaction_id, monto, moneda)
                VALUES (%s, %s, %s, 'USD')
            """, (susc_id, data.get('resource', {}).get('id'), amount))
            
            db.commit()
            
            return jsonify({'ok': True, 'mensaje': 'Suscripción activada', 'licencia_key': licencia_key})
    
    return jsonify({'ok': True})

@app.route('/api/v1/mis_suscripciones', methods=['GET'])
@requiere_token
def mis_suscripciones():
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("""
        SELECT plan, estado, fecha_inicio, fecha_vencimiento, paypal_subscription_id
        FROM suscripciones
        WHERE usuario_id = %s
        ORDER BY fecha_inicio DESC
    """, (g.user_id,))
    
    suscripciones = cursor.fetchall()
    
    return jsonify({'suscripciones': [dict(s) for s in suscripciones]})

# ========== CONFIGURACIÓN DE LOGS ==========
import logging

# Configurar logging a archivo
logging.basicConfig(
    filename='logs/api.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Agregar un log al inicio
logging.info("API iniciada - Versión con webhook")

# ========== RUTA RAÍZ PARA LA WEB ==========
@app.route('/')
def index():
    return jsonify({
        'service': 'Pish API',
        'status': 'operational',
        'endpoints': [
            '/health',
            '/api/v1/register',
            '/api/v1/login',
            '/api/v1/perfil',
            '/api/v1/verificar_licencia',
            '/api/v1/webhook/paypal'
        ]
    })

# ========== RUTA RAÍZ PARA QUE NO DE 404 ==========
@app.route('/')
def home():
    return jsonify({
        "service": "Pish API",
        "status": "operational",
        "version": "1.0.0",
        "endpoints": [
            "/health",
            "/api/v1/register",
            "/api/v1/login",
            "/api/v1/perfil",
            "/api/v1/verificar_licencia",
            "/api/v1/webhook/paypal"
        ]
    })

# ========== SERVIR PÁGINAS WEB ==========
from flask import render_template

@app.route('/web/')
@app.route('/web/<path:filename>')
def serve_web(filename='index.html'):
    try:
        return render_template(filename)
    except:
        return render_template('index.html')

# Redirigir la raíz a la web
@app.route('/')
def home_with_web():
    return render_template('index.html')

# ========== SERVIR PÁGINAS WEB ==========
from flask import render_template

@app.route('/web/')
@app.route('/web/<path:filename>')
def serve_web(filename='index.html'):
    try:
        return render_template(filename)
    except:
        return "Página no encontrada", 404

# Redirigir la raíz a la web
@app.route('/')
def home_with_web():
    return render_template('index.html')
