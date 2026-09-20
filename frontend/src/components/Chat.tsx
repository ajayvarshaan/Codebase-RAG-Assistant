import React, { useEffect, useRef, type FormEvent, type KeyboardEvent } from "react";
import ReactMarkdown from "react-markdown";
import "./Chat.css";

type ChatSource = {
  chunk_id: number;
  file_id: number;
  file_path: string;
  start_line: number;
  end_line: number;
};

type ChatMessage = {
  id: number;
  question: string;
  answer: string;
  sources: ChatSource[];
};

type Props = {
  chatHistory: ChatMessage[];
  question: string;
  chatMessage: string;
  onQuestionChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onClearChat: () => void;
  onOpenSource: (source: ChatSource) => void;
};

/* SVG icons — no emoji, no symbols */
const IconSend = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
  </svg>
);

const IconAI = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3" />
    <path d="M12 2v3M12 19v3M4.22 4.22l2.12 2.12M17.66 17.66l2.12 2.12M2 12h3M19 12h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12" />
  </svg>
);

const IconUser = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
);

const IconSource = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
  </svg>
);

export default function Chat({
  chatHistory,
  question,
  chatMessage,
  onQuestionChange,
  onSubmit,
  onClearChat,
  onOpenSource,
}: Props) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isThinking = chatMessage === "Thinking...";

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory, isThinking]);

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onQuestionChange(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (question.trim() && !isThinking) {
        e.currentTarget.form?.requestSubmit();
      }
    }
  };

  return (
    <div className="cb-wrap">

      {/* Header */}
      <div className="cb-header">
        <div className="cb-header-left">
          <div className="cb-logo">
            <IconAI />
          </div>
          <div>
            <div className="cb-title">Codebase Assistant</div>
            <div className="cb-status">
              <span className="cb-status-dot" />
              {isThinking ? "Thinking" : "Ready"}
            </div>
          </div>
        </div>

        {chatHistory.length > 0 && (
          <button type="button" className="cb-clear-btn" onClick={onClearChat}>
            Clear chat
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="cb-messages">
        {chatHistory.length === 0 && !isThinking ? (
          <div className="cb-empty">
            <div className="cb-empty-icon">
              <IconAI />
            </div>
            <p className="cb-empty-title">Ask about your codebase</p>
            <p className="cb-empty-sub">
              Search the indexed codebase and get precise answers with source references.
            </p>
          </div>
        ) : (
          <>
            {chatHistory.map((chat) => (
              <React.Fragment key={chat.id}>

                {/* User message */}
                <div className="cb-row cb-user-row">
                  <div className="cb-user-meta">
                    <span className="cb-user-label">You</span>
                    <div className="cb-user-avatar"><IconUser /></div>
                  </div>
                  <div className="cb-user-bubble">{chat.question}</div>
                </div>

                {/* AI message */}
                <div className="cb-row cb-ai-row">
                  <div className="cb-ai-inner">
                    <div className="cb-ai-avatar"><IconAI /></div>
                    <div className="cb-ai-body">
                      <div className="cb-ai-name">Codebase Assistant</div>
                      {chat.answer === "" ? (
                        <div className="cb-thinking">
                          <span className="cb-thinking-dot" />
                          <span className="cb-thinking-dot" />
                          <span className="cb-thinking-dot" />
                        </div>
                      ) : (
                        <>
                          <div className="cb-ai-text">
                            <ReactMarkdown>{chat.answer}</ReactMarkdown>
                          </div>
                          {chat.sources.length > 0 && (
                            <div className="cb-sources">
                              <div className="cb-sources-label">📎 Sources</div>
                              {chat.sources.map((source) => (
                                <button
                                  key={source.chunk_id}
                                  type="button"
                                  className="cb-source-chip"
                                  onClick={() => onOpenSource(source)}
                                >
                                  <IconSource />
                                  {source.file_path}:{source.start_line}–{source.end_line}
                                </button>
                              ))}
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                </div>

              </React.Fragment>
            ))}


          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="cb-input-area">
        <form className="cb-form" onSubmit={onSubmit}>
          <div className="cb-input-box">
            <textarea
              ref={textareaRef}
              className="cb-textarea"
              placeholder="Ask anything about your codebase..."
              value={question}
              rows={1}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
            />
            <button
              type="submit"
              className="cb-send-btn"
              disabled={!question.trim() || isThinking}
              title="Send"
            >
              <IconSend />
            </button>
          </div>
          <p className="cb-hint">Enter to send · Shift+Enter for new line</p>
        </form>
      </div>

    </div>
  );
}
