import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '@environments/environment';

@Component({
  selector: 'app-analysis-detail-page',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './analysis-detail-page.component.html',
  styleUrls: ['./analysis-detail-page.component.scss']
})
export class AnalysisDetailPageComponent implements OnInit {
  loading = true;
  error = '';
  analysis: any = null;
  fileId = '';

  constructor(private route: ActivatedRoute, private http: HttpClient) {
    this.fileId = this.route.snapshot.paramMap.get('fileId') || '';
  }

  ngOnInit() {
    this.loading = true;
    this.http.get<any>(`${environment.apiUrl}/institutions/analysis/${this.fileId}`).subscribe({
      next: (data) => {
        this.analysis = data;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load analysis detail';
        this.loading = false;
      }
    });
  }
}
