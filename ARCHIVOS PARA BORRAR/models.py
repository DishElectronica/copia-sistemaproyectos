from flask_sqlalchemy import SQLAlchemy

from datetime import datetime

db = SQLAlchemy()

class Proyecto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_proyecto = db.Column(db.String(100), nullable=False)
    cliente = db.Column(db.String(100), nullable=False)
    # ... (aquí irían todos los demás campos que ya tienes en tu proyecto)

    # Relación con las notas
    notas = db.relationship('NotaProyecto', backref='proyecto', lazy=True)

class NotaProyecto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contenido = db.Column(db.Text, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    leido = db.Column(db.Boolean, default=False)
    proyecto_id = db.Column(db.Integer, db.ForeignKey('proyecto.id'), nullable=False)