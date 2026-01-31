import { Component, Input, Output, EventEmitter, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './sidebar.component.html',
  styleUrls: ['./sidebar.component.scss']
})
export class SidebarComponent {

  // open = false;
  @Input() open = false;
  @Output() openChange = new EventEmitter<boolean>();

  isMobile(): boolean {
    return window.innerWidth <= 768;
  }

   toggleSidebar(): void {
    this.open = !this.open;
  }

  closeSidebar() {
    this.open = false;
    this.openChange.emit(false);
  }

  onMenuClick(): void {
    if (this.isMobile()) {
      this.closeSidebar();
    }
    
  }


  @HostListener('window:resize')
  onResize() {
    if (!this.isMobile()) {
      this.open = false;
      this.openChange.emit(false);
    }
  }

  menuItems = [
    { label: 'Dashboard', icon: '📊', route: '/dashboard' },
    { label: 'Upload Excel', icon: '📤', route: '/upload' },
    { label: 'Sync Status', icon: '🔄', route: '/sync' },
    { label: 'Settings', icon: '⚙️', route: '/settings' },
    { label: 'Analysis History', icon: '📁', route: '/analysis-history' }
  ];
}
