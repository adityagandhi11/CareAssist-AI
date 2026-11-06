import { Component, OnInit } from '@angular/core';
import { DatePipe } from '@angular/common';
import { finalize } from 'rxjs';
import { ClinicApiService } from '../core/clinic-api.service';
import { DocumentRecord, listFrom } from '../core/models';
import { ToastService } from '../core/toast.service';

@Component({
  selector: 'app-documents',
  standalone: true,
  imports: [DatePipe],
  template: `
    <div class="page-title"><div><div class="eyebrow">TRUSTED CARE CONTENT</div><h1>Knowledge base</h1><p>Keep CareAssist grounded in the right clinic information.</p></div><span class="secure"><i></i> Private workspace</span></div>
    <section class="upload-card">
      <div class="upload-heading"><span class="upload-symbol">↑</span><div><h2>Add a care resource</h2><p>Upload clinic documents so CareAssist can use them to answer patient questions.</p></div></div>
      <label class="drop-zone" [class.dragging]="dragging" [class.has-file]="selectedFile" (dragover)="onDragOver($event)" (dragleave)="dragging = false" (drop)="onDrop($event)">
        <input type="file" accept=".pdf,.txt" (change)="onFile($event)" aria-label="Choose a care resource file" />
        <span class="file-icon">{{ selectedFile ? '▤' : '⇧' }}</span>
        @if (selectedFile) { <b>{{ selectedFile.name }}</b><small>{{ (selectedFile.size / 1024 / 1024).toFixed(1) }} MB · Click to choose a different file</small> }
        @else { <b>Drop a file here, or <em>browse files</em></b><small>PDF or text files · Up to 10 MB</small> }
      </label>
      <div class="upload-controls"><button class="upload-button" type="button" (click)="upload()" [disabled]="!selectedFile || uploading">{{ uploading ? 'Uploading…' : 'Upload resource →' }}</button></div>
      <p class="upload-note"><span>♧</span> Files are securely stored and only used to support relevant patient questions.</p>
    </section>
    <section class="documents-card">
      <div class="documents-head"><div><h2>Uploaded resources</h2><p>{{ documents.length }} {{ documents.length === 1 ? 'resource' : 'resources' }} available to the assistant</p></div><button class="refresh" type="button" (click)="load()" [disabled]="loading" aria-label="Refresh resources">↻</button></div>
      @if (loading) { <div class="loading"><span></span>Loading your resources…</div> }
      @else if (documents.length) {
        <div class="resource-list">
          @for (doc of documents; track doc.id) {
            <article class="resource-row">
              <span class="doc-type" [class]="fileType(doc.filename)">{{ fileType(doc.filename) }}</span>
              <div class="resource-info"><b>{{ doc.filename }}</b><small>Added {{ doc.created_at | date:'MMM d, y' }} <i>·</i> {{ doc.page_count }} {{ doc.page_count === 1 ? 'page' : 'pages' }}</small>@if (doc.processing_error) { <small class="process-error">{{ doc.processing_error }}</small> }</div>
              <span class="ready" [class]="doc.status"><i></i>{{ doc.status }}</span>
              @if (doc.status !== 'processed') { <button class="row-action process" type="button" (click)="process(doc)" [disabled]="processingId === doc.id">{{ processingId === doc.id ? 'Processing…' : 'Process' }}</button> }
              <button class="row-action delete" type="button" (click)="remove(doc)" [disabled]="deletingId === doc.id">{{ deletingId === doc.id ? 'Removing…' : 'Delete' }}</button>
            </article>
          }
        </div>
      } @else {
        <div class="empty"><span>▤</span><h3>Your knowledge base is ready to grow</h3><p>Add trusted clinic resources to help the assistant give grounded, helpful answers.</p></div>
      }
    </section>
  `,
  styleUrl: './documents.component.scss'
})
export class DocumentsComponent implements OnInit {
  documents: DocumentRecord[] = [];
  selectedFile: File | null = null;
  loading = true;
  uploading = false;
  dragging = false;
  processingId: number | null = null;
  deletingId: number | null = null;
  constructor(private readonly api: ClinicApiService, private readonly toast: ToastService) {}
  ngOnInit(): void { this.load(); }
  onDragOver(event: DragEvent): void { event.preventDefault(); this.dragging = true; }
  onDrop(event: DragEvent): void { event.preventDefault(); this.dragging = false; const file = event.dataTransfer?.files.item(0); if (file) this.setFile(file); }
  onFile(event: Event): void { const file = (event.target as HTMLInputElement).files?.item(0); if (file) this.setFile(file); }
  fileType(name: string): string { return name.split('.').pop()?.toLowerCase() === 'pdf' ? 'PDF' : 'TXT'; }
  upload(): void {
    if (!this.selectedFile || this.uploading) return;
    this.uploading = true;
    this.api.uploadDocument(this.selectedFile).pipe(finalize(() => this.uploading = false)).subscribe({
      next: () => { this.toast.success('Your resource was uploaded successfully.'); this.selectedFile = null; this.load(); },
      error: (error) => this.toast.error(error.error?.detail ?? 'We couldn’t upload that file. Please try again.')
    });
  }
  process(doc: DocumentRecord): void {
    if (this.processingId !== null) return;
    this.processingId = doc.id;
    this.api.processDocument(doc.id).pipe(finalize(() => this.processingId = null)).subscribe({
      next: () => { this.toast.success(`${doc.filename} is ready for grounded answers.`); this.load(); },
      error: (error) => this.toast.error(error.error?.detail ?? `We couldn’t process ${doc.filename}.`)
    });
  }
  remove(doc: DocumentRecord): void {
    if (this.deletingId !== null || !window.confirm(`Remove "${doc.filename}" from the knowledge base?`)) return;
    this.deletingId = doc.id;
    this.api.deleteDocument(doc.id).pipe(finalize(() => this.deletingId = null)).subscribe({
      next: () => { this.toast.success('The resource was removed.'); this.load(); },
      error: (error) => this.toast.error(error.error?.detail ?? `We couldn’t remove ${doc.filename}.`)
    });
  }
  load(): void {
    this.loading = true;
    this.api.documents().pipe(finalize(() => this.loading = false)).subscribe({
      next: (items) => this.documents = listFrom(items).sort((a, b) => b.created_at.localeCompare(a.created_at)),
      error: () => this.toast.error('We couldn’t load your resources. Please refresh to try again.')
    });
  }
  private setFile(file: File): void {
    const allowed = /\.(pdf|txt)$/i.test(file.name);
    if (!allowed) { this.toast.error('The clinic API accepts PDF and TXT documents only.'); return; }
    if (file.size > 10 * 1024 * 1024) { this.toast.error('This file is larger than the clinic’s 10 MB upload limit.'); return; }
    this.selectedFile = file;
  }
}
