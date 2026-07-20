from supabase import create_client
import os
from datetime import date, datetime
USAR_SUPABASE = True


# CONFIGURACIÓN
SUPABASE_URL = "https://rbhafdjkdqpijrzuyeeq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJiaGFmZGprZHFwaWpyenV5ZWVxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODEzNzAwMjIsImV4cCI6MjA5Njk0NjAyMn0.VAHqTuFHbLPer88ulL-BQAjvcPQSfCl-lGBVFZJWEp0" 
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- FUNCIÓN 1: CREAR (POST) ---
def enviar_a_supabase(proyecto):
    print("--- INTENTANDO CREAR EN SUPABASE ---")
    try:
        datos = {
            "nombre_proyecto": proyecto.nombre_proyecto,
            "cliente": proyecto.cliente,
            "numero_cotizacion": proyecto.numero_cotizacion,
            "es_prioritario": proyecto.es_prioritario,
            "estado": proyecto.estado,
            "fecha_inicio": proyecto.fecha_inicio,
            "fecha_fin": proyecto.fecha_fin,
            "orden_compra": proyecto.orden_compra,
            "factura": proyecto.factura,
            "id_encargado": proyecto.id_encargado,
            "presupuesto": float(proyecto.presupuesto or 0.0),
            "costo_ejecutado": float(proyecto.costo_ejecutado or 0.0),
            "fecha_actualizacion_costo": proyecto.fecha_actualizacion_costo.isoformat() if proyecto.fecha_actualizacion_costo else None
        }
        response = supabase.table("proyecto").insert(datos).execute()
        return response
    except Exception as e:
        print(f"Error al insertar en Supabase: {e}")
        return None

# --- FUNCIÓN 2: ACTUALIZAR (PATCH) ---
def actualizar_detalles_supabase(proyecto_id, nuevos_datos):
    proyecto_id = int(proyecto_id)
    print(f"DEBUG: Actualizando Supabase ID {proyecto_id} con: {nuevos_datos}")
    
    # Limpieza: Si la fecha es un string vacío "", la convertimos a None
    for clave in ["fecha_inicio", "fecha_fin"]:
        if clave in nuevos_datos and not nuevos_datos[clave]:
            nuevos_datos[clave] = None

    print(f"Enviando a Supabase ID: {proyecto_id} | Datos: {nuevos_datos}")
    
    try:
        print("Intentando ejecutar el UPDATE...")
        response = supabase.table("proyecto").update(nuevos_datos).eq("id", proyecto_id).execute()
        # Imprimimos la respuesta completa del servidor
        print("DEBUG: Respuesta de Supabase:", response.data) 
        return response
    except Exception as e:
        print(f"ERROR CAPTURADO EN LA EJECUCIÓN: {e}")
        return None
        
# --- FUNCIÓN PARA BITÁCORA (POST) ---
def enviar_a_supabase_bitacora(bitacora_entrada):
    """
    Envía una nueva entrada de bitácora a Supabase.
    Recibe un objeto con los atributos necesarios.
    """
    print("--- INTENTANDO CREAR EN SUPABASE: BITÁCORA ---")
    try:
        # Preparamos el diccionario de datos
        datos = {
            "tarea": bitacora_entrada.tarea,
            "anotacion": bitacora_entrada.anotacion,
            "id_encargado": int(bitacora_entrada.id_encargado),
            "usuario": bitacora_entrada.usuario,
            # Supabase insertará la fecha automáticamente si tienes 
            # 'created_at' configurado como 'now()' en la tabla, 
            # si no, puedes agregar: "fecha_registro": datetime.now().isoformat()
        }
        
        # Ejecutamos la inserción en la tabla 'bitacora_tareas'
        # Asegúrate de que el nombre de la tabla coincida con el de tu base de datos
        response = supabase.table("bitacora_tareas").insert(datos).execute()
        
        print("Éxito al insertar en Supabase")
        return response
    except Exception as e:
        print(f"Error al insertar bitácora en Supabase: {e}")
        return None    
    

       
# En db_supabase.py
from sqlalchemy.orm import joinedload # <--- ¡IMPORTANTE!

def obtener_datos_para_exportar():
    try:
        if USAR_SUPABASE:
            return obtener_bitacora_supabase()
        else:
            from app import BitacoraTareas, app
            with app.app_context():
                # USAMOS joinedload: Esto trae la bitácora Y el encargado en 1 sola consulta.
                datos = BitacoraTareas.query.options(joinedload(BitacoraTareas.encargado))\
                        .order_by(BitacoraTareas.fecha_registro.desc()).all()
                return datos
    except Exception as e:
        print(f"--- ERROR: {e} ---")
        return []
    
