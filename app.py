from flask import Flask, render_template, request, redirect, url_for,jsonify, Response
#from notas_logica import tiene_notas_pendientes, guardar_nota_db
from flask_sqlalchemy import SQLAlchemy 
from notas_logica import tiene_notas_pendientes, obtener_notas_db, marcar_como_leido
# ... el resto de tus importaciones ...
import pytz
import os
from sqlalchemy import create_engine
import csv
import io
from datetime import datetime, timezone, timedelta
import time
from sqlalchemy import event
from db_supabase import enviar_a_supabase, enviar_a_supabase_bitacora, obtener_datos_para_exportar
# enviar a supabase ....
from collections import defaultdict
from db_supabase import actualizar_detalles_supabase
from flask import render_template, request, redirect, url_for, flash
from db_supabase import supabase  # Importamos o objeto 'supabase' que criamos no outro arquivo
# Agrégalo junto s tus otros imports al inicio de app.py
from flask import Response, jsonify
from db_supabase import obtener_datos_para_exportar # Importamos tu nuevo gestor
from db_supabase import obtener_datos_proyectos
from db_supabase import USAR_SUPABASE
from db_supabase import guardar_nota_supabase, obtener_notas_supabase, USAR_SUPABASE
from flask import render_template
from notas_logica import obtener_notas_proyecto # Importas la lógica aquí
# O si prefieres: from config import USAR_SUPABASE (pero 'import config' es más seguro)
# Busca esta línea en tu app.py y modifícala:


DATABASE_URL = os.environ.get("DATABASE_URL") or 'sqlite:///database.db'

engine = create_engine(DATABASE_URL)



from notas_logica import (
    tiene_notas_pendientes, 
    guardar_nota_db, 
    obtener_notas_db, 
    marcar_como_leido
)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sistema_limpio.db'
app.secret_key = 'una_clave_muy_secreta_y_larga'
db = SQLAlchemy(app)

from notas_logica import tiene_notas_pendientes, guardar_nota_db, obtener_notas_db, marcar_como_leido

def obtener_hora_cali():
    zona_cali = pytz.timezone('America/Bogota')
    # Quitamos .isoformat() para que sea un objeto datetime puro
    return datetime.now(zona_cali).replace(tzinfo=None)
            

# --- MODELOS ---
class Encargado(db.Model):
    __tablename__ = 'encargado'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    proyectos = db.relationship('Proyecto', back_populates='encargado')

class Proyecto(db.Model):
    __tablename__ = 'proyecto' 
    id = db.Column(db.Integer, primary_key=True)
    nombre_proyecto = db.Column(db.String(100), nullable=False)
    cliente = db.Column(db.String(100), nullable=False)
    numero_cotizacion = db.Column(db.String(50))
    es_prioritario = db.Column(db.Boolean, default=False)
    estado = db.Column(db.String(20), default='activo')
    fecha_inicio = db.Column(db.String(20), nullable=True)
    fecha_fin = db.Column(db.String(20), nullable=True)
    orden_compra = db.Column(db.String(100))
    factura = db.Column(db.String(100))
    id_encargado = db.Column(db.Integer, db.ForeignKey('encargado.id'))
    
    encargado = db.relationship('Encargado', back_populates='proyectos')
    presupuesto = db.Column(db.Float, default=0.0)
    costo_ejecutado = db.Column(db.Float, default=0.0)
    fecha_actualizacion_costo = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    # ------------------------------------------
    # Relaciones únicas (solo una vez)
    entregables = db.relationship('Entregable', backref='proyecto', lazy=True, cascade="all, delete-orphan")
    links = db.relationship('LinkProyecto', backref='proyecto', lazy=True, cascade="all, delete-orphan")

    @property
    def porcentaje_utilidad(self):
    # Usamos 0 si es None para evitar errores
        presupuesto = self.presupuesto or 0
        costo = self.costo_ejecutado or 0
    
        if presupuesto > 0:
           utilidad = ((presupuesto - costo) / presupuesto) * 100
           return round(utilidad, 1)
        return 0.0
    
    


class BitacoraTareas(db.Model):
    __tablename__ = 'bitacora_tareas'
    id = db.Column(db.Integer, primary_key=True)
    tarea = db.Column(db.String(100), nullable=False)

    anotacion = db.Column(db.Text)
    fecha_registro = db.Column(db.DateTime, default=obtener_hora_cali)
    usuario = db.Column(db.String(50))
    # Sin relaciones, sin porcentajes. Solo datos puros.
    id_encargado = db.Column(db.Integer, db.ForeignKey('encargado.id'))
    encargado = db.relationship('Encargado')

