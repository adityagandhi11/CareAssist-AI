import { Component, OnInit } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';
import { Appointment, AvailableSlot, listFrom } from '../core/models';
import { ClinicApiService } from '../core/clinic-api.service';
import { ToastService } from '../core/toast.service';
import { AuthService } from '../core/auth.service';

@Component({
  selector: 'app-appointments',
  standalone: true,
  imports: [DatePipe, ReactiveFormsModule],
  template: `
    <div class="page-title"><div><div class="eyebrow">{{ admin ? 'CLINIC SCHEDULE' : 'YOUR CARE' }}</div><h1>{{ admin ? 'Appointments' : 'Your appointments' }}</h1><p>{{ admin ? 'Keep track of patient visits across the clinic.' : 'Make time for you. Find, book, and keep track of your care.' }}</p></div>@if (!admin) { <button class="primary-button" type="button" (click)="showForm = !showForm">{{ showForm ? '× Close' : '＋ Book a visit' }}</button> }</div>
    @if (showForm && !admin) {
      <section class="booking-card">
        <div class="booking-head"><div class="form-icon">＋</div><div><h2>Let’s find a time for you.</h2><p>Share a few details and our team will confirm your visit.</p></div></div>
        <form [formGroup]="form" (ngSubmit)="book()" novalidate>
          <div class="form-grid">
            <div class="field"><label for="visit-date">Choose a date</label><input id="visit-date" type="date" [min]="minDate" formControlName="appointment_date" (change)="onDateChange()" />@if (invalid('appointment_date')) { <small>Choose a date in the future.</small> }</div>
            <div class="field"><label for="visit-time">Available appointment time</label><select id="visit-time" formControlName="starts_at"><option value="">{{ loadingSlots ? 'Checking availability…' : 'Choose an available time' }}</option>@for (slot of availableSlots; track slot.starts_at) { <option [value]="slot.starts_at">{{ slot.starts_at | date:'h:mm a' }}</option> }</select>@if (invalid('starts_at')) { <small>Choose an available time.</small> } @else if (form.controls.appointment_date.value && !loadingSlots && !availableSlots.length) { <small>No times are available for this date. Please try another.</small> }</div>
            <div class="field"><label for="visit-type">Type of care</label><select id="visit-type" formControlName="visit_type"><option value="">Choose a care type</option><option>General consultation</option><option>Primary care</option><option>Dental care</option><option>Women's health</option><option>Mental wellness</option><option>Follow-up visit</option></select>@if (invalid('visit_type')) { <small>Please choose a care type.</small> }</div>
            <div class="field"><label for="visit-reason">What would you like help with?</label><input id="visit-reason" formControlName="reason" placeholder="A short note for your care team (optional)" maxlength="240" /></div>
          </div>
          <div class="form-actions"><span>We’ll follow up to confirm your appointment.</span><button class="primary-button" type="submit" [disabled]="saving">{{ saving ? 'Sending request…' : 'Request appointment →' }}</button></div>
        </form>
      </section>
    }
    <section class="list-card">
      <div class="list-heading"><div><h2>{{ admin ? 'Clinic schedule' : 'Your care calendar' }}</h2><p>{{ appointments.length }} {{ appointments.length === 1 ? 'appointment' : 'appointments' }}{{ admin ? ' on record' : ' on your record' }}</p></div><div class="legend"><span><i class="confirmed"></i> Approved</span><span><i class="pending"></i> Pending</span></div></div>
      @if (loading) { <div class="loading"><span></span>Loading appointments…</div> }
      @else if (appointments.length) {
        <div class="appointment-list">
          @for (item of appointments; track item.id) {
            <article class="appointment-row">
              <div class="date-block"><b>{{ item.starts_at | date:'dd' }}</b><span>{{ item.starts_at | date:'MMM' }}</span></div>
              <div class="visit-info"><div class="visit-tags"><span class="status" [class]="item.status">{{ item.status.replace('_', ' ') }}</span><span>{{ item.starts_at | date:'h:mm a' }} – {{ item.ends_at | date:'h:mm a' }}</span></div><h3>{{ item.reason }}</h3><p>{{ item.starts_at | date:'EEEE, MMMM d, y' }}</p></div>
              @if (admin) { <div class="patient-tag"><span>{{ item.patient_id }}</span>Patient #{{ item.patient_id }}</div> }
              @if (admin && item.status === 'pending') { <button class="row-action" type="button" [disabled]="updatingId === item.id" (click)="setStatus(item, 'approved')">{{ updatingId === item.id ? 'Saving…' : 'Approve' }}</button> }
              @if (admin && item.status === 'approved') { <button class="row-action" type="button" [disabled]="updatingId === item.id" (click)="setStatus(item, 'completed')">{{ updatingId === item.id ? 'Saving…' : 'Complete' }}</button> }
              @if (!admin && (item.status === 'pending' || item.status === 'approved')) { <button class="row-action cancel" type="button" [disabled]="updatingId === item.id" (click)="setStatus(item, 'cancelled')">{{ updatingId === item.id ? 'Saving…' : 'Cancel' }}</button> }
              <span class="row-arrow">↗</span>
            </article>
          }
        </div>
      } @else {
        <div class="empty"><span class="empty-icon">▦</span><h3>No appointments just yet</h3><p>Your booked visits will show up here. Ready when you are.</p>@if (!admin) { <button class="secondary-button" type="button" (click)="showForm = true">Book your first visit</button> }</div>
      }
    </section>
    <p class="privacy"><span>♧</span> Your care details are private and only shared with your care team.</p>
  `,
  styleUrl: './appointments.component.scss'
})
export class AppointmentsComponent implements OnInit {
  appointments: Appointment[] = [];
  availableSlots: AvailableSlot[] = [];
  loading = true;
  loadingSlots = false;
  saving = false;
  updatingId: number | null = null;
  showForm = false;
  readonly admin: boolean;
  readonly minDate = new Date().toISOString().slice(0, 10);
  readonly form;

