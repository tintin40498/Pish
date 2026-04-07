# Agregar al final de api/server.py, antes del app.run()

@app.route('/api/v1/bloquear', methods=['POST'])
def bloquear_dominio_api():
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from agent.blocker import PhishBlocker
    
    data = request.get_json()
    dominio = data.get('dominio')
    
    if not dominio:
        return jsonify({'error': 'Falta dominio'}), 400
    
    blocker = PhishBlocker()
    if blocker.bloquear_dominio(dominio):
        return jsonify({'status': 'bloqueado', 'dominio': dominio})
    else:
        return jsonify({'status': 'ya_bloqueado', 'dominio': dominio})

@app.route('/api/v1/desbloquear', methods=['POST'])
def desbloquear_dominio_api():
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from agent.blocker import PhishBlocker
    
    data = request.get_json()
    dominio = data.get('dominio')
    
    if not dominio:
        return jsonify({'error': 'Falta dominio'}), 400
    
    blocker = PhishBlocker()
    if blocker.desbloquear_dominio(dominio):
        return jsonify({'status': 'desbloqueado', 'dominio': dominio})
    else:
        return jsonify({'status': 'no_bloqueado', 'dominio': dominio})

@app.route('/api/v1/bloqueados')
def listar_bloqueados_api():
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from agent.blocker import PhishBlocker
    
    blocker = PhishBlocker()
    return jsonify({'bloqueados': list(blocker.dominios_bloqueados)})
