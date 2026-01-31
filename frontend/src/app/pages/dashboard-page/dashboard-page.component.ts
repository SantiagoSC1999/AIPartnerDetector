import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { environment } from '@environments/environment';
import { InstitutionService } from '../../services/api/institution.service';

@Component({
  selector: 'app-dashboard-page',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard-page.component.html',
  styleUrls: ['./dashboard-page.component.scss']
})
export class DashboardPageComponent implements OnInit {
  loading = true;
  stats = {
    institutions_count: 0,
    countries_count: 0,
    embeddings_count: 0,
    last_sync: null as string | null
  };
  health = {
    status: 'unknown',
    message: ''
  };
  error = '';
  generatingEmbeddings = false;
  embeddingsMessage = '';

  constructor(private http: HttpClient, private institutionService: InstitutionService) {}

  ngOnInit() {
    this.loadDashboardData();
  }

  loadDashboardData() {
    this.loading = true;
    this.error = '';
    
    // Load sync status
    this.http.get<any>(`${environment.apiUrl}/institutions/sync-status`).subscribe({
      next: (data) => {
        this.stats = data;
      },
      error: (err) => {
        console.error('Error loading sync status:', err);
        this.error = 'Failed to load sync status';
      }
    });

    // Load health status
    this.http.get<any>(`${environment.apiUrl}/institutions/health`).subscribe({
      next: (data) => {
        this.health = data;
      },
      error: (err) => {
        console.error('Error loading health:', err);
        this.error = 'Failed to load health status';
      },
      complete: () => {
        this.loading = false;
      }
    });
  }

  refreshData() {
    this.loadDashboardData();
  }

  generateEmbeddings() {
    this.generatingEmbeddings = true;
    this.embeddingsMessage = '';
    this.institutionService.generateEmbeddings().subscribe({
      next: (res) => {
        this.embeddingsMessage = '✅ Embeddings generated successfully!';
        this.generatingEmbeddings = false;
        this.loadDashboardData();
      },
      error: (err) => {
        this.embeddingsMessage = '❌ Error generating embeddings: ' + (err.error?.detail || err.message || 'Unknown error');
        this.generatingEmbeddings = false;
      }
    });
  }
}
