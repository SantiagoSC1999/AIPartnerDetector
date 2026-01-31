import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '@environments/environment';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class InstitutionService {
  private apiUrl = `${environment.apiUrl}/institutions`;

  constructor(private http: HttpClient) {}

  generateEmbeddings(): Observable<any> {
    return this.http.post(`${this.apiUrl}/generate-embeddings`, {});
  }
}
