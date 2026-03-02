import React, { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { apiRequest } from '../../api/client';
import './AdminMessagingPage.css';

function AdminMessagingPage() {
  const { user } = useAuth();
  const currentUserId = user?.user_id || user?.id;
  const [conversations, setConversations] = useState([]);
  const [selectedClient, setSelectedClient] = useState(null);
  const [messages, setMessages] = useState([]);
  const [reply, setReply] = useState('');
  const [replyPdf, setReplyPdf] = useState(null);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [trackingLoading, setTrackingLoading] = useState(false);
  const [trackingError, setTrackingError] = useState('');
  const [tracking, setTracking] = useState(null);

  const loadConversations = () =>
    apiRequest('/api/v1/messages/admin/conversations/', { auth: true })
      .then(res => {
        if (res.ok && Array.isArray(res.data?.conversations)) {
          setConversations(res.data.conversations);
          return;
        }
        setError('Could not load conversations.');
      })
      .catch(() => setError('Could not load conversations.'));

  const loadMessages = (clientId) =>
    apiRequest(`/api/v1/messages/admin/conversations/${clientId}/`, { auth: true })
      .then(res => {
        if (res.ok && Array.isArray(res.data?.messages)) {
          setMessages(res.data.messages);
          return;
        }
        setError('Could not load messages.');
      })
      .catch(() => setError('Could not load messages.'));

  const loadTracking = (clientId) =>
    apiRequest(`/api/v1/messages/admin/clients/${clientId}/tracking-snapshot/`, { auth: true })
      .then(res => {
        if (res.ok && res.data?.tracking) {
          setTracking(res.data.tracking);
          setTrackingError('');
          return;
        }
        setTracking(null);
        setTrackingError('Could not load client tracking.');
      })
      .catch(() => {
        setTracking(null);
        setTrackingError('Could not load client tracking.');
      });

  // Fetch all client conversations (sorted by oldest unanswered message)
  useEffect(() => {
    setLoading(true);
    loadConversations()
      .finally(() => setLoading(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch messages for selected client
  useEffect(() => {
    if (!selectedClient) return;
    setLoading(true);
    setTrackingLoading(true);
    loadMessages(selectedClient.id)
      .finally(() => setLoading(false));
    loadTracking(selectedClient.id)
      .finally(() => setTrackingLoading(false));
  }, [selectedClient]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelectClient = (client) => {
    if (selectedClient?.id === client.id) {
      setLoading(true);
      setTrackingLoading(true);
      loadMessages(client.id).finally(() => setLoading(false));
      loadTracking(client.id).finally(() => setTrackingLoading(false));
      return;
    }
    setSelectedClient(client);
    setReply('');
    setReplyPdf(null);
    setError('');
    setTracking(null);
    setTrackingError('');
  };

  const recentWeights = (tracking?.weights || []).slice(0, 5);
  const recentPhotos = (tracking?.photos || []).slice(0, 6);

  const handleSend = async () => {
    if ((!reply.trim() && !replyPdf) || !selectedClient) return;
    setSending(true);
    setError('');
    const res = await apiRequest('/api/v1/messages/', {
      method: 'POST',
      auth: true,
      body: {
        recipient_id: selectedClient.id,
        content: reply.trim(),
      },
    });
    if (res.ok) {
      if (replyPdf && res.data?.id) {
        const formData = new FormData();
        formData.append('file', replyPdf);
        formData.append('message_id', res.data.id);
        const attachRes = await apiRequest('/api/v1/message-attachments/', {
          method: 'POST',
          auth: true,
          body: formData,
        });
        if (!attachRes.ok) {
          setError('Message sent, but PDF upload failed.');
        }
      }

      setReply('');
      setReplyPdf(null);
      await Promise.all([loadMessages(selectedClient.id), loadConversations()]);
    } else {
      setError('Failed to send message.');
    }
    setSending(false);
  };

  return (
    <div className="admin-messaging-page">
      <h1 className="admin-messaging-title">Client Messaging Portal</h1>
      <div className="messaging-layout">
        <aside className="messaging-sidebar">
          <h2 className="messaging-sidebar-title">Clients</h2>
          {loading && <p>Loading…</p>}
          {error && <p className="error">{error}</p>}
          <ul className="client-list">
            {conversations.map((conv) => (
              <li
                key={conv.client.id}
                className={selectedClient?.id === conv.client.id ? 'selected' : ''}
                onClick={() => handleSelectClient(conv.client)}
              >
                <span>{conv.client.name || conv.client.email}</span>
                {conv.unanswered_count > 0 && (
                  <span className="badge">{conv.unanswered_count}</span>
                )}
              </li>
            ))}
          </ul>
        </aside>
        <main className="messaging-main">
          {selectedClient ? (
            <>
              <section className="conversation-thread">
                <div className="conversation">
                  <h2 className="conversation-title">Conversation with {selectedClient.name || selectedClient.email}</h2>
                  <div className="messages-list">
                    {messages.length === 0 && <p>No messages yet.</p>}
                    {messages.map((msg) => (
                      <div key={msg.id} className={`message ${msg.sender === currentUserId ? 'sent' : 'received'}`}>
                        <div className="message-meta">
                          <span>{msg.sender === currentUserId ? 'You' : selectedClient.name || selectedClient.email}</span>
                          <span className="message-date">{new Date(msg.sent_at).toLocaleString()}</span>
                        </div>
                        <div className="message-content">{msg.content}</div>
                        {Array.isArray(msg.attachments) && msg.attachments.length > 0 && (
                          <div className="message-attachments">
                            {msg.attachments.map((att) => (
                              <a key={att.id} href={att.file} target="_blank" rel="noopener noreferrer">
                                {att.original_filename || 'View PDF'}
                              </a>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                  <div className="message-reply">
                    <textarea
                      value={reply}
                      onChange={e => setReply(e.target.value)}
                      placeholder="Type your reply…"
                      rows={3}
                      disabled={sending}
                    />
                    <div className="reply-controls-row">
                      <input
                        type="file"
                        accept="application/pdf"
                        onChange={(e) => setReplyPdf(e.target.files?.[0] || null)}
                        disabled={sending}
                      />
                    </div>
                    {replyPdf && <p className="reply-file-name">PDF selected: {replyPdf.name}</p>}
                    <div className="reply-send-row">
                      <button onClick={handleSend} disabled={sending || (!reply.trim() && !replyPdf)}>
                        {sending ? 'Sending…' : 'Send'}
                      </button>
                    </div>
                  </div>
                </div>
              </section>

              <section className="tracking-panel tracking-panel-below">
                <h3>Client Tracking Snapshot</h3>
                {trackingLoading && <p className="tracking-muted">Loading tracking…</p>}
                {trackingError && <p className="error">{trackingError}</p>}

                {!trackingLoading && !trackingError && tracking && (
                  <>
                    <p className="tracking-muted">
                      Photos: <strong>{tracking.summary?.photo_count ?? 0}</strong> • Weights: <strong>{tracking.summary?.weight_count ?? 0}</strong>
                    </p>

                    <div className="tracking-section">
                      <h4>Recent Weights</h4>
                      {recentWeights.length === 0 ? (
                        <p className="tracking-muted">No weight entries yet.</p>
                      ) : (
                        <ul className="tracking-list">
                          {recentWeights.map((row) => (
                            <li key={row.id}>
                              <span>{row.weight_value} {row.unit}</span>
                              <small>{new Date(row.measured_at).toLocaleString()}</small>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>

                    <div className="tracking-section">
                      <h4>Recent Progress Photos</h4>
                      {recentPhotos.length === 0 ? (
                        <p className="tracking-muted">No photos yet.</p>
                      ) : (
                        <ul className="tracking-list">
                          {recentPhotos.map((photo) => (
                            <li key={photo.id}>
                              <a href={photo.file_url} target="_blank" rel="noopener noreferrer" className="tracking-photo-link">
                                <img src={photo.file_url} alt="Client progress" className="tracking-photo-thumb" />
                                <span>View photo</span>
                              </a>
                              <small>{new Date(photo.created_at || photo.captured_for_date).toLocaleDateString()}</small>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </>
                )}
              </section>
            </>
          ) : (
            <p>Select a client to view and reply to messages.</p>
          )}
        </main>
      </div>
    </div>
  );
}

export default AdminMessagingPage;
