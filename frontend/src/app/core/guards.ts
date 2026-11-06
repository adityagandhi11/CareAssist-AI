import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';

export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  if (auth.isAuthenticated()) return true;
  return inject(Router).createUrlTree(['/login']);
};

export const guestGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  if (!auth.isAuthenticated()) return true;
  return inject(Router).createUrlTree([auth.user()?.role === 'admin' ? '/admin/dashboard' : '/dashboard']);
};

export const adminGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  if (auth.isAuthenticated() && auth.user()?.role === 'admin') return true;
  return inject(Router).createUrlTree([auth.isAuthenticated() ? '/dashboard' : '/login']);
};

export const patientGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  if (auth.isAuthenticated() && auth.user()?.role !== 'admin') return true;
  return inject(Router).createUrlTree([auth.isAuthenticated() ? '/admin/dashboard' : '/login']);
};

export const dashboardGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  if (auth.user()?.role !== 'admin') return true;
  return inject(Router).createUrlTree(['/admin/dashboard']);
};
