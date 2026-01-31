import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { environment } from '@environments/environment';

@Component({
  selector: 'app-settings-page',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './settings-page.component.html',
  styleUrls: ['./settings-page.component.scss']
})
export class SettingsPageComponent implements OnInit {
  loading = true;
  config = {
    exact_match_threshold: 0,
    potential_duplicate_threshold: 0,
    duplicate_threshold: 0,
    embedding_batch_size: 0
  };
  error = '';

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.loadConfig();
  }

  loadConfig() {
    this.loading = true;
    this.http.get<any>(`${environment.apiUrl}/institutions/config`).subscribe({
      next: (data) => {
        this.config = data;
        this.loading = false;
      },
      error: (err) => {
        console.error('Error loading config:', err);
        this.error = 'Failed to load configuration';
        this.loading = false;
      }
    });
  }
}