class Entregable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey('proyecto.id'), nullable=False)
    informe_tecnico = db.Column(db.Boolean, default=False)
    costo_preliminar = db.Column(db.Boolean, default=False)
    fecha_costo_preliminar = db.Column(db.Date, nullable=True)
    costo_final = db.Column(db.Boolean, default=False)
    acta_firmada = db.Column(db.Boolean, default=False)
    fecha_acta_firmada = db.Column(db.Date, nullable=True)
    notas_gestion_acta = db.Column(db.Text, nullable=True)

class LinkProyecto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey('proyecto.id'), nullable=False)
    nombre_link = db.Column(db.String)
    url = db.Column(db.String(500))
    
    
class ConfiguracionGlobal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url_cotizaciones = db.Column(db.String(500))
    url_informes = db.Column(db.String(500))
    url_remisiones = db.Column(db.String(500)) 


def calcular_progreso(proyecto):
    progreso = 0
    ent = proyecto.entregables[0] if proyecto.entregables else None
    
    if ent:
        # Cada uno vale 20%
        if ent.costo_preliminar: progreso += 20
        if ent.costo_final: progreso += 20
        if ent.acta_firmada: progreso += 20
        if ent.informe_tecnico: progreso += 20
        
    # Los links valen 5% cada uno (máximo 4 links = 20%)
    num_links = len(proyecto.links)
    progreso += min(num_links * 5, 20)
    
    return progreso

# --- FUNCIÓN PRECARGA ---
def precargar_encargados():
    nombres = ["Auxiliar 1", "Auxiliar 2", "Auxiliar 3", "Auxiliar 4"]
    for nombre in nombres:
        if not Encargado.query.filter_by(nombre=nombre).first():
            db.session.add(Encargado(nombre=nombre))
    db.session.commit()

# 4. INICIALIZACIÓN (Mueve tu bloque AQUÍ, debajo de las clases)
with app.app_context():
    db.create_all()
    precargar_encargados()
    if not ConfiguracionGlobal.query.first():
        db.session.add(ConfiguracionGlobal())
        db.session.commit()

@app.after_request
def add_header(response):
    # Esto le dice a cualquier navegador: "No guardes nada, busca siempre lo nuevo"
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# --- RUTAS ---

@app.route('/', methods=['GET', 'POST'])
def index():
    proyectos_agrupados = defaultdict(list)

    if request.method == 'POST':
        try:
            encargado_id = request.form.get('id_encargado')
            nuevo = Proyecto(
                nombre_proyecto=request.form['nombre'],
                cliente=request.form['cliente'],
                numero_cotizacion=request.form.get('numero_cotizacion'),
                id_encargado=int(encargado_id) if encargado_id and encargado_id.isdigit() else None
            )
            db.session.add(nuevo)
            db.session.commit()

            db.session.add(Entregable(proyecto_id=nuevo.id))
            db.session.commit()

            # LLAMADA AL PUENTE
            from db_supabase import enviar_a_supabase
            enviar_a_supabase(nuevo)

            flash("Proyecto guardado correctamente.")

        except Exception as e:
            db.session.rollback()
            flash(f"Error al guardar: {e}")
            print(f"Error específico: {e}")

        return redirect('/')
    
    # Lógica de carga para GET
    config = ConfiguracionGlobal.query.first()

    # 1. Lógica de filtrado por encargado
    id_filtro = request.args.get('id_encargado')
    query = Proyecto.query.filter_by(estado='activo')
    if id_filtro and id_filtro.isdigit():
        query = query.filter_by(id_encargado=int(id_filtro))
    
    proyectos = query.all()

    # 2. Cálculo de progreso y agrupación
    for p in proyectos:
        entregable = Entregable.query.filter_by(proyecto_id=p.id).first()
        progreso_links = len(p.links[:3]) * 7 if p.links else 0
        progreso_ent = 0

        if entregable:
            items = [entregable.costo_preliminar, entregable.costo_final, 
                     entregable.acta_firmada, entregable.informe_tecnico]
            progreso_ent = sum(1 for x in items if x) * 19.75
        
        p.progreso_total = progreso_links + progreso_ent
        proyectos_agrupados[p.cliente].append(p)

    # 3. Obtener bitácora
    registros = BitacoraTareas.query.order_by(BitacoraTareas.fecha_registro.desc()).limit(10).all()

    # 4. RETORNO FINAL
    return render_template('index.html', 
                           proyectos_agrupados=proyectos_agrupados, 
                           encargados=Encargado.query.all(),
                           config=config,
                           registros_recientes=registros)





