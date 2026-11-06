import { AfterViewChecked, Component, ElementRef, OnInit, ViewChild } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize, switchMap, tap } from 'rxjs';
import { ChatMessage, Conversation, listFrom } from '../core/models';
import { ClinicApiService } from '../core/clinic-api.service';
import { ToastService } from '../core/toast.service';

@Component({
  selector: 'app-assistant',
  standalone: true,
  imports: [DatePipe, ReactiveFormsModule],
  template: `
    <div class="chat-page">
      @if (historyOpen) { <button type="button" class="history-scrim" aria-label="Close conversation history" (click)="historyOpen = false"></button> }
      <aside class="history" [class.mobile-open]="historyOpen">
        <div class="history-head"><div><span class="history-label">YOUR CARE ASSISTANT</span><h2>Conversations</h2></div><button class="new-chat" type="button" aria-label="Start a new chat" title="New conversation" (click)="newChat()">＋</button></div>
        <div class="history-search"><span>⌕</span><input type="search" placeholder="Find a conversation" [value]="search" (input)="search = inputValue($event)" /></div>
        <button class="start-chat" type="button" (click)="newChat()"><span>＋</span> Start a new conversation</button>
        <div class="history-list">
          <div class="history-section">RECENT</div>
          @if (historyLoading) { <div class="history-loading">Loading conversations…</div> }
          @else {
            @for (conversation of filteredConversations; track conversation.id) {
              <div class="history-entry">
                <button type="button" class="history-item" [class.selected]="conversation.id === conversationId" (click)="openConversation(conversation)">
                  <span class="chat-mark">✧</span><span class="history-item-text"><b>{{ conversation.title || 'Care conversation' }}</b><small>{{ conversation.updated_at | date:'MMM d' }}</small></span>
                </button>
                <button type="button" class="delete-chat" title="Delete conversation" [attr.aria-label]="'Delete ' + conversation.title" (click)="deleteConversation(conversation, $event)">×</button>
              </div>
            }
            @if (!filteredConversations.length) { <div class="no-history">Your conversations will appear here.</div> }
          }
        </div>
        <div class="history-foot"><span>♧</span> Private and secure conversations</div>
      </aside>
      <section class="chat-main">
        <header class="chat-header"><div class="assistant-avatar">✧<i></i></div><div><h1>CareAssist <span>AI</span></h1><p><i></i> Your caring clinic companion</p></div><button type="button" class="more-button" title="Conversation history" aria-label="Open conversation history" (click)="historyOpen = !historyOpen">☰</button></header>
        <div class="conversation" #conversationBody>
          @if (loadingConversation) { <div class="chat-loading"><span></span>Opening your conversation…</div> }
          @else if (messages.length === 0) {
            <div class="welcome-chat">
              <div class="welcome-icon">✧</div><div class="welcome-label">HERE WHEN YOU NEED US</div><h2>A little more clarity,<br><em>one question at a time.</em></h2>
              <p>I can help you explore clinic services, appointment guidance, and trusted information from your care team.</p>
              <div class="suggestions">
                <button type="button" (click)="askSuggestion('What services does the clinic offer?')"><span>♡</span> What services does the clinic offer? <i>↗</i></button>
                <button type="button" (click)="askSuggestion('How do I prepare for an appointment?')"><span>▦</span> How do I prepare for an appointment? <i>↗</i></button>
                <button type="button" (click)="askSuggestion('What should I bring to my first visit?')"><span>✦</span> What should I bring to my first visit? <i>↗</i></button>
              </div>
            </div>
          } @else {
            <div class="message-stack">
              @for (message of messages; track message.id) {
                <article class="message" [class.user-message]="message.role === 'user'">
                  @if (message.role === 'assistant') { <span class="message-avatar">✧</span> }
                  <div class="bubble-wrap"><div class="bubble">{{ message.content }}</div>
                    @if (message.role === 'assistant' && message.sources.length) {
                      <div class="sources"><div class="sources-label"><span>▤</span> GROUNDED IN CLINIC RESOURCES</div>
                        @for (source of message.sources; track $index) { <div class="source-card"><span class="source-mark">▤</span><span><b>{{ source }}</b></span><span class="source-check">✓</span></div> }
                      </div>
                    }
                    @if (message.role === 'assistant' && !message.sources.length) { <div class="no-source">No clinic document was available to cite for this answer.</div> }
                    <small class="time">{{ message.created_at | date:'shortTime' }}</small>
                  </div>
                </article>
              }
              @if (sending) { <article class="message"><span class="message-avatar">✧</span><div class="typing"><i></i><i></i><i></i><span>Finding a helpful answer…</span></div></article> }
            </div>
          }
        </div>
        <div class="composer-area">
          <form class="composer" (ngSubmit)="send()"><textarea rows="1" [formControl]="draft" (keydown)="onKeyDown($event)" placeholder="Ask a question about your care…" aria-label="Write your question"></textarea><button type="submit" [disabled]="!draft.valid || sending" aria-label="Send message" title="Send message">↑</button></form>
          <div class="composer-foot"><span><i></i> Answers draw on trusted clinic resources</span><small>CareAssist can be helpful, but it’s not a substitute for medical advice.</small></div>
        </div>
      </section>
    </div>
  `,
  styleUrl: './assistant.component.scss'
})
export class AssistantComponent implements OnInit, AfterViewChecked {
  @ViewChild('conversationBody') private conversationBody?: ElementRef<HTMLDivElement>;
  conversations: Conversation[] = [];
  messages: ChatMessage[] = [];
  conversationId?: number;
  search = '';
  historyLoading = true;
  historyOpen = false;
  loadingConversation = false;
  sending = false;
  shouldScroll = false;
  readonly draft = new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.maxLength(4000)] });
  constructor(private readonly api: ClinicApiService, private readonly toast: ToastService) {}
  get filteredConversations(): Conversation[] {
    const query = this.search.trim().toLowerCase();
    return query ? this.conversations.filter((item) => item.title.toLowerCase().includes(query)) : this.conversations;
  }
  ngOnInit(): void { this.loadHistory(); }
  ngAfterViewChecked(): void {
    if (this.shouldScroll && this.conversationBody) {
      this.conversationBody.nativeElement.scrollTop = this.conversationBody.nativeElement.scrollHeight;
      this.shouldScroll = false;
    }
  }
  inputValue(event: Event): string { return (event.target as HTMLInputElement).value; }
  onKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); this.send(); }
  }
  askSuggestion(text: string): void { this.draft.setValue(text); this.send(); }
  newChat(): void {
    this.conversationId = undefined;
    this.messages = [];
    this.loadingConversation = false;
    this.historyOpen = false;
    this.draft.setValue('');
  }
  openConversation(conversation: Conversation): void {
    if (conversation.id === this.conversationId) return;
    this.conversationId = conversation.id;
    this.historyOpen = false;
    this.loadingConversation = true;
    this.messages = [];
    this.api.conversationMessages(conversation.id).pipe(finalize(() => this.loadingConversation = false)).subscribe({
      next: (messages) => { this.messages = listFrom(messages).map((message) => ({ ...message, sources: message.sources ?? [] })); this.shouldScroll = true; },
      error: () => this.toast.error('We couldn’t open that conversation. Please try again.')
    });
  }
  deleteConversation(conversation: Conversation, event: Event): void {
    event.stopPropagation();
    if (!window.confirm(`Delete "${conversation.title}" and its messages?`)) return;
    this.api.deleteConversation(conversation.id).subscribe({
      next: () => {
        this.conversations = this.conversations.filter((item) => item.id !== conversation.id);
        if (this.conversationId === conversation.id) this.newChat();
        this.toast.success('Conversation deleted.');
      },
      error: (error) => this.toast.error(error.error?.detail ?? 'We couldn’t delete that conversation.')
    });
  }
  send(): void {
    const question = this.draft.value.trim();
    if (!question || question.length < 3 || question.length > 4000 || this.sending) return;
    this.draft.setValue('');
    this.sending = true;
    const optimistic: ChatMessage = {
      id: Date.now(),
      conversation_id: this.conversationId ?? 0,
      role: 'user',
      content: question,
      created_at: new Date().toISOString(),
      sources: []
    };
    this.messages = [...this.messages, optimistic];
    this.shouldScroll = true;
    const request = this.conversationId
      ? this.api.ask(this.conversationId, question)
      : this.api.createConversation(question.slice(0, 60)).pipe(
          tap((conversation) => this.conversationId = conversation.id),
          switchMap((conversation) => this.api.ask(conversation.id, question))
        );
    request.pipe(finalize(() => { this.sending = false; this.shouldScroll = true; })).subscribe({
      next: (messages) => {
        this.messages = listFrom(messages).map((message) => ({ ...message, sources: message.sources ?? [] }));
        this.loadHistory();
      },
      error: (error) => this.toast.error(error.error?.detail ?? 'The care assistant is unavailable. Please try again in a moment.')
    });
  }
  private loadHistory(): void {
    this.historyLoading = true;
    this.api.conversations().pipe(finalize(() => this.historyLoading = false)).subscribe({
      next: (items) => this.conversations = listFrom(items).sort((a, b) => b.updated_at.localeCompare(a.updated_at)),
      error: () => this.toast.error('We couldn’t load your conversation history.')
    });
  }
}
