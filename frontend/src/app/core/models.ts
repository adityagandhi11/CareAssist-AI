export type UserRole = 'patient' | 'admin';
export type AppointmentStatus = 'pending' | 'approved' | 'completed' | 'cancelled';
export type EnquiryStatus = 'open' | 'in_progress' | 'resolved' | 'closed';

export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
}

export interface ApiUser {
  id: number;
  full_name: string;
  email: string;
  role: UserRole;
}

export interface AuthResponse {
  access_token?: string;
  user?: ApiUser;
  token_type?: string;
}

export interface Appointment {
  id: number;
  patient_id: number;
  starts_at: string;
  ends_at: string;
  reason: string;
  status: AppointmentStatus;
}

export interface AvailableSlot {
  starts_at: string;
  ends_at: string;
}

export interface Enquiry {
  id: number;
  patient_id: number;
  subject: string;
  message: string;
  status: EnquiryStatus;
  created_at: string;
}

export interface DocumentRecord {
  id: number;
  filename: string;
  status: 'pending' | 'processed' | 'failed';
  processing_error: string | null;
  content_hash: string | null;
  page_count: number;
  created_at: string;
}

export interface ChatMessage {
  id: number;
  conversation_id: number;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  sources: string[];
}

export interface Conversation {
  id: number;
  patient_id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ApiList<T> {
  items?: T[];
  results?: T[];
  data?: T[];
}

export function normalizeUtcTimestamp(value: string): string {
  return value && !/(?:Z|[+-]\d{2}:\d{2})$/i.test(value) ? `${value}Z` : value;
}

export function listFrom<T>(response: T[] | ApiList<T> | null | undefined): T[] {
  if (Array.isArray(response)) return response;
  return response?.items ?? response?.results ?? response?.data ?? [];
}
