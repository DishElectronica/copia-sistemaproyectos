from flask import Flask, render_template, request, redirect, url_for, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import csv
import io
from collections import defaultdict

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///proyectos.db'
db = SQLAlchemy(app)

            

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
    fecha_inicio = db.Column(db.String(20), default="Por definir")
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
        if self.presupuesto and self.presupuesto > 0:
            return round(((self.presupuesto - self.costo_ejecutado) / self.presupuesto) * 100, 1)
        return 0


class BitacoraTareas(db.Model):
    __tablename__ = 'bitacora_tareas'
    id = db.Column(db.Integer, primary_key=True)
    tarea = db.Column(db.String(100), nullable=False)
    anotacion = db.Column(db.Text)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
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
    # No necesitamos 'cumplido' necesariamente si cada vez que agregas
    # uno nuevo asumimos que cuenta para el 5% (máximo 3).
    
class ConfiguracionGlobal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url_cotizaciones = db.Column(db.String(500))
    url_informes = db.Column(db.String(500))
    url_costos = db.Column(db.String(500)) 


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

# --- RUTAS ---
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
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
        return redirect('/')
    
    config = ConfiguracionGlobal.query.first()

    # 1. Lógica de filtrado por encargado
    id_filtro = request.args.get('id_encargado')
    query = Proyecto.query.filter_by(estado='activo')
    
    if id_filtro and id_filtro.isdigit():
        query = query.filter_by(id_encargado=int(id_filtro))
    
    proyectos = query.all()
    proyectos_agrupados = defaultdict(list)

    for p in proyectos:
        p.progreso_total = calcular_progreso(p)
        proyectos_agrupados[p.cliente].append(p)
   
    # 2. Cálculo de progreso
    for p in proyectos:

        entregable = Entregable.query.filter_by(proyecto_id=p.id).first()
        progreso_links = len(p.links[:3]) * 7 if p.links else 0
        progreso_ent = 0
        p.progreso_total = calcular_progreso(p)

        if entregable:
            items = [entregable.costo_preliminar, entregable.costo_final, 
                     entregable.acta_firmada, entregable.informe_tecnico]
            progreso_ent = sum(1 for x in items if x) * 19.75
        p.progreso_total = progreso_links + progreso_ent

    # 3. Agrupación por cliente
    proyectos_agrupados = defaultdict(list)
    for p in proyectos:
        proyectos_agrupados[p.cliente].append(p)
        p.progreso_total = calcular_progreso(p)

   # 4. Obtener bitácora
    registros = BitacoraTareas.query.order_by(BitacoraTareas.fecha_registro.desc()).limit(10).all()

    # 5. RETORNO ÚNICO AL FINAL
    return render_template('index.html', 
                           proyectos_agrupados=proyectos_agrupados, 
                           encargados=Encargado.query.all(),
                           config=config,
                           registros_recientes=registros)

    # ... tu código de proyectos ...


from datetime import datetime

@app.route('/registrar_bitacora', methods=['POST'])
def registrar_bitacora():
    nueva_entrada = BitacoraTareas(
        tarea=request.form.get('tarea'),
        anotacion=request.form.get('anotacion'),
        id_encargado=request.form.get('id_encargado'), # Guardamos el ID del encargado
        usuario="Auxiliar" # Puedes cambiarlo según tu sistema de usuarios
    )
    db.session.add(nueva_entrada)
    db.session.commit()
    return redirect('/')

@app.route('/detalle/<int:id>', methods=['GET', 'POST'])
def detalle_proyecto(id):

    db.session.expire_all()

    proyecto = Proyecto.query.get_or_404(id)
    if not LinkProyecto.query.filter_by(proyecto_id=id).first():
       
        link_temp = LinkProyecto(proyecto_id=id, nombre_link="PRUEBA", url="https://www.google.com")
        db.session.add(link_temp)
        db.session.commit()

    entregable = Entregable.query.filter_by(proyecto_id=id).first()
    config = ConfiguracionGlobal.query.first()
    links = LinkProyecto.query.filter_by(proyecto_id=id).all()

   
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        if form_type == 'admin':
            proyecto.fecha_inicio = request.form.get('fecha_inicio')
            proyecto.fecha_fin = request.form.get('fecha_fin')
            proyecto.orden_compra = request.form.get('orden_compra')
            proyecto.factura = request.form.get('factura')
            #proyecto.estado = request.form.get('estado')
            
        elif form_type == 'gestion' and entregable:
            entregable.costo_preliminar = 'costo_preliminar' in request.form
            entregable.costo_final = 'costo_final' in request.form
            entregable.acta_firmada = 'acta_firmada' in request.form
            entregable.informe_tecnico = 'informe_tecnico' in request.form
            entregable.notas_gestion_acta = request.form.get('notas_gestion_acta')
           
           # Captura de fechas
            
            if request.form.get('fecha_costo_preliminar'):
                entregable.fecha_costo_preliminar = datetime.strptime(request.form.get('fecha_costo_preliminar'), '%Y-%m-%d')
            if request.form.get('fecha_acta_firmada'):
                entregable.fecha_acta_firmada = datetime.strptime(request.form.get('fecha_acta_firmada'), '%Y-%m-%d')
            

        elif form_type == 'nuevo': # Para crear un nuevo entregable si no existe
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
    
    
    config.url_cotizaciones = request.form.get('url_cotizaciones')

    # Asignamos directamente los valores del formulario al objeto config
    config.url_cotizaciones = request.form.get('url_cotizaciones')
    config.url_informes = request.form.get('url_informes')
    config.url_costos = request.form.get('url_costos')
    
    # FORZAR EL GUARDADO
    db.session.flush() 
    db.session.commit()
   

    return redirect(request.referrer or '/')       

