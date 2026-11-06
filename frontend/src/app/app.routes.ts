import { Routes } from '@angular/router';
import { AppShellComponent } from './layout/app-shell.component';
import { LoginComponent } from './auth/login.component';
import { DashboardComponent } from './dashboard/dashboard.component';
import { AppointmentsComponent } from './appointments/appointments.component';
import { EnquiriesComponent } from './enquiries/enquiries.component';
import { AssistantComponent } from './assistant/assistant.component';
import { DocumentsComponent } from './admin/documents.component';
import { adminGuard, authGuard, dashboardGuard, guestGuard, patientGuard } from './core/guards';

export const routes: Routes = [
  { path: 'login', component: LoginComponent, canActivate: [guestGuard], title: 'Sign in · CareAssist' },
  { path: '', component: AppShellComponent, canActivate: [authGuard], children: [
    { path: 'dashboard', component: DashboardComponent, canActivate: [dashboardGuard], title: 'Overview · CareAssist' },
    { path: 'appointments', component: AppointmentsComponent, title: 'Appointments · CareAssist' },
    { path: 'enquiries', component: EnquiriesComponent, title: 'Enquiries · CareAssist' },
    { path: 'assistant', component: AssistantComponent, canActivate: [patientGuard], title: 'Care assistant · CareAssist' },
    { path: 'admin/dashboard', component: DashboardComponent, canActivate: [adminGuard], title: 'Clinic overview · CareAssist' },
    { path: 'admin/documents', component: DocumentsComponent, canActivate: [adminGuard], title: 'Knowledge base · CareAssist' },
    { path: '', pathMatch: 'full', redirectTo: 'dashboard' }
  ] },
  { path: '**', redirectTo: '' }
];
