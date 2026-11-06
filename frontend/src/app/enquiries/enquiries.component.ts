import { Component, OnInit } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';
import { AuthService } from '../core/auth.service';
import { ClinicApiService } from '../core/clinic-api.service';
import { Enquiry, listFrom } from '../core/models';
import { ToastService } from '../core/toast.service';

@Component({
  selector: 'app-enquiries',
  standalone: true,
  imports: [DatePipe, ReactiveFormsModule],
  template: `
    <div class="page-title"><div><div class="eyebrow">{{ admin ? 'PATIENT SUPPORT' : 'WE’RE HERE TO HELP' }}</div><h1>{{ admin ? 'Patient enquiries' : 'Your enquiries' }}</h1><p>{{ admin ? 'Questions from your care community, all in one place.' : 'A question about your care? We’ll make sure it reaches the right person.' }}</p></div></div>
    <div class="enquiry-layout">
      @if (!admin) {
        <section class="form-card">
          <div class="form-top"><span class="form-symbol">✉</span><div><h2>Send us a message</h2><p>Our team usually responds within one business day.</p></div></div>
          <form [formGroup]="form" (ngSubmit)="send()" novalidate>
            <label for="subject">What can we help with?</label>
            <select id="subject" formControlName="subject">
              <option value="">Choose a topic</option><option>Appointments</option><option>Billing and insurance</option><option>Clinic services</option><option>My patient account</option><option>Other question</option>
            </select>
            @if (invalid('subject')) { <small class="error">Please choose a topic.</small> }
            <label for="message">Your message</label>
            <textarea id="message" formControlName="message" rows="5" maxlength="1200" placeholder="Tell us a little more so we can help…"></textarea>
            <div class="field-footer">@if (invalid('message')) { <small class="error">Please enter at least 10 characters.</small> } @else { <small>Please don’t include urgent or emergency medical information.</small> }<span>{{ form.controls.message.value.length || 0 }}/1200</span></div>
            <button type="submit" class="send-button" [disabled]="sending">{{ sending ? 'Sending your message…' : 'Send enquiry →' }}</button>
          </form>
          <div class="urgent-note"><span>♡</span><p><b>Need urgent help?</b><br>For a medical emergency, call your local emergency number.</p></div>
        </section>
      }
      <section class="history-card" [class.full]="admin">
        <div class="history-heading"><div><h2>{{ admin ? 'Enquiry inbox' : 'Your messages' }}</h2><p>{{ enquiries.length }} {{ enquiries.length === 1 ? 'message' : 'messages' }}</p></div><span class="inbox-icon">◷</span></div>
        @if (loading) { <div class="loading"><span></span>Loading messages…</div> }
        @else if (enquiries.length) {
          <div class="enquiry-list">@for (item of enquiries; track item.id) {
            <article class="enquiry-item">
              <span class="item-icon" [class]="item.status">✉</span>
              <div class="item-main">
                <div class="item-meta"><span class="topic">{{ item.subject }}</span><span class="status" [class]="item.status">{{ item.status.replace('_', ' ') }}</span></div>
                @if (admin && item.message) { <p class="message-preview">{{ item.message }}</p> }
                <small>Sent {{ item.created_at | date:'MMM d, y' }}</small>
              </div>
              <span class="item-arrow">›</span>
            </article>
          }</div>
        } @else {
          <div class="empty"><span>✉</span><h3>No messages yet</h3><p>When you reach out, we’ll keep the conversation right here.</p></div>
        }
      </section>
    </div>
  `,
  styleUrl: './enquiries.component.scss'
})
export class EnquiriesComponent implements OnInit {
  enquiries: Enquiry[] = [];
  loading = true;
  sending = false;
  readonly admin: boolean;
  readonly form;
  constructor(private readonly fb: FormBuilder, private readonly api: ClinicApiService, private readonly toast: ToastService, auth: AuthService) {
    this.admin = auth.user()?.role === 'admin';
    this.form = this.fb.nonNullable.group({
      subject: ['', Validators.required],
      message: ['', [Validators.required, Validators.minLength(10), Validators.maxLength(1200)]]
    });
  }
  ngOnInit(): void { this.load(); }
  invalid(field: string): boolean { const control = this.form.get(field); return !!control && control.invalid && control.touched; }
  send(): void {
    this.form.markAllAsTouched();
    if (this.form.invalid || this.sending) return;
    this.sending = true;
    this.api.createEnquiry(this.form.getRawValue()).pipe(finalize(() => this.sending = false)).subscribe({
      next: () => { this.toast.success('Your message is on its way. We’ll be in touch soon.'); this.form.reset(); this.load(); },
      error: (error) => this.toast.error(error.error?.detail ?? 'We couldn’t send your message. Please try again.')
    });
  }
  private load(): void {
    this.loading = true;
    this.api.enquiries().pipe(finalize(() => this.loading = false)).subscribe({
      next: (items) => this.enquiries = listFrom(items).sort((a, b) => b.created_at.localeCompare(a.created_at)),
      error: () => this.toast.error('We couldn’t load your messages right now.')
    });
  }
}
