from flask import Blueprint, jsonify
# Importamos la lógica que ya tienes (asegúrate de tener tus funciones ahí)
from notas_logica import marcar_como_leido 

from flask import Blueprint, jsonify
from notas_logica import (
    tiene_notas_pendientes, 
    guardar_nota_db, 
    obtener_notas_db, 
    marcar_como_leido
)

# Definimos el Blueprint
notas_bp = Blueprint('notas_bp', __name__)

@notas_bp.route('/notas/<int:proyecto_id>', methods=['GET', 'POST'])
def gestionar_notas(proyecto_id):
    if request.method == 'POST':
        contenido = request.form.get('contenido', '')
        guardar_nota_db(proyecto_id, contenido)
        return jsonify({"status": "ok"})
    
      
    notas = obtener_notas_db(proyecto_id) 
    # Si viene desde un fetch de JS, devuelves JSON, si viene desde navegador, render_template
    return render_template('notas.html', notas=notas, proyecto_id=proyecto_id)


# Aquí mueves todas las rutas que usen 'marcar_como_leido' o 'obtener_notas'
@notas_bp.route('/marcar-leido/<int:nota_id>')
def marcar_leido_route(nota_id):
    hay_mas_pendientes = marcar_como_leido(nota_id)
    return jsonify({"status": "success", "tiene_pendientes": hay_mas_pendientes})

# Si tienes más rutas relacionadas con notas (como agregar o listar), 
# las vas moviendo aquí poco a poco
# 1. Creamos el Blueprint llamado 'notas_bp'
notas_bp = Blueprint('notas_bp', __name__)

# 2. Movemos la ruta aquí, pero en lugar de @app.route usamos @notas_bp.route
@notas_bp.route('/marcar-leido/<int:nota_id>')
def marcar_leido_route(nota_id):
    hay_mas_pendientes = marcar_como_leido(nota_id)
    return jsonify({"status": "success", "tiene_pendientes": hay_mas_pendientes})