import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { environment } from '@environments/environment';

@Component({
  selector: 'app-sync-page',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './sync-page.component.html',
  styleUrls: ['./sync-page.component.scss']
})
export class SyncPageComponent implements OnInit {
  loading = false;
  syncing = false;
  syncStatus = {
    institutions_count: 0,
    countries_count: 0,
    embeddings_count: 0,
    last_sync: null as string | null
  };
  error = '';
  success = '';

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.loadSyncStatus();
  }

  loadSyncStatus() {
    this.loading = true;
    this.http.get<any>(`${environment.apiUrl}/institutions/sync-status`).subscribe({
      next: (data) => {
        this.syncStatus = data;
        this.loading = false;
      },
      error: (err) => {
        console.error('Error loading sync status:', err);
        this.error = 'Failed to load sync status';
        this.loading = false;
      }
    });
  }

  triggerSync() {
    this.syncing = true;
    this.error = '';
    this.success = '';

    this.http.post(`${environment.apiUrl}/institutions/sync-clarisa`, {}).subscribe({
      next: (result: any) => {
        this.success = 'Sync triggered successfully!';
        this.syncing = false;
        setTimeout(() => this.loadSyncStatus(), 1000);
      },
      error: (err) => {
        console.error('Sync error:', err);
        this.error = 'Failed to trigger sync: ' + (err.message || 'Unknown error');
        this.syncing = false;
      }
    });
  }
}