@app.route('/registrar_bitacora', methods=['POST'])
def registrar_bitacora():
    # 1. Capturamos los datos del formulario (esto no cambia)
    # Creamos un objeto similar a lo que espera tu lógica
    class NuevaEntrada:
        def __init__(self, form):
            self.tarea = form.get('tarea')
            self.anotacion = form.get('anotacion')
            self.id_encargado = int(form.get('id_encargado') or 0)
            self.usuario = "Auxiliar"
            # Asegúrate de incluir los campos que tu tabla requiera

    nueva_entrada = NuevaEntrada(request.form)

    # 2. Guardado Local (SQLAlchemy) - ¡Sigue activo para pruebas!
    db_registro = BitacoraTareas(
        tarea=nueva_entrada.tarea,
        anotacion=nueva_entrada.anotacion,
        id_encargado=nueva_entrada.id_encargado,
        usuario=nueva_entrada.usuario
    )
    db.session.add(db_registro)
    db.session.commit()

    # 3. Guardado en Supabase (Usando TU metodología)
    # Aquí es donde ocurre la magia: tu archivo db_supabase.py lo gestiona
    try:
        # Nota: Ajusta 'bitacora_tare.as' al nombre real de tu tabla en Supabase
        enviar_a_supabase_bitacora(nueva_entrada) 
        print("Tarea guardada con éxito en Supabase")
    except Exception as e:
        print(f"Error al guardar en Supabase: {e}")
        
    return redirect('/')

    

@app.route('/detalle/<int:id>', methods=['GET', 'POST'])
def detalle_proyecto(id):
    
    # --- 1. CAPA DE RESCATE ---
    proyecto = Proyecto.query.filter_by(id=id).first()

    if not proyecto:
        from db_supabase import supabase
        response = supabase.table("proyecto").select("*").eq("id", id).execute()
        
        if response.data:
            data = response.data[0]
            # Creamos el proyecto localmente al vuelo
            proyecto = Proyecto(
                id=data['id'],
                nombre_proyecto=data['nombre_proyecto']
            )
            db.session.add(proyecto)
            db.session.commit()
            print(f"DEBUG: Proyecto {id} rescatado de Supabase a Local")
        else:
            return "Proyecto no encontrado", 404
    # --------------------------

    if request.method == 'POST':
        print(f"DEBUG: RECIBÍ UN POST. Form: {request.form.to_dict()}")

    db.session.expire_all()
    
    # Aquí aplicamos la corrección: usamos el proyecto que ya tenemos arriba
    db.session.refresh(proyecto)

    # Creamos el link de PRUEBA si no existe ninguno
    if not LinkProyecto.query.filter_by(proyecto_id=id).first():
        link_temp = LinkProyecto(proyecto_id=id, nombre_link="PRUEBA", url="https://www.google.com")
        db.session.add(link_temp)
        db.session.commit()

    entregable = Entregable.query.filter_by(proyecto_id=id).first()
    config = ConfiguracionGlobal.query.first()
    links = LinkProyecto.query.filter_by(proyecto_id=id).all()

    # Procesamiento de formularios POST
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        print(f"DEBUG: form_type recibido es: {form_type}") # <--- AÑADE ESTA LÍNEA
        
        if form_type == 'admin':
            print(f"DEBUG: Entrando en bloque de gestión. ¿Entregable existe?: {entregable is not None}") # <--- AÑADE EST
            fecha_inicio = request.form.get('fecha_inicio')
            fecha_fin = request.form.get('fecha_fin')  

            # Actualización Local (SQLite)
            proyecto.fecha_inicio = fecha_inicio if fecha_inicio else None
            proyecto.fecha_fin = fecha_fin if fecha_fin else None
            proyecto.orden_compra = request.form.get('orden_compra')
            proyecto.factura = request.form.get('factura')
            proyecto.estado = request.form.get('estado')
            db.session.commit()

            # Actualización en Supabase
            datos_supabase = {
                "fecha_inicio": proyecto.fecha_inicio or None,
                "fecha_fin": proyecto.fecha_fin or None,
                "orden_compra": proyecto.orden_compra,
                "factura": proyecto.factura,
                "estado": proyecto.estado
            } 
            datos_supabase = {k: v for k, v in datos_supabase.items() if v is not None}
            
            from db_supabase import actualizar_detalles_supabase
            actualizar_detalles_supabase(proyecto.id, datos_supabase)

            return redirect(url_for('detalle_proyecto', id=proyecto.id))
            
        elif form_type == 'gestion': 
            print("DEBUG: Entré al bloque de gestión")

            if not entregable:    
                entregable = Entregable(proyecto_id=id)
                db.session.add(entregable)
                db.session.commit()
            
            entregable.costo_preliminar = 'costo_preliminar' in request.form
            entregable.costo_final = 'costo_final' in request.form
            entregable.acta_firmada = 'acta_firmada' in request.form
            entregable.informe_tecnico = 'informe_tecnico' in request.form
            entregable.notas_gestion_acta = request.form.get('notas_gestion_acta')
            
            if request.form.get('fecha_costo_preliminar'):
                entregable.fecha_costo_preliminar = datetime.strptime(request.form.get('fecha_costo_preliminar'), '%Y-%m-%d')
            if request.form.get('fecha_acta_firmada'):
                entregable.fecha_acta_firmada = datetime.strptime(request.form.get('fecha_acta_firmada'), '%Y-%m-%d')

            db.session.commit()
            print("DEBUG: Commit local hecho. Intentando Supabase...")

            # --- SINCRONIZACIÓN CORREGIDA ---
            try:
                from db_supabase import supabase
                print("DEBUG: --- INTENTANDO CONEXIÓN SUPABASE ---")
                
                # Convertimos las fechas directamente aquí de forma segura
                fecha_costo = entregable.fecha_costo_preliminar.strftime('%Y-%m-%d') if entregable.fecha_costo_preliminar else None
                fecha_acta = entregable.fecha_acta_firmada.strftime('%Y-%m-%d') if entregable.fecha_acta_firmada else None
                
                datos_entregable = {
                    "informe_tecnico": entregable.informe_tecnico,
                    "costo_preliminar": entregable.costo_preliminar,
                    "fecha_costo_preliminar": fecha_costo,
                    "costo_final": entregable.costo_final,
                    "acta_firmada": entregable.acta_firmada,
                    "fecha_acta_firmada": fecha_acta,
                    "notas_gestion_acta": entregable.notas_gestion_acta
                }

                print(f"DEBUG: Datos a enviar: {datos_entregable}")
                supabase.table("entregable").upsert({"proyecto_id": id, **datos_entregable}).execute()
                print("DEBUG: ¡ÉXITO! Entregable sincronizado con Supabase.")
            except Exception as e:
                print(f"DEBUG: --- ERROR CAPTURADO EN SUPABASE: {e} ---")

        elif form_type == 'nuevo': 
            nuevo_nombre = request.form.get('nuevo_entregable')
            if nuevo_nombre:
               nuevo = Entregable(proyecto_id=id, nombre_entregable=nuevo_nombre)
               db.session.add(nuevo)
               
        db.session.commit()
        return redirect(f'/detalle/{id}')
        
    porcentaje = calcular_progreso(proyecto)
    
    return render_template('detalle.html', 
                           proyecto=proyecto,
                           config=config,
                           links=links,
                           porcentaje=porcentaje)

