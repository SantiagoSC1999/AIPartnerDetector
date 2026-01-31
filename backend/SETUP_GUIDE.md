# CLARISA Project - Complete Setup Guide

## Project Structure

The CLARISA AI Partners project is now organized with frontend and backend separated:

```
d:\Estudios\clarisa_ai_partners\
├── frontend/                          # Angular 17+ Frontend ✅ RUNNING
│   ├── src/
│   │   ├── app/
│   │   │   ├── components/            # Reusable components
│   │   │   ├── pages/                 # Page components
│   │   │   ├── services/              # API services
│   │   │   ├── models/                # TypeScript interfaces
│   │   │   └── interceptors/          # HTTP interceptors
│   │   ├── environments/              # Environment configs
│   │   ├── assets/                    # Static assets
│   │   └── styles.scss                # Global styles
│   ├── angular.json                   # Angular configuration
│   ├── package.json                   # Frontend dependencies
│   └── README.md                      # Frontend documentation
│
├── src/                               # FastAPI Backend
│   ├── __init__.py
│   ├── main.py                        # FastAPI application
│   ├── config.py                      # Configuration
│   ├── api/
│   │   ├── __init__.py
│   │   └── institutions.py            # Institutions endpoints
│   ├── services/
│   │   ├── clarisa_sync_service.py
│   │   ├── embedding_service.py
│   │   ├── excel_parser.py
│   │   └── normalization.py
│   ├── persistence/
│   │   └── supabase_client.py         # Database client
│   ├── embeddings/
│   │   └── bedrock_service.py         # AWS Bedrock service
│   ├── duplicate_detection/
│   │   └── detector.py                # Duplicate detection logic
│   └── audit/
│       └── logger.py                  # Audit logging
│
├── package.json                       # Project metadata
├── requirements.txt                   # Python dependencies
├── test_*.py                          # Test files
└── FRONTEND_SETUP.md                  # Frontend setup documentation
```

## Quick Start

### 1. Frontend (Angular)

**Currently Running**: ✅ http://localhost:4200

```bash
# Navigate to frontend
cd frontend

# Install dependencies (already done)
npm install --legacy-peer-deps

# Start development server
npm start

# Build for production
npm run build:prod
```

### 2. Backend (FastAPI)

**Status**: 🔴 Not started yet

```bash
# From root directory
cd d:\Estudios\clarisa_ai_partners

# Install Python dependencies
pip install -r requirements.txt

# Start backend server
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000

# Backend will be available at http://localhost:8000
```

## Frontend Features

### Pages Available
- **Dashboard** (`/dashboard`) - System monitoring and statistics
- **Upload Excel** (`/upload`) - File upload with validation
- **Sync Status** (`/sync`) - Database synchronization management
- **Settings** (`/settings`) - System configuration view

### Components
- Header with CGIAR branding
- Responsive sidebar navigation
- Footer with system info
- Reusable UI components
- Loading spinners and error alerts

## Environment Configuration

### Frontend (`frontend/src/environments/environment.ts`)
```typescript
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000',
  maxFileSize: 10 * 1024 * 1024,
  allowedFileTypes: ['.xlsx', '.xls'],
  similarityThresholds: {
    duplicate: 0.85,
    potentialDuplicate: 0.75,
    exactMatch: 0.99
  }
};
```

### Backend
- Configure Supabase connection in `src/config.py`
- Set AWS Bedrock credentials
- Configure CLARISA API endpoint
- Database connection strings

## API Integration

The frontend is ready to communicate with backend endpoints:

```
POST   /institutions/duplicates/upload      Upload Excel file
POST   /institutions/sync-clarisa            Trigger CLARISA sync
GET    /institutions/sync-status             Get database status
GET    /institutions/health                  System health check
GET    /institutions/config                  System configuration
GET    /institutions/test-clarisa-api        Test CLARISA connectivity
POST   /institutions/generate-embeddings    Generate missing embeddings
```

## Development Workflow

### Frontend Development
1. Frontend runs on http://localhost:4200
2. Changes to TypeScript/HTML/SCSS auto-reload
3. Browser automatically refreshes
4. Console shows any errors

### Backend Development
1. Start backend on http://localhost:8000
2. Frontend proxy (`proxy.conf.json`) routes `/api/*` to backend
3. Use Postman or `curl` to test endpoints
4. Backend changes require restart

### Testing API Endpoints

```bash
# Test backend health
curl http://localhost:8000/institutions/health

# List available endpoints
curl http://localhost:8000/docs

# Interactive API documentation
Open http://localhost:8000/docs in browser
```

## File Sizes & Performance

Frontend Build:
- main.js: ~2.85 MB
- styles.css: ~152 KB
- polyfills.js: ~263 KB
- Total initial: ~3.26 MB

Optimizations in place:
- Tree shaking enabled
- Code splitting ready
- Lazy loading routes
- CSS optimization

## Deployment Options

### Frontend
- **Netlify**: `npm run build:prod` then deploy `dist/` folder
- **Vercel**: Connect GitHub repo with framework preset to Angular
- **AWS S3 + CloudFront**: Upload `dist/` to S3
- **Docker**: Use provided Dockerfile
- **Nginx**: Serve static files from `dist/clarisa-frontend`

### Backend
- **Heroku**: Deploy with `Procfile`
- **AWS EC2**: Run with `uvicorn` or `gunicorn`
- **Google Cloud Run**: Containerized deployment
- **Docker**: Build image and run

## Docker Deployment

### Frontend
```dockerfile
FROM node:18-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --legacy-peer-deps
COPY . .
RUN npm run build:prod

FROM nginx:alpine
COPY --from=builder /app/dist/clarisa-frontend /usr/share/nginx/html
EXPOSE 80
```

### Build & Run
```bash
docker build -t clarisa-frontend .
docker run -p 80:4200 clarisa-frontend
```

## Troubleshooting

### Frontend Won't Start
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install --legacy-peer-deps
npm start
```

### Port Already in Use
```bash
# Find process using port 4200
netstat -ano | findstr :4200

# Kill process (Windows)
taskkill /PID <PID> /F

# Or use different port
ng serve --port 4300
```

### API Calls Failing
1. Verify backend is running: http://localhost:8000/docs
2. Check browser console for CORS errors
3. Verify proxy.conf.json is configured correctly
4. Check network tab in browser DevTools

## Next Steps

1. **Start Backend**: Run FastAPI server on port 8000
2. **Test Endpoints**: Use Swagger UI at http://localhost:8000/docs
3. **Upload Test Data**: Use the Excel upload page
4. **Monitor Dashboard**: Check real-time statistics
5. **Configure Settings**: Adjust thresholds as needed

## Resources

- **Angular Documentation**: https://angular.io/docs
- **TypeScript Handbook**: https://www.typescriptlang.org/docs/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **SCSS Guide**: https://sass-lang.com/documentation/

## Contact & Support

For issues or questions about the setup:
1. Check logs in browser console (Frontend)
2. Check terminal output (Backend)
3. Review FRONTEND_SETUP.md for frontend specifics
4. Check requirements.txt for backend dependencies

---

**Project Status**: Frontend ✅ Running | Backend ⏳ Ready to Start
**Frontend URL**: http://localhost:4200
**Backend URL**: http://localhost:8000 (when started)
**Last Updated**: 2026-01-30
