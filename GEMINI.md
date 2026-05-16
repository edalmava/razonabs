# Test de Razonamiento Abstracto — Contexto del Proyecto

Sistema de evaluación basado en Django para la gestión y aplicación de tests de razonamiento abstracto. El proyecto permite a los docentes administrar un banco de preguntas visuales y configurar tests con tiempos limitados para los estudiantes.

## 🚀 Tecnologías Principales

- **Framework:** [Django 6.0.5](https://www.djangoproject.com/)
- **Lenguaje:** Python 3.13
- **Base de Datos:** PostgreSQL (configurada en `settings.py`), SQLite (desarrollo local `db.sqlite3`)
- **Imágenes:** [Pillow](https://python-pillow.org/) (para gestión de estímulos y opciones de respuesta)
- **Entorno:** Virtualenv en el directorio `virtual/`

## 🏗️ Arquitectura y Modelos

El núcleo del sistema reside en la aplicación `test_razonamiento`:

- **Usuarios (`CustomUser`):** Soporta roles de **Estudiante** (Student) y **Docente** (Teacher).
- **Banco de Preguntas (`Question` & `AnswerOption`):** Cada pregunta consiste en una imagen de estímulo y exactamente 6 opciones de respuesta (también imágenes).
- **Tests (`Test`):** Configuración de sesiones de evaluación (nombre, duración en minutos, cantidad de preguntas a seleccionar aleatoriamente).
- **Intentos (`Attempt` & `AttemptAnswer`):** Registro detallado de la participación del estudiante, incluyendo un snapshot de las preguntas asignadas, tiempo restante y cálculo automático de puntaje.

## 🛠️ Comandos de Desarrollo

### Configuración Inicial
```powershell
# Activar entorno virtual
.\virtual\Scripts\Activate.ps1

# Instalar dependencias (basado en el código actual)
pip install django pillow psycopg2-binary
```

### Gestión de Base de Datos
```powershell
# Crear migraciones
python manage.py makemigrations test_razonamiento

# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser
```

### Ejecución
```powershell
# Iniciar servidor de desarrollo
python manage.py runserver
```

## 📏 Convenciones del Proyecto

- **Estilo de Código:** Adherencia estricta a **PEP 8** (longitud de línea ≤ 88 caracteres, preferido por herramientas como Black).
- **Modelos:** Todos los modelos heredan de `TimeStampedModel` para trazabilidad automática (`created_at`, `updated_at`).
- **Administración:** La lógica de negocio pesada para la gestión docente está integrada en el Django Admin (`admin.py`), utilizando inlines, acciones masivas y validaciones personalizadas.
- **Validaciones:** Se aplican tanto a nivel de modelo (`clean()`) como a nivel de base de datos (`constraints`) para asegurar la integridad de los datos (ej. exactamente 6 opciones por pregunta).
- **Media:** Las imágenes se organizan dinámicamente en `media/questions/{id}/` mediante funciones de utilidad en `models.py`.

## 📂 Estructura de Directorios Clave

- `testrazonabs/`: Configuración global del proyecto Django (settings, urls).
- `test_razonamiento/`: Lógica de la aplicación (modelos, administración, migraciones).
- `virtual/`: Entorno virtual de Python (no incluir en control de versiones).