@app.route('/actualizar_links_globales', methods=['POST'])
def actualizar_links_globales():
    config = ConfiguracionGlobal.query.first()
    if not config:
        config = ConfiguracionGlobal()
        db.session.add(config)
    
    # 1. Definimos las variables AQUÍ (Esto soluciona el error)
    url_cot = request.form.get('url_cotizaciones')
    url_inf = request.form.get('url_informes')
    url_rem = request.form.get('url_remisiones')
    
    # 2. Asignamos al objeto local
    config.url_cotizaciones = url_cot
    config.url_informes = url_inf
    config.url_remisiones = url_rem
    
    # FORZAR EL GUARDADO LOCAL
    db.session.commit()
   
    try:
        from db_supabase import supabase 
        
        datos_supabase = {
            "id": 1, # IMPORTANTE: el ID debe ir aquí para el upsert
            "url_cotizaciones": url_cot,
            "url_informes": url_inf,
            "url_remisiones": url_rem
        }
        
        print(f"DEBUG: Enviando a Supabase: {datos_supabase}") # <--- ESTO ES CLAVE
        
        response = supabase.table("configuracion_global").upsert(datos_supabase).execute()
        print(f"DEBUG: Respuesta Supabase: {response}") # <--- ESTO NOS DIRÁ EL ERROR
        
        print("Éxito: Links sincronizados en Supabase")
        
        supabase.table("configuracion_global").upsert(datos_supabase).execute()
        
        print("Éxito: Links sincronizados en Supabase")
    except Exception as e:
        print(f"Error sincronizando con Supabase: {e}")
    
    return redirect(request.referrer or '/')
       

@app.route('/agregar_link_proyecto/<int:id>', methods=['POST'])
def agregar_link_proyecto(id):
    print(f"DEBUG: El formulario me envió el ID: {id}")
    print(f"DEBUG: Ruta recibida con ID: {id}")
    print(f"DEBUG: Datos del form: {request.form}")
    
    nombre = request.form.get('nombre_link')
    url = request.form.get('url')
    
    if nombre and url:
        # 1. Guardado Local
        nuevo_link = LinkProyecto(proyecto_id=id, nombre_link=nombre, url=url)
        db.session.add(nuevo_link)
        db.session.commit() # Esto dispara tu 'after_commit'
        
        # 2. Sincronización con Supabase
        try:
            from db_supabase import supabase
            
            # Nota: Al insertar en Supabase, no necesitamos un ID fijo 
            # porque cada link es un registro nuevo (será autoincremental en la nube)
            datos_supabase = {
                "proyecto_id": id,
                "nombre_link": nombre,
                "url": url
            }
            
            supabase.table("link_proyecto").insert(datos_supabase).execute()
            print("Éxito: Link de proyecto sincronizado en Supabase")
            
        except Exception as e:
            print(f"DEBUG DETALLADO: {e}") 
            flash(f"Error sincronizando: {e}", "danger")
            
    return redirect(f'/detalle/{id}')


