# Estructura del Proyecto - CLARISA AI Partners

## Organización de Carpetas

```
clarisa_ai_partners/
├── backend/                          # Backend API (Python/FastAPI)
│   ├── src/
│   │   ├── main.py                   # Punto de entrada de la aplicación
│   │   ├── config.py                 # Configuración
│   │   ├── api/                      # Rutas y endpoints
│   │   ├── services/                 # Servicios de lógica de negocio
│   │   ├── embeddings/               # Servicio de embeddings con AWS Bedrock
│   │   ├── duplicate_detection/      # Lógica de detección de duplicados
│   │   ├── persistence/              # Acceso a base de datos (Supabase)
│   │   └── audit/                    # Logging y auditoría
│   ├── requirements.txt               # Dependencias Python
│   ├── .env                          # Variables de entorno
│   ├── test_*.py                     # Scripts de prueba
│   └── *.xlsx                        # Archivos de prueba
│
├── frontend/                          # Frontend Angular/TypeScript
│   ├── src/
│   ├── package.json
│   └── ...
│
├── run_backend.py                    # Script para ejecutar el backend
├── .env                              # Variables de entorno (raíz)
├── .env.example                      # Ejemplo de variables de entorno
└── ...
```

## Cómo Ejecutar el Backend

### Opción 1: Desde la raíz del proyecto (Recomendado)

```bash
python run_backend.py
```

Este script:
- Cambia al directorio `backend/`
- Configura la ruta de Python
- Inicia Uvicorn en http://0.0.0.0:8000

### Opción 2: Desde el directorio backend

```bash
cd backend
python -m uvicorn src.main:app --reload
```

### Opción 3: Desde cualquier lugar usando la ruta completa

```bash
python -m uvicorn backend.src.main:app --reload --cwd backend
```

## Instalación de Dependencias

```bash
cd backend
pip install -r requirements.txt
```

O si usas conda:

```bash
cd backend
conda create -n clarisa python=3.9
conda activate clarisa
pip install -r requirements.txt
```

## Variables de Entorno

Las variables de entorno se deben configurar en `backend/.env`:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
CLARISA_API_URL=https://api.clarisa.cgiar.org/api/institutions
USE_MOCK_EMBEDDINGS=false
USE_MOCK_SUPABASE=false
```

## API Endpoints

### Upload Duplicates
- **POST** `/institutions/duplicates/upload` - Subir archivo Excel para detectar duplicados

### Analysis History
- **GET** `/institutions/analysis` - Listar todos los análisis realizados
- **GET** `/institutions/analysis/{file_id}` - Obtener detalles de un análisis específico

## Estructura de Backend

### `src/api/` - Rutas
- `institutions.py` - Endpoints para gestión de instituciones y duplicados

### `src/services/` - Lógica de negocio
- `excel_parser.py` - Parser de archivos Excel
- `normalization.py` - Normalización de datos
- `clarisa_sync_service.py` - Sincronización con API de CLARISA
- `embedding_service.py` - Gestión de embeddings

### `src/embeddings/` - Embeddings
- `bedrock_service.py` - Servicio de AWS Bedrock para generar embeddings

### `src/duplicate_detection/` - Detección
- `detector.py` - Lógica de detección de duplicados basada en 7 reglas

### `src/persistence/` - Base de datos
- `supabase_client.py` - Cliente de Supabase para operaciones CRUD

### `src/audit/` - Auditoría
- `logger.py` - Logging de auditoría y operaciones

## Testing

Ejecutar tests:

```bash
cd backend
python test_api.py
python test_embedding_format.py
```

## Notas de Desarrollo

- El backend usa **FastAPI** para el servidor REST
- Base de datos: **Supabase** (PostgreSQL)
- Embeddings: **AWS Bedrock Titan v2** (1024 dimensiones)
- Detección de duplicados basada en:
  1. Coincidencia exacta de nombres
  2. Similitud semántica > 0.75
  3. Señales basadas en reglas

## URLs Importantes

- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Supabase: https://app.supabase.com
