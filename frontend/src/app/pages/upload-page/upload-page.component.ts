import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Router } from '@angular/router';
import { environment } from '@environments/environment';

@Component({
  selector: 'app-upload-page',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './upload-page.component.html',
  styleUrls: ['./upload-page.component.scss']
})
export class UploadPageComponent {
  dragOver = false;
  uploading = false;
  uploadProgress = 0;
  error = '';
  success = '';
  selectedFile: File | null = null;

  constructor(
    private http: HttpClient,
    private router: Router
  ) {}

  onDragOver(e: DragEvent) {
    e.preventDefault();
    this.dragOver = true;
  }

  onDragLeave() {
    this.dragOver = false;
  }

  onDrop(e: DragEvent) {
    e.preventDefault();
    this.dragOver = false;
    const files = e.dataTransfer?.files;
    if (files?.length) {
      this.handleFile(files[0]);
    }
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files?.length) {
      this.handleFile(input.files[0]);
    }
  }

  handleFile(file: File) {
    this.error = '';
    this.success = '';

    // Validate file type
    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      this.error = 'Please select an Excel file (.xlsx or .xls)';
      return;
    }

    // Validate file size
    if (file.size > environment.maxFileSize) {
      this.error = `File size exceeds ${environment.maxFileSize / (1024 * 1024)}MB limit`;
      return;
    }

    this.selectedFile = file;
  }

  uploadFile() {
    if (!this.selectedFile) {
      this.error = 'Please select a file first';
      return;
    }

    this.uploading = true;
    this.uploadProgress = 0;
    this.error = '';
    this.success = '';

    const formData = new FormData();
    formData.append('file', this.selectedFile);

    this.http.post<any>(`${environment.apiUrl}/institutions/duplicates/upload`, formData, {
      reportProgress: true,
      observe: 'events'
    }).subscribe({
      next: (event: HttpEvent<any>) => {
        if (event.type === HttpEventType.UploadProgress) {
          this.uploadProgress = Math.round((event.loaded / (event.total || 1)) * 100);
        } else if (event.type === HttpEventType.Response) {
          this.success = '✅ File uploaded successfully! Analyzing...';
          this.uploading = false;
          
          // Store results and navigate
          if (event.body) {
            // Save results to localStorage for the results page
            localStorage.setItem('analysisResults', JSON.stringify(event.body));
            
            // Navigate to results page after a short delay
            setTimeout(() => {
              this.router.navigate(['/results', event.body.file_id || 'latest']);
            }, 1500);
          }
        }
      },
      error: (err) => {
        console.error('Upload error:', err);
        this.error = '❌ Failed to upload file: ' + (err.error?.detail || err.message || 'Unknown error');
        this.uploading = false;
      }
    });
  }
}
