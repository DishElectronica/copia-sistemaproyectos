-- Estructura de Base de Datos para el Sistema de Seguimiento
CREATE TABLE IF NOT EXISTS encargados (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100),
    usuario VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS proyectos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_proyecto VARCHAR(100),
    cliente VARCHAR(100),
    fecha_inicio DATE NULL,
    fecha_finalizacion DATE NULL,
    presupuesto DECIMAL(15,2),
    costo_actual DECIMAL(15,2),
    fecha_actualizacion_costo DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    costo_real DECIMAL(15,2),
    orden_compra VARCHAR(50),
    factura VARCHAR(50),
    estado ENUM('activo', 'finalizado') DEFAULT 'activo',
    es_prioritario BOOLEAN DEFAULT FALSE,
    id_encargado INT,
    FOREIGN KEY (id_encargado) REFERENCES encargados(id)
);

CREATE TABLE IF NOT EXISTS entregables (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_proyecto INT,
    informe_tecnico BOOLEAN DEFAULT FALSE,
    costo_preliminar BOOLEAN DEFAULT FALSE,
    fecha_preliminar DATE NULL,
    costo_final BOOLEAN DEFAULT FALSE,
    fecha_final DATE NULL,
    acta_firmada BOOLEAN DEFAULT FALSE,
    contador_solicitudes INT DEFAULT 0,
    fecha_ultima_solicitud DATE NULL,
    notas_gestion_acta TEXT,
    FOREIGN KEY (id_proyecto) REFERENCES proyectos(id)
);

CREATE TABLE IF NOT EXISTS links_proyectos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_proyecto INT,
    nombre_link VARCHAR(50),
    url TEXT,
    FOREIGN KEY (id_proyecto) REFERENCES proyectos(id)
);
CREATE TABLE IF NOT EXISTS notas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proyecto_id INTEGER,
    contenido TEXT,
    leido INTEGER DEFAULT 0,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (proyecto_id) REFERENCES proyectos(id)
);

