import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map, Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { ApiList, Appointment, AvailableSlot, ChatMessage, Conversation, DocumentRecord, Enquiry, listFrom, normalizeUtcTimestamp } from './models';

const API = environment.apiUrl;

@Injectable({ providedIn: 'root' })
export class ClinicApiService {
  constructor(private readonly http: HttpClient) {}

  appointments(): Observable<Appointment[]> {
    return this.http.get<Appointment[] | ApiList<Appointment>>(`${API}/appointments`).pipe(map((response) =>
      listFrom(response).map((appointment) => ({
        ...appointment,
        starts_at: normalizeUtcTimestamp(appointment.starts_at),
        ends_at: normalizeUtcTimestamp(appointment.ends_at)
      }))
    ));
  }
  availableSlots(date: string): Observable<AvailableSlot[]> {
    return this.http.get<AvailableSlot[]>(`${API}/appointments/available-slots`, { params: { slot_date: date } });
  }
  createAppointment(data: Pick<Appointment, 'starts_at' | 'ends_at' | 'reason'>): Observable<Appointment> {
    return this.http.post<Appointment>(`${API}/appointments`, data);
  }
  updateAppointment(id: number, status: Appointment['status']): Observable<Appointment> {
    return this.http.patch<Appointment>(`${API}/appointments/${id}`, { status });
  }
  enquiries(): Observable<Enquiry[]> {
    return this.http.get<Enquiry[] | ApiList<Enquiry>>(`${API}/enquiries`).pipe(map((response) =>
      listFrom(response).map((enquiry) => ({ ...enquiry, created_at: normalizeUtcTimestamp(enquiry.created_at) }))
    ));
  }
  createEnquiry(data: Pick<Enquiry, 'subject' | 'message'>): Observable<Enquiry> {
    return this.http.post<Enquiry>(`${API}/enquiries`, data);
  }
  documents(): Observable<DocumentRecord[]> {
    return this.http.get<DocumentRecord[] | ApiList<DocumentRecord>>(`${API}/documents`).pipe(map((response) =>
      listFrom(response).map((document) => ({ ...document, created_at: normalizeUtcTimestamp(document.created_at) }))
    ));
  }
  uploadDocument(file: File): Observable<DocumentRecord> {
    const body = new FormData();
    body.append('file', file);
    return this.http.post<DocumentRecord>(`${API}/documents/upload`, body);
  }
  processDocument(id: number): Observable<DocumentRecord> {
    return this.http.post<DocumentRecord>(`${API}/documents/${id}/process`, {});
  }
  deleteDocument(id: number): Observable<void> {
    return this.http.delete<void>(`${API}/documents/${id}`);
  }
  conversations(): Observable<Conversation[]> {
    return this.http.get<Conversation[] | ApiList<Conversation>>(`${API}/chat/conversations`).pipe(map((response) =>
      listFrom(response).map((conversation) => ({ ...conversation, updated_at: normalizeUtcTimestamp(conversation.updated_at) }))
    ));
  }
  createConversation(title: string): Observable<Conversation> {
    return this.http.post<Conversation>(`${API}/chat/conversations`, { title });
  }
  conversationMessages(id: number): Observable<ChatMessage[]> {
    return this.http.get<ChatMessage[] | ApiList<ChatMessage>>(`${API}/chat/conversations/${id}/messages`).pipe(map((response) =>
      listFrom(response).map((message) => ({
        ...message,
        created_at: normalizeUtcTimestamp(message.created_at),
        sources: message.sources ?? []
      }))
    ));
  }
  ask(id: number, question: string): Observable<ChatMessage[]> {
    return this.http.post<ChatMessage[] | ApiList<ChatMessage>>(`${API}/chat/conversations/${id}/messages`, { question }).pipe(map((response) =>
      listFrom(response).map((message) => ({
        ...message,
        created_at: normalizeUtcTimestamp(message.created_at),
        sources: message.sources ?? []
      }))
    ));
  }
  deleteConversation(id: number): Observable<void> {
    return this.http.delete<void>(`${API}/chat/conversations/${id}`);
  }
}