@app.route('/actualizar_todos_los_links/<int:id>', methods=['POST'])
def actualizar_todos_los_links(id):
    links = LinkProyecto.query.filter_by(proyecto_id=id).all()
    
    
    
    for link in links:
        # Recuperamos los datos del formulario usando el ID del link
        nuevo_nombre = request.form.get(f'nombre_{link.id}')
        nueva_url = request.form.get(f'url_{link.id}')

        
        # Actualizamos solo si los datos existen
        if nuevo_nombre: link.nombre_link = nuevo_nombre
        if nueva_url: link.url = nueva_url
        
    db.session.commit()
    return redirect(f'/detalle/{id}')
    


# ... importaciones y db = SQLAlchemy(app) ...


@app.route('/archivados')
def archivados():
    # Asegúrate de usar 'archivado' para que coincida con tu botón
    proyectos_finalizados = Proyecto.query.filter_by(estado='archivado').all()
    return render_template('archivados.html', proyectos=proyectos_finalizados)

# --- RUTA DE FINALIZAR ---
@app.route('/finalizar/<int:id>')
def finalizar_proyecto(id):
    proyecto = Proyecto.query.get_or_404(id)
    proyecto.estado = 'archivado' 
    db.session.commit()

    for intento in range(3): # Intentar 3 veces si falla
        try:
            cotizacion = str(proyecto.numero_cotizacion)
            supabase.table('proyecto').update({'estado': 'archivado'}).eq('numero_cotizacion', cotizacion).execute()
            print(f"ÉXITO: Proyecto {cotizacion} actualizado.")
            break # Si sale bien, paramos el bucle
        except Exception as e:
            print(f"Intento {intento+1} fallido: {e}")
            time.sleep(2) # Esperar un poco antes de reintentar
            
    return redirect('/')

@app.route('/actualizar_costos/<int:id>', methods=['POST'])
def actualizar_costos(id):
    proyecto = Proyecto.query.get_or_404(id)
    
    # 1. Obtenemos los valores del formulario
    nuevo_presupuesto = float(request.form.get('presupuesto') or 0.0)
    nuevo_costo = float(request.form.get('costo_ejecutado') or 0.0)
    
    # 2. Actualizamos el objeto local (esto mantiene tu base local al día)
    proyecto.presupuesto = nuevo_presupuesto
    proyecto.costo_ejecutado = nuevo_costo
    db.session.commit()
    
    # 3. CREAMOS EL DICCIONARIO QUE LA FUNCIÓN EXISTENTE ESPERA
    datos_para_supabase = {
        'presupuesto': nuevo_presupuesto,
        'costo_ejecutado': nuevo_costo
    }
    
    # 4. LLAMAMOS A LA FUNCIÓN TAL CUAL ESTÁ DEFINIDA
    actualizar_detalles_supabase(proyecto.id, datos_para_supabase)
    
    return redirect(url_for('detalle_proyecto', id=id))

