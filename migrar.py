# Crea un archivo nuevo llamado 'migrar.py' y ejecútalo una vez
from app import app, db, Proyecto # Ajusta según tu estructura
from db_supabase import enviar_a_supabase

with app.app_context():
    proyectos = Proyecto.query.all()
    for p in proyectos:
        print(f"Subiendo proyecto: {p.nombre_proyecto}")
        enviar_a_supabase(p)