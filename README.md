# CLARISA AI Partner Detector

Sistema de detección de duplicados inteligente que permite a instituciones CGIAR identificar y gestionar socios duplicados en la base de datos CLARISA mediante análisis de similitud semántica con IA.

## 📋 Descripción General

CLARISA AI Partner Detector es una aplicación web moderna que combina un backend en Python (FastAPI) con un frontend en Angular 17+. El sistema permite:

- **Cargar datos de instituciones** desde archivos Excel
- **Detectar duplicados automáticamente** usando embeddings semánticos (AWS Bedrock)
- **Visualizar resultados** en dashboards interactivos
- **Sincronizar** con la base de datos CLARISA
- **Monitorear** la salud del sistema y estado de sincronización

## 🏗️ Estructura del Proyecto

```
clarisa_ai_partners/
├── backend/                    # API FastAPI
│   ├── src/
│   │   ├── api/               # Endpoints REST
│   │   ├── services/          # Lógica de negocio
│   │   ├── persistence/       # Integración Supabase
│   │   ├── embeddings/        # AWS Bedrock
│   │   ├── duplicate_detection/
│   │   └── audit/             # Logging
│   ├── scripts/               # Scripts de utilidad
│   └── requirements.txt
│
├── frontend/                   # Aplicación Angular
│   ├── src/
│   │   ├── app/
│   │   │   ├── components/    # Componentes reutilizables
│   │   │   ├── pages/         # Páginas principales
│   │   │   ├── services/      # Servicios API
│   │   │   └── interceptors/  # HTTP interceptors
│   │   └── assets/
│   └── package.json
│
└── README.md
```

## 🚀 Inicio Rápido

### Requisitos Previos

- **Python 3.10+**
- **Node.js 18+**
- **npm** o **yarn**
- Credenciales de **Supabase**
- Credenciales de **AWS Bedrock**

### Instalación Backend

```bash
cd backend

# Crear ambiente virtual
python -m venv venv

# Activar ambiente
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales
```

### Instalación Frontend

```bash
cd frontend

# Instalar dependencias
npm install

# Configurar proxy a backend (opcional)
# El proxy.conf.json ya está configurado para http://localhost:8000
```

### Correr la Aplicación

**Terminal 1 - Backend:**
```bash
cd backend
python run.py
# API disponible en http://localhost:8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
# Aplicación disponible en http://localhost:4200
```

## 📚 Características Principales

### 1. **Carga de Datos (Excel Upload)**
- Drag & drop de archivos .xlsx / .xls
- Validación de columnas requeridas
- Límite de 10MB por archivo
- Visualización de progreso en tiempo real

### 2. **Detección de Duplicados**
- Análisis semántico con embeddings IA
- 3 niveles de coincidencia:
  - **Duplicado** (≥85% similitud)
  - **Potencial duplicado** (≥75% similitud)
  - **Sin coincidencia** (<75% similitud)
- Explicación automática del motivo

### 3. **Resultados Interactivos**
- Tabla con filtrado y búsqueda
- Exportación a CSV/Excel
- Detalles expandibles por institución
- Visualización de puntuaciones de similitud

### 4. **Dashboard de Monitoreo**
- Estadísticas del sistema
- Historial de sincronizaciones
- Contador de embeddings generados
- Gráficos de distribución

### 5. **Panel de Administración**
- Sincronización manual con CLARISA
- Generación de embeddings faltantes
- Visualización de configuración del sistema
- Logs de operaciones

## 🔌 Endpoints de la API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/institutions/duplicates/upload` | Cargar Excel y detectar duplicados |
| GET | `/institutions/sync-status` | Obtener estado de sincronización |
| POST | `/institutions/sync-clarisa` | Sincronizar con CLARISA |
| GET | `/institutions/health` | Estado de salud del sistema |
| GET | `/institutions/config` | Configuración actual |
| POST | `/institutions/generate-embeddings` | Generar embeddings faltantes |
| GET | `/institutions/test-clarisa-api` | Probar conexión CLARISA |

## 🎨 Temas y Estilos

**Color Principal:** `#7ab800` (CGIAR Green)

El frontend usa:
- **SCSS** con variables de tema
- **Responsive Design** (mobile-first)
- **Componentes Material Design**
- **Accesibilidad WCAG 2.1 AA**

## 🔧 Variables de Entorno

### Backend (.env)

```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
CLARISA_API_URL=https://clarisa.cgiar.org/api
```

### Frontend (environment.ts)

```typescript
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000',
  apiVersion: 'v1',
  primaryColor: '#7ab800',
  maxFileSize: 10 * 1024 * 1024,
  allowedFileTypes: ['.xlsx', '.xls']
};
```

## 📦 Tecnologías Utilizadas

### Backend
- **FastAPI** - Framework web moderno
- **Python 3.10+** - Lenguaje
- **Supabase** - Base de datos PostgreSQL
- **AWS Bedrock** - Embeddings semánticos
- **Pandas** - Procesamiento de datos
- **OpenPyXL** - Lectura de Excel

### Frontend
- **Angular 17+** - Framework web
- **TypeScript 5.0+** - Lenguaje tipado
- **RxJS** - Programación reactiva
- **SCSS** - Estilos avanzados
- **Chart.js** - Gráficos interactivos

## 📖 Documentación Adicional

- [Setup Guide Backend](./backend/SETUP_GUIDE.md)
- [README Frontend](./frontend/README.md)
- [Guía de Estilos](./frontend/STYLE_SYSTEM_GUIDE.md)
- [Guía Responsive](./frontend/RESPONSIVE_DESIGN_GUIDE.md)

## 🧪 Testing

### Backend
```bash
cd backend
pytest
```

### Frontend
```bash
cd frontend
npm test              # Unit tests
npm run e2e          # End-to-end tests
```

## 🚢 Deployment

### Docker

```bash
# Construir imagen
docker build -t clarisa-detector .

# Correr contenedor
docker run -p 80:80 clarisa-detector
```

### Build Producción

**Frontend:**
```bash
npm run build -- --configuration=production
```

**Backend:**
```bash
python run.py  # En producción usar gunicorn/uvicorn
```

## 📋 Configuración de Colores

| Uso | Color | Hex |
|-----|-------|-----|
| Primario | Verde CGIAR | #7ab800 |
| Primario Oscuro | Verde Oscuro | #5a8c00 |
| Primario Claro | Verde Claro | #9ad633 |
| Secundario | Azul Oscuro | #2c3e50 |
| Acento | Azul Cielo | #3498db |
| Éxito | Verde | #27ae60 |
| Advertencia | Naranja | #f39c12 |
| Peligro | Rojo | #e74c3c |

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Crea un branch para tu feature (`git checkout -b feature/AmazingFeature`)
2. Commit tus cambios (`git commit -m 'Add AmazingFeature'`)
3. Push al branch (`git push origin feature/AmazingFeature`)
4. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo licencia CGIAR.

## 👤 Autor

**SantiagoSC1999**
- Email: sasa.sanchezcorre-7@hotmail.com
- GitHub: [@SantiagoSC1999](https://github.com/SantiagoSC1999)

## 📞 Soporte

Para reportar bugs o solicitar features, abre un issue en el repositorio.

---

**Última actualización:** Enero 2026
