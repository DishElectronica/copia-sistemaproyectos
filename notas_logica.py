import os
import sqlite3

# Usaremos un único nombre para todo el sistema
NOMBRE_DB = 'sistema_limpio.db'



def borrar_base_de_datos():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), NOMBRE_DB)
    if os.path.exists(db_path):
        os.remove(db_path)
        return True
    return False

def obtener_conexion():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, NOMBRE_DB)
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sistema_limpio.db')
    
    
    conn = sqlite3.connect(db_path)
    
    # CORRECCIÓN: 'leido' en lugar de 'lceido'
    conn.execute('''CREATE TABLE IF NOT EXISTS notas 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                     proyecto_id INTEGER, 
                     contenido TEXT, 
                     leido INTEGER DEFAULT 0, 
                     fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.row_factory = sqlite3.Row
    return conn

def guardar_nota_db(proyecto_id, contenido):
    conn = obtener_conexion()
    conn.execute('INSERT INTO notas (proyecto_id, contenido) VALUES (?, ?)', (proyecto_id, contenido))
    conn.commit()
    conn.close()

def obtener_notas_db(proyecto_id):
    conn = obtener_conexion()
    notas = conn.execute('''
        SELECT * FROM notas 
        WHERE proyecto_id = ? 
        ORDER BY fecha_creacion DESC
    ''', (proyecto_id,)).fetchall()
    
    resultado = [dict(n) for n in notas]
    conn.close()
    return resultado


def marcar_como_leido(nota_id): # Cambiamos proyecto_id por nota_id
    conn = obtener_conexion()
    # Ahora actualizamos basándonos en el ID único de la nota
    conn.execute('UPDATE notas SET leido = 1 WHERE id = ?', (nota_id,))
    conn.commit()
    conn.close()    

def tiene_notas_pendientes(proyecto_id):
    conn = obtener_conexion()
    # Buscamos si existe al menos una nota sin leer
    cursor = conn.execute('SELECT 1 FROM notas WHERE proyecto_id = ? AND leido = 0 LIMIT 1', (proyecto_id,))
    resultado = cursor.fetchone()
    conn.close()
    return resultado is not None    