import { Component, OnInit } from '@angular/core';
import { DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { Appointment, Enquiry, listFrom } from '../core/models';
import { ClinicApiService } from '../core/clinic-api.service';
import { AuthService } from '../core/auth.service';
import { ToastService } from '../core/toast.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [DatePipe, RouterLink],
  template: `
    @if (admin) {
      <div class="page-heading"><div><div class="greeting">CLINIC OVERVIEW</div><h1>Your clinic at a glance.</h1><p>Here’s what’s happening across your care community.</p></div><a class="button primary" routerLink="/admin/documents">＋ Add a document</a></div>
      <section class="admin-welcome"><div class="welcome-copy"><span class="overline">CAREASSIST WORKSPACE</span><h2>Good {{ dayPart }}, {{ firstName }}.</h2><p>A healthier day starts with a little clarity. Here’s your clinic’s latest activity.</p></div><div class="welcome-art"><span>✚</span><i>✦</i><b>✧</b></div></section>
      <section class="stats-grid">
        <article class="stat-card"><span class="stat-icon mint">▦</span><div><small>Appointments</small><strong>{{ appointments.length }}</strong></div><span class="stat-note">all time</span></article>
        <article class="stat-card"><span class="stat-icon peach">◷</span><div><small>Upcoming visits</small><strong>{{ upcomingCount }}</strong></div><span class="stat-note">scheduled</span></article>
        <article class="stat-card"><span class="stat-icon lavender">✉</span><div><small>Open enquiries</small><strong>{{ openEnquiries }}</strong></div><span class="stat-note">need attention</span></article>
        <article class="stat-card"><span class="stat-icon blue">▤</span><div><small>Care resources</small><strong>Knowledge</strong></div><a class="stat-link" routerLink="/admin/documents">Manage →</a></article>
      </section>
      <section class="content-grid">
        <article class="panel appointments-panel"><div class="panel-heading"><div><h3>Recent appointments</h3><p>Your clinic schedule, in one place.</p></div><a routerLink="/appointments">View all <span>→</span></a></div>
          @if (loading) { <div class="loading-row"><span class="spinner"></span> Loading appointments…</div> }
          @else if (appointments.length) { <div class="table-wrap"><table><thead><tr><th>PATIENT</th><th>DATE &amp; TIME</th><th>CARE TYPE</th><th>STATUS</th></tr></thead><tbody>
            @for (item of appointments.slice(0, 5); track item.id) { <tr><td><span class="patient-name"><i>{{ item.patient_id }}</i>Patient #{{ item.patient_id }}</span></td><td>{{ item.starts_at | date:'MMM d, y' }}<small>{{ item.starts_at | date:'h:mm a' }}</small></td><td>{{ item.reason }}</td><td><span class="status" [class]="item.status">{{ item.status.replace('_', ' ') }}</span></td></tr> }
          </tbody></table></div> }
          @else { <div class="empty-state"><span>▦</span><b>No appointments yet</b><p>New appointments will appear here as soon as they’re booked.</p><a class="button subtle" routerLink="/appointments">View appointments</a></div> }
        </article>
        <aside class="panel quick-panel"><div class="panel-heading"><div><h3>Quick actions</h3><p>Keep care moving forward.</p></div></div><a class="quick-link" routerLink="/appointments"><span class="quick-icon mint">＋</span><span><b>View appointments</b><small>Browse your clinic schedule</small></span><i>→</i></a><a class="quick-link" routerLink="/enquiries"><span class="quick-icon lavender">✉</span><span><b>Review enquiries</b><small>Respond to patient questions</small></span><i>→</i></a><a class="quick-link" routerLink="/admin/documents"><span class="quick-icon blue">▤</span><span><b>Knowledge base</b><small>Manage trusted care resources</small></span><i>→</i></a></aside>
      </section>
    } @else {
      <div class="page-heading"><div><div class="greeting">YOUR CARE, IN ONE PLACE</div><h1>Good {{ dayPart }}, {{ firstName }}<span class="wave">✦</span></h1><p>A little easier, a little more personal. Your care starts here.</p></div><a class="button primary" routerLink="/appointments"><span>＋</span> Book an appointment</a></div>
      <section class="welcome-banner"><div class="banner-copy"><span class="banner-label"><span>✦</span> A HEALTHIER YOU, EVERY DAY</span><h2>Here for you, every step<br>of the way.</h2><p>Appointments, answers, and a team that cares — all just a click away.</p><a routerLink="/assistant">Meet your care assistant <span>→</span></a></div><div class="banner-illustration"><div class="sun"></div><div class="circle-back"></div><div class="plant plant-one">⌁</div><div class="person"><span class="person-head"></span><span class="person-body"></span></div><div class="plant plant-two">♧</div><div class="banner-sticker">✚</div></div></section>
      <section class="stats-grid patient-stats">
        <article class="stat-card"><span class="stat-icon mint">▦</span><div><small>Upcoming appointments</small><strong>{{ upcomingCount }}</strong></div><a class="stat-link" routerLink="/appointments">View visits →</a></article>
        <article class="stat-card"><span class="stat-icon peach">◷</span><div><small>Appointments attended</small><strong>{{ completedCount }}</strong></div><span class="stat-note">your care journey</span></article>
        <article class="stat-card"><span class="stat-icon lavender">✉</span><div><small>Active enquiries</small><strong>{{ openEnquiries }}</strong></div><a class="stat-link" routerLink="/enquiries">View enquiries →</a></article>
      </section>
      <section class="content-grid patient-content">
        <article class="panel appointments-panel"><div class="panel-heading"><div><h3>Your next appointment</h3><p>A little time set aside for your wellbeing.</p></div><a routerLink="/appointments">All appointments <span>→</span></a></div>
          @if (loading) { <div class="loading-row"><span class="spinner"></span> Loading your care…</div> }
          @else if (nextAppointment) { <div class="next-appointment"><div class="date-tile"><b>{{ nextAppointment.starts_at | date:'dd' }}</b><span>{{ nextAppointment.starts_at | date:'MMM' }}</span></div><div class="next-details"><span class="status" [class]="nextAppointment.status">{{ nextAppointment.status.replace('_', ' ') }}</span><h4>{{ nextAppointment.reason }}</h4><p>{{ nextAppointment.starts_at | date:'EEEE, MMMM d, y' }} <span>·</span> {{ nextAppointment.starts_at | date:'h:mm a' }} – {{ nextAppointment.ends_at | date:'h:mm a' }}</p><small>CareAssist clinic</small></div><span class="calendar-mark">▦</span></div> }
          @else { <div class="empty-state compact"><span>♡</span><b>Nothing on your calendar just yet</b><p>When you’re ready, book a visit and we’ll be here.</p><a class="button subtle" routerLink="/appointments">Find an appointment</a></div> }
        </article>
        <aside class="panel care-tips"><span class="tip-icon">✧</span><div class="tip-label">YOUR CARE COMPANION</div><h3>Questions on your mind?</h3><p>Your AI care assistant can help with clinic services, appointment guidance, and everyday health questions.</p><a routerLink="/assistant">Ask CareAssist <span>→</span></a><div class="tip-decoration">✳</div></aside>
      </section>
    }
  `,
  styleUrl: './dashboard.component.scss'
})
export class DashboardComponent implements OnInit {
  appointments: Appointment[] = [];
  enquiries: Enquiry[] = [];
  loading = true;
  readonly admin: boolean;
  constructor(private readonly api: ClinicApiService, private readonly auth: AuthService, private readonly toast: ToastService) {
    this.admin = auth.user()?.role === 'admin';
  }
  get firstName(): string { return (this.auth.user()?.name || 'there').trim().split(/\s+/)[0]; }
  get dayPart(): string { const h = new Date().getHours(); return h < 12 ? 'morning' : h < 17 ? 'afternoon' : 'evening'; }
  get upcoming(): Appointment[] { return this.appointments.filter((item) => item.status !== 'cancelled' && new Date(item.starts_at) >= new Date()); }
  get upcomingCount(): number { return this.upcoming.length; }
  get completedCount(): number { return this.appointments.filter((item) => item.status === 'completed').length; }
  get openEnquiries(): number { return this.enquiries.filter((item) => item.status === 'open' || item.status === 'in_progress').length; }
  get nextAppointment(): Appointment | undefined { return [...this.upcoming].sort((a, b) => a.starts_at.localeCompare(b.starts_at))[0]; }
  initials(name: string): string { return name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase(); }

  ngOnInit(): void {
    this.api.appointments().pipe(finalize(() => this.loading = false)).subscribe({
      next: (items) => this.appointments = listFrom(items).sort((a, b) => a.starts_at.localeCompare(b.starts_at)),
      error: () => this.toast.error('We couldn’t load appointments right now.')
    });
    this.api.enquiries().subscribe({
      next: (items) => this.enquiries = listFrom(items),
      error: () => { /* Dashboard appointment data remains available if enquiries are offline. */ }
    });
  }
}
