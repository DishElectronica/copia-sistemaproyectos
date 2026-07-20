import os
import sqlite3
from db_supabase import obtener_notas_supabase

def obtener_notas_proyecto(proyecto_id):
    """Función puente para obtener notas desde Supabase"""
    print(f"--- LEYENDO NOTAS DE SUPABASE PARA PROYECTO: {proyecto_id} ---")
    return obtener_notas_supabase(proyecto_id)

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
    db_path = os.path.join(base_dir, 'sistema_limpio.db')
    conn = sqlite3.connect(db_path)
    
    # CORRECCIÓN: 'leido' en lugar de 'lceido'
    conn.execute('''CREATE TABLE IF NOT EXISTS notas 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                     proyecto_id INTEGER, 
                     contenido TEXT, 
                     leido INTEGER DEFAULT 0)''')
                    
    try:
        conn.execute('ALTER TABLE notas ADD COLUMN fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        conn.commit()
    except sqlite3.OperationalError:
        pass # La columna ya existe, no hacemos nada
    
    conn.row_factory = sqlite3.Row
    return conn

def guardar_nota_db(proyecto_id, contenido):
    conn = obtener_conexion()
    
    try:
        # 2. PASO: Ejecutar la operación de inserción (INSERT)
        cursor = conn.cursor() # Necesitamos un cursor para ejecutar
        cursor.execute('INSERT INTO notas (proyecto_id, contenido) VALUES (?, ?)', (proyecto_id, contenido))

        conn.commit()
        print("--- ÉXITO: Nota guardada ---")

    except Exception as e:
        # Si algo sale mal, el error se captura aquí
        print(f"--- ERROR CRÍTICO EN DB: {str(e)} ---")
        conn.rollback() # Revertimos cualquier cambio parcial para evitar corrupción
        
    finally:
        # 4. PASO: Cerrar la conexión SIEMPRE (para no dejarla abierta)
        conn.close()

    #conn.execute('INSERT INTO notas (proyecto_id, contenido) VALUES (?, ?)', (proyecto_id, contenido))
    #conn.commit()

    
def obtener_notas_db(proyecto_id):
    conn = obtener_conexion()
    cursor = conn.execute('SELECT * FROM notas WHERE proyecto_id = ? ORDER BY fecha_creacion DESC', (proyecto_id,))
    
    # Esto es más seguro para obtener los nombres de las columnas
    columnas = [description[0] for description in cursor.description]
    notas = cursor.fetchall()
    
    # Crear lista de diccionarios manualmente
    resultado = [dict(zip(columnas, fila)) for fila in notas]
    
    conn.close()
    return resultado

from db_supabase import obtener_notas_supabase

def obtener_notas_proyecto(proyecto_id):
    """Función puente para obtener notas desde Supabase"""
    print(f"--- LEYENDO NOTAS DE SUPABASE PARA PROYECTO: {proyecto_id} ---")
    return obtener_notas_supabase(proyecto_id)

def marcar_como_leido(nota_id):
    conn = obtener_conexion()
    proyecto_id = None # Declaramos para usarlo luego
    
    try:
        # 1. Obtenemos el proyecto_id PRIMERO (para poder contar después)
        proyecto = conn.execute('SELECT proyecto_id FROM notas WHERE id = ?', (nota_id,)).fetchone()
        proyecto_id = proyecto[0] if proyecto else None
        
        # 2. Marcamos como leída
        conn.execute('UPDATE notas SET leido = 1 WHERE id = ?', (nota_id,))
        conn.commit()
    finally:
        conn.close()

    # 3. Proceso seguro: Sincronización con Supabase
    try:
        from db_supabase import sync_nota_leida_to_supabase
        sync_nota_leida_to_supabase(nota_id)
    except Exception as e:
        print(f"Error sincronizando con Supabase, pero la base local está a salvo: {e}")

    # 4. Verificamos si quedan pendientes usando la función que YA EXISTE
    # Si tenemos un proyecto_id, verificamos; si no, retornamos False
    if proyecto_id:
        return tiene_notas_pendientes(proyecto_id)
    return False


def tiene_notas_pendientes(proyecto_id):
    conn = obtener_conexion()
    # Buscamos si existe al menos una nota sin leer
    cursor = conn.execute('SELECT 1 FROM notas WHERE proyecto_id = ? AND leido = 0 LIMIT 1', (proyecto_id,))
    resultado = cursor.fetchone()
    conn.close()
    return resultado is not None    


def obtener_estado_pendientes_general():
    """
    Retorna un diccionario con los IDs de proyectos que tienen notas pendientes.
    Formato: {proyecto_id: True, proyecto_id: True}
    Esto evita hacer 20 consultas si tienes 20 proyectos.
    """
    conn = obtener_conexion()
    # Traemos solo los IDs que tengan al menos una nota sin leer
    cursor = conn.execute('SELECT DISTINCT proyecto_id FROM notas WHERE leido = 0')
    pendientes = {row[0] for row in cursor.fetchall()}
    conn.close()
    return pendientes