from app import app, db
from models import Link

with app.app_context():
    todos = Link.query.all()
    print(f"--- RESULTADO DE LA BASE DE DATOS ---")
    print(f"Total de links encontrados: {len(todos)}")
    for l in todos:
        print(f"- Link encontrado: {l.nombre_link} (ID Proyecto: {l.proyecto_id})")
