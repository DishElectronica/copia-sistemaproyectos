# Comandos Útiles - Sistema de Proyectos  datos guardados  

11:12pm  pm  junio 6  guardados

### 1. Servidor y Ejecución
- `
` ' python app.py  : Inicia el servidor de desarrollo.
- `Ctrl + C` : Detiene el servidor en la terminal.

### 2. Base de Datos (SQLite)
Para entrar a consultar la base de datos directamente desde la terminal:
- `sqlite3 instance/proyectos.db` : Abre la base de datos (nota: Flask suele crearla en la carpeta 'instance').
- `.tables` : Lista todas las tablas creadas.
- `.schema nombre_tabla` : Muestra la estructura de una tabla específica.
- `SELECT * FROM proyecto;` : Ver todos los proyectos guardados.
- `.exit` : Salir de la consola de sqlite.

### 3. Mantenimiento y Limpieza
- `rm instance/proyectos.db` : (En Linux/Git Bash) Borra la base de datos para resetear todo el sistema.
- `del instance\proyectos.db` : (En la terminal CMD de Windows) Borra la base de datos.

### 4. Git (Si decides usar control de versiones)
- `git status` : Ver qué archivos han cambiado.
- `git add .` : Preparar cambios para guardar.
- `git commit -m "Descripción"` : Guardar una versión del proyecto.

### Tips de Diseño (CSS)
- `target="_blank"`: Indispensable en enlaces de gestión para no perder la sesión activa.
- `flex-direction: row;`: Si quieres que los inputs y el botón "Ir al Link" queden todos en una sola línea, puedes aplicar esto a tu clase `.link-item`.
source venv/Scripts/activate   activar entorno virtual