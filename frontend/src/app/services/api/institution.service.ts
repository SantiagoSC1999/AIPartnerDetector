import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '@environments/environment';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class InstitutionService {
  private apiUrl: string;

  constructor(private http: HttpClient) {
    this.apiUrl = this.getApiUrl();
  }

  /**
   * Get the API URL based on environment
   * If localhost, use localhost:8000
   * Otherwise use the configured backend URL
   */
  private getApiUrl(): string {
    const backendUrl = environment.apiUrl;
    
    // If we're on localhost, use localhost:8000
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      return 'http://localhost:8000/institutions';
    }
    
    // Otherwise use the configured backend URL
    return `${backendUrl}/institutions`;
  }

  generateEmbeddings(): Observable<any> {
    return this.http.post(`${this.apiUrl}/generate-embeddings`, {});
  }
}
