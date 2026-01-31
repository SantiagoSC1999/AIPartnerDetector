import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { environment } from '@environments/environment';

@Component({
  selector: 'app-analysis-history-page',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './analysis-history-page.component.html',
  styleUrls: ['./analysis-history-page.component.scss']
})
export class AnalysisHistoryPageComponent implements OnInit {
  loading = true;
  error = '';
  analyses: any[] = [];

  constructor(private http: HttpClient, private router: Router) {}

  ngOnInit() {
    this.loading = true;
    this.http.get<any>(`${environment.apiUrl}/institutions/analysis`).subscribe({
      next: (data) => {
        this.analyses = data.analyses || [];
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load analysis history';
        this.loading = false;
      }
    });
  }

  viewAnalysis(fileId: string) {
    this.router.navigate(['/analysis-history', fileId]);
  }
}
