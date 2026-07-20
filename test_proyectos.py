from flask import Flask, request, render_template
from supabase import create_client

app = Flask(__name__)

# --- CONFIGURACIÓN GLOBAL (Arriba, fuera de cualquier ruta) ---
URL = "https://rbhafdjkdqpijrzuyeeq.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJiaGFmZGprZHFwaWpyenV5ZWVxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODEzNzAwMjIsImV4cCI6MjA5Njk0NjAyMn0.VAHqTuFHbLPer88ulL-BQAjvcPQSfCl-lGBVFZJWEp0" # <--- CAMBIA ESTO POR LA CORRECTA

supabase = create_client(URL, KEY)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        print("--- PASO A: PROCESANDO DATOS ---")
        
        datos = {
            "nombre": request.form.get('nombre'),
            "cliente": request.form.get('cliente'),
            "fecha_inicio": None
        }

        try:
            print("--- PASO B: EJECUTANDO INSERT ---")
            # Intentamos guardar
            response = supabase.table("proyectos").insert(datos).execute()
            print("--- PASO C: ¡ÉXITO! ---")
            return "Datos guardados correctamente."

        except Exception as e:
            print("--- ¡ERROR AL GUARDAR! ---")
            print(f"Detalle del error: {e}")
            return f"Error: {e}"

    return render_template('index.html') # O tu archivo de formulario

if __name__ == '__main__':
    app.run(debug=True)