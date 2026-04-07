#!/usr/bin/env python3
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'phishdns.db')
HOSTS_FILE = '/etc/hosts'
BACKUP_FILE = '/etc/hosts.backup'

def crear_backup():
    if not os.path.exists(BACKUP_FILE):
        os.system(f'sudo cp {HOSTS_FILE} {BACKUP_FILE}')
        print("[BACKUP] Creado")

def bloquear_dominio(dominio):
    crear_backup()
    with open(HOSTS_FILE, 'a') as f:
        f.write(f"127.0.0.1 {dominio}\n")
    print(f"[BLOQUEADO] {dominio}")

def bloquear_sospechosos():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT dominio FROM dominios WHERE clasificacion != 'seguro'")
    for row in cursor.fetchall():
        dominio = row[0]
        bloquear_dominio(dominio)
    conn.close()

if __name__ == '__main__':
    bloquear_sospechosos()
