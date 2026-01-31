import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export function apiInterceptor(req: HttpRequest<any>, next: any): Observable<HttpEvent<any>> {
  // Only modify requests to /institutions (our backend API)
  if (req.url.startsWith('/institutions')) {
    // Prepend the API URL from environment configuration
    // This allows Railway deployment to use the configured backend URL
    const apiUrl = environment.apiUrl;
    const fullUrl = `${apiUrl}${req.url}`;
    req = req.clone({ url: fullUrl });
  }
  
  return next(req);
}
