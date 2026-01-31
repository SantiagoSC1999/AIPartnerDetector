import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export function apiInterceptor(req: HttpRequest<any>, next: any): Observable<HttpEvent<any>> {
  // API Interceptor - can add common headers here
  return next(req);
}
