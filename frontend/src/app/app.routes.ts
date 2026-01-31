import { Routes } from '@angular/router';
import { DashboardPageComponent } from './pages/dashboard-page/dashboard-page.component';
import { UploadPageComponent } from './pages/upload-page/upload-page.component';
import { ResultsPageComponent } from './pages/results-page/results-page.component';
import { SyncPageComponent } from './pages/sync-page/sync-page.component';
import { SettingsPageComponent } from './pages/settings-page/settings-page.component';
import { AnalysisHistoryPageComponent } from './pages/analysis-history-page/analysis-history-page.component';
import { AnalysisDetailPageComponent } from './pages/analysis-detail-page/analysis-detail-page.component';

export const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  { 
    path: 'dashboard', 
    component: DashboardPageComponent,
    data: { title: 'Dashboard' }
  },
  { 
    path: 'upload', 
    component: UploadPageComponent,
    data: { title: 'Upload Excel' }
  },
  { 
    path: 'results/:fileId', 
    component: ResultsPageComponent,
    data: { title: 'Results' }
  },
  { 
    path: 'sync', 
    component: SyncPageComponent,
    data: { title: 'Sync Status' }
  },
  { 
    path: 'settings', 
    component: SettingsPageComponent,
    data: { title: 'Settings' }
  },
  { 
    path: 'analysis-history', 
    component: AnalysisHistoryPageComponent,
    data: { title: 'Analysis History' }
  },
  { 
    path: 'analysis-history/:fileId', 
    component: AnalysisDetailPageComponent,
    data: { title: 'Analysis Detail' }
  }
];
