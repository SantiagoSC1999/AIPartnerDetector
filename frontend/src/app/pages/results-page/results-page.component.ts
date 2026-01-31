import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

interface UploadRecord {
  id: string;
  status: 'duplicate' | 'potential_duplicate' | 'no_match';
  matched_clarisa_id?: number;
  similarity_score?: number;
  reason?: string;
  original_data: {
    partner_name: string;
    acronym: string;
    web_page: string;
    institution_type: string;
    country_id: string;
  };
}

interface AnalysisResult {
  file_id: string;
  total_records: number;
  results: UploadRecord[];
  progress: {
    processed: number;
    total: number;
    duplicates: number;
    potential_duplicates: number;
    errors: string[];
  };
}

@Component({
  selector: 'app-results-page',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './results-page.component.html',
  styleUrls: ['./results-page.component.scss']
})
export class ResultsPageComponent implements OnInit {
  fileId: string = '';
  analysisResults: AnalysisResult | null = null;
  loading = true;
  currentFilter = 'all';
  searchQuery = '';
  currentPage = 1;
  pageSize = 50;

  constructor(
    private route: ActivatedRoute,
    private router: Router
  ) {
    this.fileId = this.route.snapshot.paramMap.get('fileId') || '';
  }

  ngOnInit() {
    // Load results from localStorage
    const storedResults = localStorage.getItem('analysisResults');
    if (storedResults) {
      this.analysisResults = JSON.parse(storedResults);
      this.loading = false;
    } else {
      // Could load from API here if needed
      setTimeout(() => {
        this.loading = false;
      }, 2000);
    }
  }

  get filteredResults(): UploadRecord[] {
    if (!this.analysisResults?.results) return [];
    
    let results = this.analysisResults.results;

    // Apply filter
    if (this.currentFilter !== 'all') {
      results = results.filter(r => r.status === this.currentFilter);
    }

    // Apply search
    if (this.searchQuery.trim()) {
      const query = this.searchQuery.toLowerCase();
      results = results.filter(r =>
        r.original_data.partner_name.toLowerCase().includes(query) ||
        r.original_data.acronym.toLowerCase().includes(query) ||
        r.id.toLowerCase().includes(query)
      );
    }

    return results;
  }

  get paginatedResults(): UploadRecord[] {
    const start = (this.currentPage - 1) * this.pageSize;
    return this.filteredResults.slice(start, start + this.pageSize);
  }

  get totalPages(): number {
    return Math.ceil(this.filteredResults.length / this.pageSize);
  }

  getStatusBadgeClass(status: string): string {
    switch (status) {
      case 'duplicate':
        return 'duplicate';
      case 'potential_duplicate':
        return 'potential';
      case 'no_match':
        return 'no-match';
      default:
        return '';
    }
  }

  getStatusLabel(status: string): string {
    switch (status) {
      case 'duplicate':
        return '🔴 Duplicate';
      case 'potential_duplicate':
        return '🟡 Potential Duplicate';
      case 'no_match':
        return '🟢 No Match';
      default:
        return status;
    }
  }

  getSimilarityColor(score?: number): string {
    if (!score) return '#95a5a6';
    if (score >= 0.85) return '#e74c3c';
    if (score >= 0.75) return '#f39c12';
    return '#27ae60';
  }

  setFilter(filter: string) {
    this.currentFilter = filter;
    this.currentPage = 1;
  }

  goToPage(page: number) {
    if (page > 0 && page <= this.totalPages) {
      this.currentPage = page;
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }

  exportToCSV() {
    if (!this.filteredResults.length) return;

    const headers = [
      'ID',
      'Partner Name',
      'Acronym',
      'Status',
      'Similarity Score',
      'CLARISA Match ID',
      'Reason',
      'Web Page',
      'Institution Type',
      'Country ID'
    ];
    const escape = (val: any) => {
      if (val == null) return '';
      const str = String(val);
      return '"' + str.replace(/"/g, '""') + '"';
    };
    const rows = this.filteredResults.map(r => [
      r.id,
      r.original_data.partner_name,
      r.original_data.acronym,
      this.getStatusLabel(r.status),
      r.similarity_score !== undefined ? (r.similarity_score * 100).toFixed(1) + '%' : '-',
      r.matched_clarisa_id || '-',
      r.reason || '-',
      r.original_data.web_page || '-',
      r.original_data.institution_type || '-',
      r.original_data.country_id || '-'
    ].map(escape));
    const csv = [headers.map(escape).join(','), ...rows.map(row => row.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `analysis_results_${this.fileId}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  backToUpload() {
    this.router.navigate(['/upload']);
  }
}