@app.route('/agregar_link_proyecto/<int:id>', methods=['POST'])
def agregar_link_proyecto(id):
    # Capturamos los datos del formulario
    nombre = request.form.get('nombre_link')
    url = request.form.get('url')
    
    if nombre and url:
        # Creamos el nuevo registro
        nuevo_link = LinkProyecto(proyecto_id=id, nombre_link=nombre, url=url)
        db.session.add(nuevo_link)
        db.session.commit()
    
    # 4. Redirigimos de vuelta a la página de detalle para ver el nuevo link
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
    return redirect('/')

from datetime import datetime # Asegúrate de tener este import arriba

@app.route('/actualizar_costos/<int:id>', methods=['POST'])
def actualizar_costos(id):
    proyecto = Proyecto.query.get_or_404(id)
    
    # Tu lógica actual
    try:
        nuevo_presupuesto = float(request.form.get('Presupuesto', 0))
        nuevo_costo = float(request.form.get('costo_ejecutado', 0))
    except ValueError:
        nuevo_presupuesto = 0
        nuevo_costo = 0
    
    # Asignamos los valores al objeto proyecto
    proyecto.presupuesto = nuevo_presupuesto
    proyecto.costo_ejecutado = nuevo_costo
    
    # --- AQUÍ ESTÁ LA NUEVA LÍNEA PARA LA FECHA ---
    # Esto guardará la fecha y hora exacta del momento en que se procesa el POST
    proyecto.fecha_actualizacion_costos = datetime.now().strftime('%d/%m/%Y %H:%M')
    
    # Guardamos en la base de datos
    db.session.commit()
    
    return redirect(url_for('detalle_proyecto', id=id))

@app.route('/exportar_bitacora_csv')
def exportar_bitacora_csv():
    # Ordena por encargado y luego por fecha
    registros = BitacoraTareas.query.order_by(BitacoraTareas.id_encargado, BitacoraTareas.fecha_registro.desc()).all()
    
    si = io.StringIO()
    writer = csv.writer(si)
    
    # Encabezados
    writer.writerow(['Encargado', 'Tarea', 'Anotación', 'Fecha', 'Hora'])
    
    for r in registros:
        nombre = r.encargado.nombre if r.encargado else 'Sin asignar'
        writer.writerow([nombre, r.tarea, r.anotacion, r.fecha_registro.strftime('%Y-%m-%d'), r.fecha_registro.strftime('%H:%M:%S')])
    
    output = si.getvalue()
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=bitacora_tareas.csv"})

@app.route('/exportar_csv')
def exportar_csv():
    # Obtenemos todos los proyectos activos (puedes ajustar el filtro si solo quieres activos)
    proyectos = Proyecto.query.all()
    
    si = io.StringIO()
    writer = csv.writer(si)
    
    # Encabezados en el orden que solicitaste:
    # Cliente, Nombre Proyecto, N° Cotización, Presupuesto, Orden de Compra, Utilidad, Encargado
    writer.writerow(['Cliente', 'Nombre Proyecto', 'N° Cotización', 'Presupuesto', 'Orden de Compra', 'Utilidad', 'Encargado']),
    
    for p in proyectos:
        # Calculamos la utilidad aquí mismo (Presupuesto - Costo Ejecutado)
        utilidad = (p.presupuesto or 0) - (p.costo_ejecutado or 0),
        fecha = p.fecha_actualizacion_costo.strftime('%Y-%m-%d') if p.fecha_actualizacion_costo else 'S/F'

        writer.writerow([
            p.cliente,
            p.nombre_proyecto,
            p.numero_cotizacion or 'S/C',
            p.presupuesto or 0,
            p.orden_compra or 'S/A', # Asegúrate que este campo exista en tu modelo
            utilidad,
            p.encargado.nombre if p.encargado else 'Sin asignar',
            fecha
        ])
    
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=reporte_proyectos_total.csv"}
    )

@app.route('/exportar_finalizados_csv')
def exportar_finalizados_csv():
    # Filtramos solo los que están finalizados
    proyectos = Proyecto.query.filter_by(estado='archivado').all()
    
    si = io.StringIO()
    writer = csv.writer(si)
    
    # Mismo orden que el reporte de proyectos activos
    
    writer.writerow([
        'Cliente', 'Nombre Proyecto', 'N° Cotización', 'Presupuesto', 
        'Orden de Compra', 'Utilidad', 'Encargado', 'Fecha Finalizado'
    ])

    for p in proyectos:
        utilidad = (p.presupuesto or 0) - (p.costo_ejecutado or 0)
        fecha = p.fecha_fin if p.fecha_fin else 'S/F'
        
        writer.writerow([
            p.cliente,
            p.nombre_proyecto,
            p.numero_cotizacion or 'S/C',
            p.presupuesto or 0,
            p.orden_compra or 'S/A',
            utilidad,
            p.encargado.nombre if p.encargado else 'Sin asignar',
            fecha # Nueva columna
        ])
    
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=reporte_proyectos_finalizados.csv"}
    )

if __name__ == '__main__':
    app.run(debug=True)
#actualizdo