  constructor(private readonly fb: FormBuilder, private readonly api: ClinicApiService, private readonly toast: ToastService, auth: AuthService) {
    this.admin = auth.user()?.role === 'admin';
    this.form = this.fb.nonNullable.group({
      visit_type: ['', Validators.required],
      appointment_date: ['', Validators.required],
      starts_at: ['', Validators.required],
      reason: ['', [Validators.maxLength(240)]]
    });
  }

  ngOnInit(): void { this.load(); }
  invalid(field: string): boolean { const control = this.form.get(field); return !!control && control.invalid && control.touched; }

  onDateChange(): void {
    const date = this.form.controls.appointment_date.value;
    this.form.controls.starts_at.setValue('');
    this.availableSlots = [];
    if (!date) return;
    this.loadingSlots = true;
    this.api.availableSlots(date).pipe(finalize(() => this.loadingSlots = false)).subscribe({
      next: (slots) => this.availableSlots = listFrom(slots),
      error: () => this.toast.error('We couldn’t check availability. Please try again.')
    });
  }

  book(): void {
    this.form.markAllAsTouched();
    if (this.form.invalid || this.saving) return;
    const { starts_at, visit_type, reason } = this.form.getRawValue();
    const slot = this.availableSlots.find((item) => item.starts_at === starts_at);
    if (!slot) { this.toast.error('Choose an available appointment time.'); return; }
    this.saving = true;
    this.api.createAppointment({
      starts_at: slot.starts_at,
      ends_at: slot.ends_at,
      reason: reason.trim() ? `${visit_type}: ${reason.trim()}` : visit_type
    }).pipe(finalize(() => this.saving = false)).subscribe({
      next: () => { this.toast.success('Your appointment request has been sent.'); this.form.reset(); this.availableSlots = []; this.showForm = false; this.load(); },
      error: (error) => this.toast.error(error.error?.detail ?? 'We couldn’t book your visit. Please try again.')
    });
  }

  setStatus(item: Appointment, status: Appointment['status']): void {
    if (this.updatingId !== null) return;
    this.updatingId = item.id;
    this.api.updateAppointment(item.id, status).pipe(finalize(() => this.updatingId = null)).subscribe({
      next: () => { this.toast.success(status === 'approved' ? 'Appointment approved.' : status === 'completed' ? 'Appointment marked complete.' : 'Appointment cancelled.'); this.load(); },
      error: (error) => this.toast.error(error.error?.detail ?? 'We couldn’t update this appointment.')
    });
  }

  private load(): void {
    this.loading = true;
    this.api.appointments().pipe(finalize(() => this.loading = false)).subscribe({
      next: (items) => this.appointments = listFrom(items).sort((a, b) => b.starts_at.localeCompare(a.starts_at)),
      error: () => this.toast.error('We couldn’t load your appointments. Please refresh to try again.')
    });
  }
}
