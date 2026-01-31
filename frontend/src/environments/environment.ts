export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000',
  appName: 'AI Partner Matching/Duplicate Detector',
  primaryColor: '#7ab800',
  maxFileSize: 10 * 1024 * 1024,
  allowedFileTypes: ['.xlsx', '.xls'],
  similarityThresholds: {
    duplicate: 0.85,
    potentialDuplicate: 0.75,
    exactMatch: 0.99
  }
};