@app.route('/exportar_bitacora_csv')
def exportar_bitacora_csv():
    registros = obtener_datos_para_exportar()
    
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(['Encargado', 'Tarea', 'Anotación', 'Fecha', 'Hora'])
    
    nombres_encargados = {
        1: 'Auxiliar 1',
        2: 'Auxiliar 2',
        3: 'Auxiliar 3',
        4: 'Auxiliar 4',
    }
    
    # Definimos la zona horaria una sola vez fuera del bucle
    colombia_tz = timezone(timedelta(hours=-5))

    for r in registros:
        if isinstance(r, dict): # Viene de Supabase
            id_enc = r.get('id_encargado')
            nombre = nombres_encargados.get(id_enc, 'Sin asignar')
            tarea = r.get('tarea', '')
            anotacion = r.get('anotacion', '')
            fecha_str = r.get('fecha_registro')
            
            # Aplicamos zona horaria
            
            if fecha_str:
                fecha_utc = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
                if fecha_utc.tzinfo is None:
                    fecha_utc = fecha_utc.replace(tzinfo=timezone.utc)
                fecha = fecha_utc.astimezone(colombia_tz)
            else:
                fecha = datetime.now(colombia_tz)

            
        else: # Viene de Local
            nombre = r.encargado.nombre if r.encargado else 'Sin asignar'
            tarea = r.tarea
            anotacion = r.anotacion
            # Si el objeto local no tiene zona horaria, la asignamos
            fecha = r.fecha_registro.replace(tzinfo=colombia_tz) if r.fecha_registro.tzinfo is None else r.fecha_registro.astimezone(colombia_tz)
            
        writer.writerow([nombre, tarea, anotacion, fecha.strftime('%Y-%m-%d'), fecha.strftime('%H:%M:%S')])
    
    return Response(si.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=bitacora_tareas.csv"})



@app.route('/exportar_csv')
def exportar_csv():
    proyectos = obtener_datos_proyectos(filtrar_finalizados=False)
    
    si = io.StringIO()
    writer = csv.writer(si)
    
    # 1. Agregamos las nuevas columnas al encabezado
    writer.writerow([
        'Cliente', 'Nombre Proyecto', 'N° Cotización', 'Presupuesto', 
        'Costo Ejecutado', 'Orden de Compra', 'Utilidad', 'Encargado', 
        'Fecha Inicio', 'Fecha Fin', 'Estado', 'Factura'
    ])
    
    for p in proyectos:
        # 2. Extracción segura (Diccionario para Supabase / Objeto para Local)
        if isinstance(p, dict):
            cliente = p.get('cliente')
            nombre = p.get('nombre_proyecto')
            cot = p.get('numero_cotizacion') or 'S/C'
            presupuesto = float(p.get('presupuesto') or 0)
            costo = float(p.get('costo_ejecutado') or 0)
            orden = p.get('orden_compra') or 'S/A'
            encargado = p.get('encargado', {}).get('nombre') if p.get('encargado') else 'Sin asignar'
            fecha_i = p.get('fecha_inicio') or 'N/A'
            fecha_f = p.get('fecha_fin') or 'N/A'
            estado = p.get('estado') or 'N/A'
            factura = p.get('factura') or 'N/A'
        else:
            cliente = p.cliente
            nombre = p.nombre_proyecto
            cot = p.numero_cotizacion or 'S/C'
            presupuesto = float(p.presupuesto or 0)
            costo = float(p.costo_ejecutado or 0)
            orden = p.orden_compra or 'S/A'
            encargado = p.encargado.nombre if p.encargado else 'Sin asignar'
            fecha_i = p.fecha_inicio.strftime('%Y-%m-%d') if p.fecha_inicio else 'N/A'
            fecha_f = p.fecha_fin.strftime('%Y-%m-%d') if p.fecha_fin else 'N/A'
            estado = p.estado or 'N/A'
            factura = p.factura or 'N/A'

        utilidad = presupuesto - costo
        
        # 3. Escribimos la fila completa
        writer.writerow([
            cliente, nombre, cot, presupuesto, costo, orden, 
            utilidad, encargado, fecha_i, fecha_f, estado, factura
        ])
    
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=reporte_proyectos_total.csv"}
    )


@app.route('/eliminar/<int:id>', methods=['POST'])
def eliminar_proyecto(id):
    # Obtenemos los datos del formulario
    usuario = request.form.get('usuario')
    palabra = request.form.get('palabra_clave')
    
    proyecto = Proyecto.query.get_or_404(id)
    
    # Validamos que la palabra clave sea exacta
    if palabra == "CONFIRMAR":
        # 1. Registro de auditoría (se guardará en el servidor)
        log_mensaje = f"[{datetime.now()}] Proyecto '{proyecto.nombre_proyecto}' (ID: {id}) eliminado por: {usuario}\n"
        with open("log_eliminaciones.txt", "a") as f:
            f.write(log_mensaje)
        
        # 2. Eliminación de la base de datos
        db.session.delete(proyecto)
        db.session.commit()
        
        flash("El proyecto fue eliminado exitosamente.")
    else:
        flash("Error: La palabra clave no es correcta. No se realizó ninguna acción.")
        
    return redirect(url_for('index'))

@app.route('/alertas')
def alertas():
    # Buscamos proyectos 'archivado' donde el acta NO está firmada
    pendientes = Proyecto.query.join(Entregable).filter(
        Proyecto.estado == 'archivado',
        Entregable.acta_firmada == False
    ).all()
    
    return render_template('alertas.html', proyectos=pendientes)

from sqlalchemy.orm import joinedload # Asegúrate de importar esto arriba

@app.route('/mapa')
def mapa_proyectos():
    # Solo buscamos proyectos que NO estén archivados
    proyectos = Proyecto.query.filter(Proyecto.estado != 'archivado')\
                             .options(joinedload(Proyecto.encargado))\
                             .all()
    
    
    db.session.expire_all()
    proyectos_data = []                         
    for p in proyectos:

        
        estado = tiene_notas_pendientes(p.id)
        p.tiene_pendientes = tiene_notas_pendientes(p.id)
        proyectos_data.append({
            'nombre_proyecto': p.nombre_proyecto,
            'encargado': p.encargado,
            'porcentaje_utilidad': p.porcentaje_utilidad,
            'id': p.id,
            'tiene_pendientes': estado
        })
    
    
    return render_template('mapa.html', proyectos=proyectos_data)




