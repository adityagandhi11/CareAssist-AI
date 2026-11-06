import { Component, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '../core/auth.service';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="app-frame">
      @if (menuOpen()) { <button class="scrim" aria-label="Close navigation" (click)="menuOpen.set(false)"></button> }
      <aside class="sidebar" [class.open]="menuOpen()">
        <a class="brand" routerLink="/dashboard" (click)="menuOpen.set(false)">
          <span class="brand-mark"><span>✚</span></span>
          <span class="brand-name">care<span>assist</span><small>YOUR HEALTH, IN GOOD HANDS</small></span>
        </a>
        <div class="workspace-label">{{ isAdmin ? 'WORKSPACE' : 'YOUR CARE' }}</div>
        <nav class="navigation" aria-label="Main navigation">
          @if (!isAdmin) {
            <a routerLink="/dashboard" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }" (click)="menuOpen.set(false)"><span class="nav-icon">⌂</span> Overview</a>
            <a routerLink="/appointments" routerLinkActive="active" (click)="menuOpen.set(false)"><span class="nav-icon">▦</span> Appointments</a>
            <a routerLink="/enquiries" routerLinkActive="active" (click)="menuOpen.set(false)"><span class="nav-icon">◷</span> My enquiries</a>
            <a routerLink="/assistant" routerLinkActive="active" (click)="menuOpen.set(false)"><span class="nav-icon">✧</span> Care assistant <span class="new-pill">AI</span></a>
          } @else {
            <a routerLink="/admin/dashboard" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }" (click)="menuOpen.set(false)"><span class="nav-icon">⌂</span> Overview</a>
            <a routerLink="/appointments" routerLinkActive="active" (click)="menuOpen.set(false)"><span class="nav-icon">▦</span> Appointments</a>
            <a routerLink="/enquiries" routerLinkActive="active" (click)="menuOpen.set(false)"><span class="nav-icon">◷</span> Enquiries</a>
            <a routerLink="/admin/documents" routerLinkActive="active" (click)="menuOpen.set(false)"><span class="nav-icon">▤</span> Knowledge base</a>
          }
        </nav>
        <div class="sidebar-bottom">
          <div class="help-card"><span class="help-spark">✦</span><b>Need a hand?</b><p>Our support team is always happy to help.</p><a routerLink="/enquiries">Contact support <span>→</span></a></div>
          <div class="sidebar-user">
            <span class="avatar">{{ initials }}</span>
            <span class="user-meta"><b>{{ auth.user()?.name || 'Care member' }}</b><small>{{ isAdmin ? 'Clinic administrator' : 'Patient account' }}</small></span>
            <button type="button" class="logout" aria-label="Sign out" title="Sign out" (click)="auth.logout()">↗</button>
          </div>
        </div>
      </aside>
      <main class="main-area">
        <header class="topbar">
          <button type="button" class="menu-button" aria-label="Open navigation" (click)="menuOpen.set(true)">☰</button>
          <div class="breadcrumb"><span>{{ isAdmin ? 'Clinic workspace' : 'Patient portal' }}</span><i>/</i><b>{{ pageTitle }}</b></div>
          <div class="top-actions">
            <span class="secure-label"><span></span> Secure &amp; private</span>
            <button type="button" class="top-avatar" [title]="auth.user()?.name || 'Account'">{{ initials }}</button>
          </div>
        </header>
        <div class="page-content"><router-outlet /></div>
      </main>
    </div>
  `,
  styleUrl: './app-shell.component.scss'
})
export class AppShellComponent {
  readonly menuOpen = signal(false);
  constructor(readonly auth: AuthService, private readonly router: Router) {}
  get isAdmin(): boolean { return this.auth.user()?.role === 'admin'; }
  get initials(): string {
    return (this.auth.user()?.name || 'CA').split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase();
  }
  get pageTitle(): string {
    const path = this.router.url.split('?')[0];
    return ({ '/dashboard': 'Overview', '/admin/dashboard': 'Overview', '/appointments': 'Appointments',
      '/enquiries': 'Enquiries', '/assistant': 'Care assistant', '/admin/documents': 'Knowledge base' } as Record<string, string>)[path] || 'Overview';
  }
}
