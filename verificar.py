import sqlite3

def verificar():
    conn = sqlite3.connect('proyectos.db')
    cursor = conn.cursor()
    # Esta consulta pregunta a la base de datos por el nombre de las tablas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tablas = cursor.fetchall()
    conn.close()
    
    print("Tablas encontradas en la base de datos:")
    for tabla in tablas:
        print(f"- {tabla[0]}")

if __name__ == '__main__':
    verificar()