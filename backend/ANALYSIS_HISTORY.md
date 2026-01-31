# Analysis History Endpoints

## Setup

Antes de usar estos endpoints, necesitas crear la tabla en Supabase:

1. Ve a tu Supabase dashboard
2. Abre el SQL Editor
3. Copia y ejecuta el contenido de `db_create_analysis_table.sql`

```sql
-- Ejecuta este SQL en tu Supabase
CREATE TABLE IF NOT EXISTS analysis_records (
    id BIGSERIAL PRIMARY KEY,
    file_id UUID NOT NULL,
    filename TEXT NOT NULL,
    uploaded_id TEXT NOT NULL,
    institution_name TEXT,
    acronym TEXT,
    status TEXT NOT NULL,
    similarity FLOAT DEFAULT 0,
    clarisa_match INTEGER,
    reason TEXT,
    web_page TEXT,
    type TEXT,
    country INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analysis_file_id ON analysis_records(file_id);
CREATE INDEX IF NOT EXISTS idx_analysis_created_at ON analysis_records(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_status ON analysis_records(status);
CREATE INDEX IF NOT EXISTS idx_analysis_clarisa_match ON analysis_records(clarisa_match);
```

## Endpoints

### 1. GET `/institutions/analysis`
Obtiene la lista de todos los análisis realizados.

**Request:**
```bash
curl http://localhost:8000/institutions/analysis
```

**Response:**
```json
{
    "total": 5,
    "analyses": [
        {
            "file_id": "a1b2c3d4-e5f6-47g8-h9i0-j1k2l3m4n5o6",
            "filename": "institutions.xlsx",
            "created_at": "2026-01-31T10:30:00+00:00"
        },
        {
            "file_id": "b2c3d4e5-f6g7-48h9-i0j1-k2l3m4n5o6p7",
            "filename": "test_data.xlsx",
            "created_at": "2026-01-31T09:15:00+00:00"
        }
    ]
}
```

### 2. GET `/institutions/analysis/{file_id}`
Obtiene los detalles completos de un análisis específico, incluyendo todos los registros evaluados.

**Request:**
```bash
curl http://localhost:8000/institutions/analysis/a1b2c3d4-e5f6-47g8-h9i0-j1k2l3m4n5o6
```

**Response:**
```json
{
    "file_id": "a1b2c3d4-e5f6-47g8-h9i0-j1k2l3m4n5o6",
    "filename": "institutions.xlsx",
    "created_at": "2026-01-31T10:30:00+00:00",
    "total_records": 36,
    "summary": {
        "duplicate": 12,
        "possible_duplicate": 8,
        "no_match": 16
    },
    "records": [
        {
            "id": 1,
            "file_id": "a1b2c3d4-e5f6-47g8-h9i0-j1k2l3m4n5o6",
            "filename": "institutions.xlsx",
            "uploaded_id": "8465",
            "institution_name": "Wageningen University and Research Centre",
            "acronym": null,
            "status": "duplicate",
            "similarity": 1.0,
            "clarisa_match": 1,
            "reason": "Exact name match",
            "web_page": null,
            "type": "Private company (other than financial)",
            "country": 50,
            "created_at": "2026-01-31T10:30:00+00:00"
        },
        {
            "id": 2,
            "file_id": "a1b2c3d4-e5f6-47g8-h9i0-j1k2l3m4n5o6",
            "filename": "institutions.xlsx",
            "uploaded_id": "8495",
            "institution_name": "Bambu Nusa Verde",
            "acronym": null,
            "status": "no_match",
            "similarity": 0.0,
            "clarisa_match": null,
            "reason": "No matching institutions found",
            "web_page": null,
            "type": "Other",
            "country": 86,
            "created_at": "2026-01-31T10:30:00+00:00"
        }
    ]
}
```

## Flujo Completo

1. **Subes un archivo Excel** a `/institutions/duplicates/upload`
   - Se procesa inmediatamente
   - Se devuelven los resultados
   - Se guardan automáticamente en `analysis_records`

2. **Recuperas el historial** con `GET /institutions/analysis`
   - Ves todos los análisis previos
   - Cada uno tiene un `file_id`

3. **Ves detalles de un análisis** con `GET /institutions/analysis/{file_id}`
   - Accedes a todos los registros evaluados
   - Ves el resumen (duplicates, possible_duplicates, no_match)
   - Puedes revisar cada análisis individual

## Campos Guardados

Cada registro de análisis guarda:
- `file_id`: Identificador único del análisis
- `filename`: Nombre del archivo Excel
- `uploaded_id`: ID del registro en tu Excel
- `institution_name`: Nombre de la institución subida
- `acronym`: Acrónimo (si aplica)
- `status`: duplicate | possible_duplicate | no_match
- `similarity`: Score de similitud (0.0 - 1.0)
- `clarisa_match`: ID del duplicado encontrado en CLARISA
- `reason`: Explicación de por qué se clasificó así
- `web_page`: Página web (si aplica)
- `type`: Tipo de institución
- `country`: ID del país
- `created_at`: Timestamp del análisis

