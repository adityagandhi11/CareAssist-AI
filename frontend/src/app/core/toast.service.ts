import { Injectable, signal } from '@angular/core';

export interface ToastMessage { id: number; text: string; kind: 'success' | 'error' | 'info'; }

@Injectable({ providedIn: 'root' })
export class ToastService {
  readonly messages = signal<ToastMessage[]>([]);
  private sequence = 0;

  success(text: string): void { this.show(text, 'success'); }
  error(text: string): void { this.show(text, 'error'); }
  info(text: string): void { this.show(text, 'info'); }
  dismiss(id: number): void { this.messages.update((all) => all.filter((item) => item.id !== id)); }

  private show(text: string, kind: ToastMessage['kind']): void {
    const id = ++this.sequence;
    this.messages.update((all) => [...all, { id, text, kind }]);
    window.setTimeout(() => this.dismiss(id), 4500);
  }
}
