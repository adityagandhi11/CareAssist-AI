import { Component, signal } from '@angular/core';
import { AbstractControl, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { AuthService } from '../core/auth.service';
import { ToastService } from '../core/toast.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  template: `
    <main class="auth-page">
      <section class="auth-story">
        <a class="brand" routerLink="/login"><span class="brand-mark">✚</span><span class="brand-name">care<span>assist</span></span></a>
        <div class="story-content">
          <div class="eyebrow"><span></span> CARE THAT FEELS CLOSER</div>
          <h1>Your health journey,<br><em>all in one place.</em></h1>
          <p>Thoughtful care, easier appointments, and trusted answers whenever you need them.</p>
          <div class="story-art">
            <div class="orbit orbit-one"></div><div class="orbit orbit-two"></div>
            <div class="heart">♥</div>
            <div class="float-card appointment-float"><span class="float-icon">✚</span><div><b>Care, connected</b><small>Your health team is here</small></div><span class="float-check">✓</span></div>
            <div class="float-card trust-float"><span class="trust-stars">★★★★★</span><b>Here for you, every step.</b></div>
          </div>
          <div class="story-proof"><span class="proof-avatars"><i>J</i><i>A</i><i>M</i></span><span>Care that starts with <b>you.</b></span></div>
        </div>
        <div class="story-foot"><span>© 2025 CareAssist Health</span><span>Privacy · Support</span></div>
      </section>
      <section class="auth-side">
        <div class="auth-card">
          <div class="mobile-brand"><span class="brand-mark">✚</span><span class="brand-name">care<span>assist</span></span></div>
          <div class="welcome-kicker">{{ registering() ? 'LET’S GET YOU STARTED' : 'WELCOME BACK' }}</div>
          <h2>{{ registering() ? 'Create your account' : 'Good to see you.' }}</h2>
          <p class="form-intro">{{ registering() ? 'Your care, made a little simpler.' : 'Sign in to pick up where you left off.' }}</p>
          <form [formGroup]="form" (ngSubmit)="submit()" novalidate>
            @if (registering()) {
              <label for="name">Full name</label>
              <div class="input-wrap" [class.invalid]="showError('name')"><span class="input-icon">♙</span><input id="name" formControlName="name" autocomplete="name" placeholder="How should we address you?" /></div>
              @if (showError('name')) { <small class="field-error">Please enter your name.</small> }
            }
            <label for="email">Email address</label>
            <div class="input-wrap" [class.invalid]="showError('email')"><span class="input-icon">✉</span><input id="email" type="email" formControlName="email" autocomplete="email" placeholder="you@example.com" /></div>
            @if (showError('email')) { <small class="field-error">Enter a valid email address.</small> }
            <div class="password-label"><label for="password">Password</label>@if (!registering()) { <a href="mailto:support@careassist.health?subject=Password%20help">Forgot password?</a> }</div>
            <div class="input-wrap" [class.invalid]="showError('password')"><span class="input-icon">♙</span><input id="password" [type]="showPassword() ? 'text' : 'password'" formControlName="password" [autocomplete]="registering() ? 'new-password' : 'current-password'" placeholder="At least 8 characters" /><button class="reveal" type="button" (click)="showPassword.set(!showPassword())">{{ showPassword() ? 'Hide' : 'Show' }}</button></div>
            @if (showError('password')) { <small class="field-error">Password must be at least 8 characters.</small> }
            <button type="submit" class="submit-button" [disabled]="loading()">{{ loading() ? (registering() ? 'Creating account…' : 'Signing in…') : (registering() ? 'Create account' : 'Sign in to your account') }} <span>→</span></button>
          </form>
          <div class="switch-auth">{{ registering() ? 'Already have an account?' : 'New to CareAssist?'} <button type="button" (click)="toggleMode()">{{ registering() ? 'Sign in' : 'Create an account' }}</button></div>
          <div class="hipaa-note"><span>♧</span> Your information is private and protected</div>
        </div>
      </section>
    </main>
  `,
  styleUrl: './login.component.scss'
})
export class LoginComponent {
  readonly registering = signal(false);
  readonly loading = signal(false);
  readonly showPassword = signal(false);
  readonly form;

  constructor(
    private readonly fb: FormBuilder,
    private readonly auth: AuthService,
    private readonly router: Router,
    private readonly toast: ToastService
  ) {
    this.form = this.fb.group({
      name: [''],
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(8)]]
    });
  }

  toggleMode(): void {
    this.registering.update((value) => !value);
    this.form.controls.name.setValidators(this.registering() ? [Validators.required, Validators.minLength(2)] : []);
    this.form.controls.password.setValidators([Validators.required, Validators.minLength(this.registering() ? 8 : 1)]);
    this.form.controls.name.updateValueAndValidity();
    this.form.controls.password.updateValueAndValidity();
  }

  showError(field: 'name' | 'email' | 'password'): boolean {
    const control = this.form.get(field);
    return !!control && control.invalid && (control.touched || control.dirty);
  }

  submit(): void {
    this.form.markAllAsTouched();
    if (this.form.invalid || this.loading()) return;
    this.loading.set(true);
    const value = this.form.getRawValue();
    if (this.registering()) {
      this.auth.register({ name: value.name!.trim(), email: value.email!.trim(), password: value.password! })
        .pipe(finalize(() => this.loading.set(false))).subscribe({
          next: () => {
            this.toast.success('Your account is ready. Sign in to continue.');
            this.registering.set(false);
            this.form.controls.name.clearValidators();
            this.form.controls.name.updateValueAndValidity();
          },
          error: (error: HttpErrorResponse) => this.toast.error(this.errorMessage(error))
        });
      return;
    }
    this.auth.login({ email: value.email!.trim(), password: value.password! })
      .pipe(finalize(() => this.loading.set(false))).subscribe({
      next: () => {
        this.toast.success('Welcome back.');
        void this.router.navigate([this.auth.user()?.role === 'admin' ? '/admin/dashboard' : '/dashboard']);
      },
      error: (error: HttpErrorResponse) => this.toast.error(this.errorMessage(error))
    });
  }

  private errorMessage(error: HttpErrorResponse): string {
    return error.error?.detail ?? error.error?.message ?? (error.status === 0
      ? 'Could not reach CareAssist. Check that the clinic API is running and try again.'
      : error.status === 401 ? 'That email and password combination was not recognized.'
      : 'We could not complete your request. Please try again.');
  }
}
