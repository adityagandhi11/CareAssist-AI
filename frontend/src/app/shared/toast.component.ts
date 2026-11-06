import { Component, inject } from '@angular/core';
import { ToastService } from '../core/toast.service';

@Component({
  selector: 'app-toast',
  standalone: true,
  template: `
    <div class="toast-stack" aria-live="polite">
      @for (toast of service.messages(); track toast.id) {
        <div class="toast" [class]="toast.kind" role="status">
          <span class="toast-mark">{{ toast.kind === 'success' ? '✓' : toast.kind === 'error' ? '!' : 'i' }}</span>
          <span>{{ toast.text }}</span>
          <button type="button" aria-label="Dismiss notification" (click)="service.dismiss(toast.id)">×</button>
        </div>
      }
    </div>
  `,
  styles: [`
    .toast-stack { position: fixed; z-index: 1000; right: 24px; top: 24px; display: grid; gap: 10px; width: min(390px, calc(100vw - 32px)); }
    .toast { display: flex; align-items: center; gap: 12px; padding: 14px 16px; background: #fff; border: 1px solid #e7e9ed; border-radius: 14px; box-shadow: 0 12px 35px #182b3a1c; color: #233346; font-size: 13px; animation: enter .2s ease-out; }
    .toast-mark { display: grid; place-items: center; width: 23px; height: 23px; border-radius: 50%; background: #e7f6f1; color: #118365; font-weight: 700; flex: 0 0 auto; }
    .toast.error .toast-mark { background: #fff0ef; color: #d34b44; } .toast.info .toast-mark { background: #eef4ff; color: #4577d4; }
    .toast button { margin-left: auto; border: 0; background: none; color: #8a96a5; font-size: 21px; cursor: pointer; }
    @keyframes enter { from { opacity: 0; transform: translateY(-7px); } to { opacity: 1; transform: translateY(0); } }
  `]
})
export class ToastComponent {
  readonly service = inject(ToastService);
}
