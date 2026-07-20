from supabase import create_client

# Pega aquí la URL exacta de tu proyecto
URL = "https://rbhafdjkdqpijrzuyeeq.supabase.co"
# Pega aquí la llave que empieza por eyJ...
KEY = "TU_KEY_AQUI_QUE_EMPIEZA_POR_eyJ"

supabase = create_client(URL, KEY)

try:
    print("Intentando insertar...")
    response = supabase.table("proyectos").insert({"nombre": "Prueba Final"}).execute()
    print("¡ÉXITO! Respuesta:", response)
except Exception as e:
    print("ERROR:", e)