from flask import request, jsonify
# Cámbialo de esto:
# from notas_logica import ..., borrar_base_de_dato

# A esto (agregando la 's' al final):
# from notas_logica import guardar_nota_db, obtener_notas_db, marcar_como_leido, borrar_base_de_datos

@app.route('/notas/<int:proyecto_id>', methods=['GET', 'POST'])
def gestionar_notas(proyecto_id):
    # 1. Lógica para cuando el usuario envía el formulario (POST)
    if request.method == 'POST':
        contenido = request.form.get('contenido', '')
        print(f"--- TRUCO RASTREADOR: Recibiendo contenido para proyecto {proyecto_id}: {contenido} ---")
        
        if USAR_SUPABASE:
            guardar_nota_supabase(proyecto_id, contenido)
        else:
            guardar_nota_db_local(proyecto_id, contenido)
        
        # Redirigimos para recargar la página y limpiar el formulario
        return jsonify({"status": "success", "mensaje": "Nota guardada correctamente"})



    # 2. Lógica para cuando el usuario simplemente entra a ver (GET)
    if USAR_SUPABASE:
        lista_notas = obtener_notas_supabase(proyecto_id)
    else:
        lista_notas = obtener_notas_db(proyecto_id)
        
    # Renderizamos la página enviando la lista de notas
    return jsonify(lista_notas)
    
# En tu función de creación de tabla, añade la columna 'leido'

@app.route('/reset-sistema')
def reset():
    from notas_logica import borrar_base_de_datos
    borrar_base_de_datos()
    return "Base de datos eliminada. Reinicia el servidor para empezar de cero."

@app.route('/notas/<int:proyecto_id>')
def ver_notas(proyecto_id):

    # Aquí está el cambio clave:
    if USAR_SUPABASE:
        lista_notas = obtener_notas_supabase(proyecto_id) # Debes crear/usar esta función
    else:
        lista_notas = obtener_notas_db(proyecto_id)

    # Debug: ¿Cuántas notas encontró realmente?
    print(f"--- NOTAS RECUPERADAS: {len(lista_notas)} ---")

    return render_template('notas_proyecto.html', notas=lista_notas, proyecto_id=proyecto_id)


    template_path = os.path.join(app.root_path, 'templates', 'notas.html')
    print(f"--- FLASK ESTÁ BUSCANDO EL HTML AQUÍ: {template_path} ---")

    return render_template('notas.html', notas=lista_notas, proyecto_id=proyecto_id)
    

def verificar_si_quedan_pendientes(proyecto_id):
    # Esto es una lógica genérica para Supabase. 
    # Asegúrate de usar la variable 'supabase' que tengas definida en tu proyecto
    response = supabase.table("notas") \
                       .select("id", count='exact') \
                       .eq("proyecto_id", proyecto_id) \
                       .eq("leido", 0) \
                       .execute()
    

    print(f"DEBUG: Quedan {response.count} notas pendientes") # Mira esto en la terminal
    # Devuelve True si la cuenta es mayor a 0, False en caso contrario
    return response.count > 0






@app.route('/marcar-leido/<int:nota_id>/<int:proyecto_id>')
def marcar_leido_route(nota_id, proyecto_id):
    # Llamamos a la función lógica que ahora nos dice si quedan pendientes
    print(f"DEBUG: Intentando marcar nota {nota_id} como leída.")
    
    marcar_como_leido(nota_id)
    # 2. CALCULO: ¿Quedan pendientes en este proyecto?
    #proyecto_id = obtener_proyecto_por_nota(nota_id) # Debes obtener el ID del proyecto
    notas_pendientes = verificar_si_quedan_pendientes(proyecto_id) 
    
    # 3. Devuelve al frontend el estado actual
    return jsonify({
        "status": "success",
        "tiene_pendientes": notas_pendientes # True si quedan, False si ya no
    })




# Esta función se ejecutará automáticamente tras cada commit
@event.listens_for(db.session, 'after_commit')
def receive_after_commit(session):

    modelos_manuales = (ConfiguracionGlobal, LinkProyecto)

    # Aquí puedes añadir lógica para identificar qué se guardó
    # Por ahora, una llamada simple de aviso a la nube
    for obj in session.new.union(session.dirty):
       
        if isinstance(obj, modelos_manuales):
           continue

        print(f"Sincronizando automáticamente: {obj}")
    # enviar_a_supabase(...)

