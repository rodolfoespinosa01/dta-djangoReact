import React, { useEffect, useRef, useState } from 'react';
import { apiRequest } from '../api/client';
import { useAuth } from '../context/AuthContext';
import './MessagingPortal.css';

function MessagingPortal({ adminUserId }) {
  const { user } = useAuth();
  const currentEmail = (user?.email || '').toLowerCase();
  const threadRef = useRef(null);
  const [messages, setMessages] = useState([]);
  const [content, setContent] = useState('');
  const [pdfFile, setPdfFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchMessages();
  }, []);

  useEffect(() => {
    if (!threadRef.current) return;
    threadRef.current.scrollTo({
      top: threadRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, [messages]);

  async function fetchMessages() {
    setLoading(true);
    setError('');
    try {
      const res = await apiRequest('/api/v1/messages/', { auth: true });
      if (res.ok) setMessages(res.data);
      else setError('Failed to load messages');
    } catch (e) {
      setError('Error loading messages');
    }
    setLoading(false);
  }

  async function handleSend(e) {
    e.preventDefault();
    if (!content.trim() && !pdfFile) return;
    setError('');
    try {
      const sendRes = await apiRequest('/api/v1/messages/', {
        method: 'POST',
        body: { recipient_id: adminUserId, content: content.trim() },
        auth: true,
      });

      if (!sendRes.ok) {
        setError('Failed to send message');
        return;
      }

      if (pdfFile && sendRes.data?.id) {
        const formData = new FormData();
        formData.append('file', pdfFile);
        formData.append('message_id', sendRes.data.id);

        const attachRes = await apiRequest('/api/v1/message-attachments/', {
          method: 'POST',
          body: formData,
          auth: true,
        });
        if (!attachRes.ok) {
          setError('Message sent, but PDF upload failed.');
        }
      }

      setContent('');
      setPdfFile(null);
      fetchMessages();
    } catch (e) {
      setError('Error sending message');
    }
  }

  return (
    <div className="client-messaging-portal">
      <div className="client-messaging-header">
        <h2>Messages with your coach</h2>
        <button type="button" className="client-msg-refresh" onClick={fetchMessages} disabled={loading}>
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      {error && <p className="client-msg-error">{error}</p>}

      <div className="client-thread" role="log" aria-live="polite" ref={threadRef}>
        {loading && messages.length === 0 ? <p className="client-msg-muted">Loading messages…</p> : null}
        {!loading && messages.length === 0 ? <p className="client-msg-muted">No messages yet. Start the conversation with your coach.</p> : null}

        {messages.map((msg) => {
          const isMine = currentEmail && String(msg.sender || '').toLowerCase() === currentEmail;
          return (
            <article key={msg.id} className={`client-msg-bubble ${isMine ? 'sent' : 'received'}`}>
              <div className="client-msg-meta">
                <span>{isMine ? 'You' : 'Coach'}</span>
                <span>{new Date(msg.sent_at).toLocaleString()}</span>
              </div>

              {msg.content ? <p className="client-msg-content">{msg.content}</p> : null}

              {Array.isArray(msg.attachments) && msg.attachments.length > 0 ? (
                <div className="client-msg-docs">
                  <p>Documents included</p>
                  <ul>
                    {msg.attachments.map((att) => (
                      <li key={att.id}>
                        <a href={att.file} target="_blank" rel="noopener noreferrer">
                          {att.original_filename || 'Open PDF'}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </article>
          );
        })}
      </div>

      <form onSubmit={handleSend} className="client-msg-compose">
        <h3>Send a message</h3>
        <textarea
          placeholder="Write your message to your coach…"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={4}
        />
        <div className="client-msg-compose-row">
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => setPdfFile(e.target.files?.[0] || null)}
          />
        </div>
        {pdfFile ? <p className="client-msg-file">PDF selected: {pdfFile.name}</p> : null}
        <div className="client-msg-send-row">
          <button type="submit" disabled={loading || (!content.trim() && !pdfFile)}>
            Send Message
          </button>
        </div>
      </form>
    </div>
  );
}

export default MessagingPortal;
