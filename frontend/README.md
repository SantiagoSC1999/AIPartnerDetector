# CLARISA Duplicate Detector Frontend

A modern Angular 17+ web application for detecting duplicate institutions in the CLARISA database using semantic similarity analysis and Excel file uploads.

## Features

- **Excel File Upload**: Drag-and-drop interface for uploading institution data
- **Duplicate Detection**: Automatic detection of duplicates against CLARISA database
- **Interactive Dashboard**: Real-time monitoring of system health and statistics
- **Results Visualization**: Color-coded similarity scores and detailed duplicate information
- **Synchronization Management**: Manual trigger for CLARISA database synchronization
- **Configuration Display**: View and monitor system thresholds and settings

## Quick Start

### Prerequisites

- Node.js 18+ 
- npm or yarn
- Angular CLI 17+

### Installation

```bash
cd frontend
npm install
```

### Development Server

```bash
npm start
```

Navigate to `http://localhost:4200/`. The application will automatically reload if you change any source files.

```bash
# Or with hot reload and auto-open
npm run dev
```

### Build for Production

```bash
npm run build:prod
```

The build artifacts will be stored in the `dist/` directory.

## Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── components/
│   │   │   ├── layout/          # Header, Sidebar, Footer
│   │   │   ├── upload/          # Excel upload components
│   │   │   ├── results/         # Results display components
│   │   │   ├── dashboard/       # Dashboard widgets
│   │   │   └── shared/          # Shared utilities
│   │   ├── services/            # API and utility services
│   │   ├── models/              # TypeScript interfaces
│   │   ├── pages/               # Page components
│   │   ├── interceptors/        # HTTP interceptors
│   │   └── app.routes.ts        # Route configuration
│   ├── environments/            # Environment configs
│   ├── assets/                  # Static assets
│   └── styles.scss              # Global styles
├── angular.json                 # Angular CLI config
├── tsconfig.json               # TypeScript config
└── package.json                # Dependencies
```

## API Integration

The frontend connects to a FastAPI backend at `http://localhost:8000` with the following endpoints:

- `POST /institutions/duplicates/upload` - Upload Excel file
- `GET /institutions/sync-status` - Get database status
- `POST /institutions/sync-clarisa` - Trigger sync
- `GET /institutions/health` - System health check
- `GET /institutions/config` - System configuration
- `GET /institutions/test-clarisa-api` - Test CLARISA API
- `POST /institutions/generate-embeddings` - Generate embeddings

## Configuration

Edit `src/environments/environment.ts` to configure:

```typescript
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000',
  maxFileSize: 10 * 1024 * 1024, // 10MB
  allowedFileTypes: ['.xlsx', '.xls'],
  similarityThresholds: {
    duplicate: 0.85,
    potentialDuplicate: 0.75,
    exactMatch: 0.99
  }
};
```

## Technologies

- **Framework**: Angular 17+
- **Language**: TypeScript 5.0+
- **Styling**: SCSS
- **HTTP**: Angular HttpClient
- **Routing**: Angular Router
- **Build Tool**: Angular CLI / Webpack

## Running Tests

```bash
# Unit tests
npm test

# E2E tests
npm run e2e
```

## Deployment

### Docker

```bash
docker build -t clarisa-frontend .
docker run -p 80:80 clarisa-frontend
```

### Nginx

The application can be deployed to any static hosting service (Netlify, Vercel, etc.) or served via Nginx.

## Color Theme

Primary Color: **#7ab800** (CGIAR Green)

- Primary Dark: #5a8c00
- Primary Light: #9ad633
- Secondary: #2c3e50
- Background: #f8f9fa

## Accessibility

The application follows WCAG 2.1 AA compliance standards with:

- Semantic HTML
- ARIA labels where needed
- Keyboard navigation support
- High contrast colors
- Responsive design

## Development Guidelines

- Use standalone Angular components
- Implement TypeScript strict mode
- Follow Angular style guide
- Add unit tests for new features
- Use RxJS for reactive programming

## License

Copyright © 2024 CGIAR. All rights reserved.

## Support

For issues or questions, please contact the development team.
