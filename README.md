# Test de Razonamiento Abstracto

Sistema de evaluación basado en Django para la gestión y aplicación de tests de razonamiento abstracto. Permite a los docentes administrar un banco de preguntas visuales y configurar tests con tiempos limitados para los estudiantes.

## Características

- **Gestión de Preguntas**: Banco de preguntas con imágenes de estímulo y 6 opciones de respuesta visuales
- **Tests Configurables**: Define tiempo por pregunta, número de preguntas y máximo de intentos
- **Panel Docente**: CRUD completo de estudiantes, preguntas y tests
- **Panel Estudiantil**: Tests disponibles, seguimiento de intentos, historial de resultados
- **Importación Masiva**: Importar estudiantes desde archivo CSV

## Tech Stack

- Django 6.0.5
- Python 3.13
- PostgreSQL (producción) / SQLite (desarrollo local)
- Pillow para gestión de imágenes

## Instalación

```powershell
# Activar entorno virtual
.\virtual\Scripts\Activate.ps1

# Migrar base de datos
python manage.py migrate

# Ejecutar servidor
python manage.py runserver
```

## Rutas Principales

| Ruta | Descripción |
|------|-------------|
| `/` | Redirección según rol |
| `/login/` | Autenticación |
| `/tests/` | Tests disponibles (estudiante) |
| `/teacher/` | Panel docente |
| `/teacher/students/` | Gestión de estudiantes |
| `/teacher/questions/` | Banco de preguntas |
| `/admin/` | Admin de Django |

## Configuración

- Base de datos por defecto: PostgreSQL en `localhost:5433`
- Para usar SQLite en desarrollo local, editar `settings.py`:
  ```python
  DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
  ```

## Estructura

- `testrazonabs/`: Configuración del proyecto Django
- `test_razonamiento/`: Aplicación principal (models, views, templates)
- `media/questions/`: Imágenes de preguntas
- `db.sqlite3`: Base de datos SQLite local

## Documentación Adicional

- `AGENTS.md`: Guía para desarrolladores
- `GEMINI.md`: Documentación detallada del proyecto