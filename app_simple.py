from flask import Flask, request
from supabase import create_client

app = Flask(__name__)

# CONFIGURA ESTOS DOS VALORES CON TUS CREDENCIALES REALES
URL = "https://rbhafdjkdqpijrzuyeeq.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJiaGFmZGprZHFwaWpyenV5ZWVxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODEzNzAwMjIsImV4cCI6MjA5Njk0NjAyMn0.VAHqTuFHbLPer88ulL-BQAjvcPQSfCl-lGBVFZJWEp0"  

supabase = create_client(URL, KEY)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        print("--- PASO 1: RECIBIENDO DATOS ---")
        
        datos = {
            "nombre": request.form.get('nombre', 'Sin Nombre'),
            "cliente": request.form.get('cliente', 'Sin Cliente'),
            "fecha_inicio": None
        }
        
        try:
            print("--- PASO 2: CONECTANDO A SUPABASE ---")
            # Forzamos la inserción y capturamos el resultado
            response = supabase.table("proyectos").insert(datos).execute()
            
            print("--- PASO 3: ÉXITO ---")
            print(f"Respuesta de Supabase: {response.data}")
            return "¡Datos guardados con éxito en Supabase!"
            
        except Exception as e:
            print("--- PASO 3: ¡ERROR DETECTADO! ---")
            print(f"Detalle: {e}")
            return f"Error al guardar: {e}"

    return render_template('index.html')