@app.route('/exportar_notas/<int:proyecto_id>')
def exportar_notas_csv(proyecto_id):
    # 1. Consultamos a Supabase
    response = supabase.table("notas").select("*").eq("proyecto_id", proyecto_id).execute()
    notas = response.data
    
    # 2. Creamos el archivo CSV en memoria
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Contenido', 'Fecha']) # Encabezados
    
    for nota in notas:
        cw.writerow([nota['id'], nota['contenido'], nota['fecha_creacion']])
        
    # 3. Retornamos la respuesta como un archivo descargable
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=notas_proyecto_{proyecto_id}.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/imprimir-notas/<int:proyecto_id>')
def ver_notas_proyecto(proyecto_id):
    # Aquí obtienes las notas (de Supabase o donde las tengas)
    notas = obtener_notas_supabase(proyecto_id) 
    # Renderizas un nuevo archivo HTML llamado 'notas_proyecto.html'
    return render_template('notas_proyecto.html', notas=notas, proyecto_id=proyecto_id)

# 2. RUTA PARA TU PANEL FLOTANTE (La que usa tu JS en el mapa)
@app.route('/api/notas/<int:proyecto_id>')
def obtener_notas_json(proyecto_id):
    if USAR_SUPABASE:
        lista_notas = obtener_notas_supabase(proyecto_id)
    else:
        lista_notas = obtener_notas_db(proyecto_id)
    return jsonify(lista_notas)

# Esta ruta se queda igual para que tu mapa (JS) siga funcionando
@app.route('/notas/<int:proyecto_id>', methods=['GET', 'POST'])
def manejar_notas(proyecto_id):
    if request.method == 'POST':
        # ... tu lógica de guardar ...
        return jsonify({"status": "success"})
    else:
        # Esta es la que tu JS usa para el panel flotante
        notas = obtener_notas_proyecto(proyecto_id)
        return jsonify(notas)

# Esta ruta es la nueva para el panel (solo JSON)
@app.route('/data/notas/<int:proyecto_id>')
def obtener_datos_panel(proyecto_id):
    lista_notas = obtener_notas_supabase(proyecto_id)
    return jsonify(lista_notas)

import io
import csv
from flask import Response

@app.route('/exportar_finalizados_csv')
def exportar_finalizados_csv():

    try:
        # Ahora sí, al importar 'supabase', esta línea debería funcionar
        
        response = supabase.table('proyecto')\
                           .select('*')\
                           .eq('estado', 'archivado')\
                           .order('fecha_fin', desc=True)\
                           .execute()

        proyectos = response.data 
        print(f"DEBUG: Se encontraron {len(proyectos)} proyectos archivados.")
    except Exception as e:
        return f"Error al conectar con Supabase: {e}", 500
    # Consultamos a Supabase
    #response = supabase.table('proyecto').select('*').eq('estado', 'archivado').execute()
    #response = supabase.table('proyecto').select('*').execute()


    verificar_si_quedan_pendientes
    print(f"Registros encontrados: {len(response.data)}")
    
    proyectos = response.data 

    
    si = io.StringIO()
    writer = csv.writer(si)
    
    # Encabezados
    writer.writerow(['Cliente', 'Nombre Proyecto', 'N° Cotización', 'Presupuesto', 'Costo Ejecutado', 'Orden de Compra', 'Utilidad', 'Fecha Finalizado'])

    for p in proyectos:
        presupuesto = p.get('presupuesto') or 0
        costo = p.get('costo_ejecutado') or 0
        writer.writerow([
            p.get('cliente'),
            p.get('nombre_proyecto'),
            p.get('numero_cotizacion') or 'S/C',
            presupuesto,
            costo,
            p.get('orden_compra') or 'S/A',
            presupuesto - costo,
            p.get('fecha_fin') or 'S/F'
        ])
    
    output = si.getvalue()
    si.close()

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=reporte_proyectos_finalizados.csv"}
    )

import csv
from io import StringIO
from flask import Response

@app.route('/exportar-activos-csv')
def exportar_activos_csv():
    # Si consultas directamente a Supabase o a tu ORM local:
    # Ejemplo con Supabase:
    response = supabase.table("proyecto").select("*").neq("estado", "archivado").execute()
    proyectos = response.data
    
    # Crear el archivo CSV en memoria
    def generate():
        data = StringIO()
        writer = csv.writer(data)
        
        # Escribir encabezados basados en tus columnas
        writer.writerow(['ID', 'Nombre Proyecto', 'Cliente', 'Encargado', 'Fecha Inicio', 'Fecha Fin', 'Estado', 'Presupuesto', 'Costo Ejecutado'])
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)
        
        # Escribir filas de proyectos activos
        for p in proyectos:
            writer.writerow([
                p.get('id'),
                p.get('nombre_proyecto'),
                p.get('cliente'),
                p.get('id_encargado'),
                p.get('fecha_inicio'),
                p.get('fecha_fin'),
                p.get('estado'),
                p.get('presupuesto'),
                p.get('costo_ejecutado')
            ])
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)

    return Response(generate(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=proyectos_activos.csv"})



if __name__ == '__main__':
    app.run(debug=True)


# Forzando actualizacion de plantillas en render