from sqlalchemy.orm import joinedload

def obtener_bitacora_supabase():
    try:
        # Hacemos la consulta a la tabla 'bitacora_tareas'
        # Usamos .select('*, encargado(*)') si tienes la relación configurada en Supabase
        response = supabase.table("bitacora_tareas")\
                           .select("*, encargado(nombre)")\
                           .order("fecha_registro", desc=True)\
                           .execute()
        return response.data
    except Exception as e:
        print(f"Error al leer bitácora en Supabase: {e}")
        return []
    
def obtener_proyectos_supabase(finalizados=False):
    """
    Trae los proyectos desde la tabla 'proyecto' en Supabase.
    """
    try:
        # Hacemos la consulta a la tabla 'proyecto'
        # Usamos .select("*, encargado(*)") si tienes la relación configurada en Supabase
        # Si no tienes relaciones configuradas, usa solo "*"
        query = supabase.table("proyecto").select("*")
        
        # Filtro si es necesario
        if finalizados:
            query = query.eq("estado", "archivado")
            
        response = query.execute()
        
        # Retornamos los datos directamente
        return response.data
    except Exception as e:
        print(f"Error al leer proyectos en Supabase: {e}")
        return []


def obtener_datos_proyectos(filtrar_finalizados=False):
    """
    Gestor centralizado para obtener proyectos desde Supabase o Local.
    """
    try:
        if USAR_SUPABASE:
            # Aquí pondrías tu lógica de Supabase (ej. client.table('proyectos').select('*')...)
            return obtener_proyectos_supabase(finalizados=filtrar_finalizados)
        else:
            from app import Proyecto, app
            with app.app_context():
                query = Proyecto.query.options(joinedload(Proyecto.encargado))
                if filtrar_finalizados:
                    query = query.filter_by(estado='archivado')
                return query.all()
    except Exception as e:
        print(f"Error en capa de datos (Proyectos): {e}")
        return []

# --- FUNCIÓN PARA GUARDAR NOTAS EN SUPABASE ---

#USAR_SUPABASE = True
def guardar_nota_supabase(proyecto_id, contenido):
    print(f"--- INTENTANDO GUARDAR NOTA EN SUPABASE: Proyecto {proyecto_id} ---")
    try:
        datos = {
            "proyecto_id": int(proyecto_id),
            "contenido": contenido,
            # 'leido' y 'fecha_creacion' no son obligatorios aquí porque 
            # Supabase los llenará automáticamente con los valores por defecto 
            # (0 y CURRENT_TIMESTAMP) que definiste en tu CREATE TABLE.
        }
        response = supabase.table("notas").insert(datos).execute()
        print("--- ÉXITO: Nota guardada en Supabase ---")
        return response
    except Exception as e:
        print(f"Error al insertar nota en Supabase: {e}")
        return None    

def obtener_notas_supabase(proyecto_id):
    print(f"--- LEYENDO NOTAS DE SUPABASE PARA PROYECTO: {proyecto_id} ---")
    try:
        # Hacemos la consulta a la tabla 'notas' filtrando por proyecto_id
        response = supabase.table("notas")\
                           .select("*")\
                           .eq("proyecto_id", int(proyecto_id))\
                           .order("fecha_creacion", desc=True)\
                           .execute()
        
        # 'response.data' contiene la lista de notas que buscamos
        return response.data
    except Exception as e:
        print(f"Error al leer notas en Supabase: {e}")
        return []
    
def sync_nota_leida_to_supabase(nota_id):
    print(f"--- SINCRONIZANDO NOTA {nota_id} COMO LEÍDA EN SUPABASE ---")
    try:
        response = supabase.table("notas") \
                           .update({"leido": 1}) \
                           .eq("id", nota_id) \
                           .execute()
        print("--- ÉXITO: Nota actualizada en Supabase ---")
        return response
    except Exception as e:
        print(f"Error al actualizar nota en Supabase: {e}")
        return None
    
# En db_supabase.py
def actualizar_entregable_supabase(entregable_id, datos):
    try:
        response = supabase.table("entregable").update(datos).eq("id", entregable_id).execute()
        return response
    except Exception as e:
        print(f"Error en Supabase: {e}")
        return None
    
