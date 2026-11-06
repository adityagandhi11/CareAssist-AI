import { Injectable, computed, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';
import { environment } from '../../environments/environment';
import { ApiUser, AuthResponse, User } from './models';

const TOKEN_KEY = 'careassist_access_token';
const USER_KEY = 'careassist_user';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly currentUser = signal<User | null>(this.readUser());
  readonly user = this.currentUser.asReadonly();
  readonly isAuthenticated = computed(() => Boolean(this.currentUser()));

  constructor(private readonly http: HttpClient, private readonly router: Router) {}

  login(credentials: { email: string; password: string }): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${environment.apiUrl}/auth/login`, credentials).pipe(
      tap((response) => this.acceptAuth(response))
    );
  }

  register(data: { name: string; email: string; password: string }): Observable<ApiUser> {
    return this.http.post<ApiUser>(`${environment.apiUrl}/auth/register`, {
      full_name: data.name,
      email: data.email,
      password: data.password
    });
  }

  logout(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    this.currentUser.set(null);
    void this.router.navigate(['/login']);
  }

  token(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  private acceptAuth(response: AuthResponse): void {
    const token = response.access_token;
    if (!token) throw new Error('The server did not return an access token.');
    if (!response.user) throw new Error('The server did not return the signed-in user.');
    const user = this.normalizeUser(response.user);
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    this.currentUser.set(user);
  }

  private normalizeUser(user: ApiUser): User {
    return { id: user.id, name: user.full_name, email: user.email, role: user.role };
  }

  private readUser(): User | null {
    try {
      const saved = localStorage.getItem(USER_KEY);
      if (!saved) return null;
      const user = JSON.parse(saved) as User & { full_name?: string };
      return { ...user, name: user.name ?? user.full_name ?? user.email.split('@')[0] };
    } catch {
      return null;
    }
  }
}
