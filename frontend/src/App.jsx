import { useEffect, useRef, useState } from 'react'

const SIDEBAR_W = 260

const styles = {
  root: {
    display: 'flex',
    height: '100vh',
    fontFamily: "'Segoe UI', system-ui, sans-serif",
    background: '#1e1e2e',
    color: '#cdd6f4',
  },
  sidebar: {
    width: SIDEBAR_W,
    minWidth: SIDEBAR_W,
    background: '#181825',
    display: 'flex',
    flexDirection: 'column',
    padding: '16px 12px',
    gap: '8px',
    borderRight: '1px solid #313244',
  },
  sidebarTitle: {
    margin: '0 0 8px 4px',
    fontSize: '13px',
    fontWeight: 600,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    color: '#6c7086',
  },
  newChatBtn: {
    padding: '10px 12px',
    background: '#89b4fa',
    color: '#1e1e2e',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontWeight: 700,
    fontSize: '14px',
    textAlign: 'left',
  },
  threadList: {
    flex: 1,
    overflowY: 'auto',
    marginTop: '4px',
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  panel: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    minWidth: 0,
  },
  placeholder: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#6c7086',
    fontSize: '15px',
  },
  messages: {
    flex: 1,
    overflowY: 'auto',
    padding: '24px 32px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  inputRow: {
    padding: '12px 24px 16px',
    borderTop: '1px solid #313244',
    display: 'flex',
    gap: '8px',
    alignItems: 'flex-end',
  },
  textarea: {
    flex: 1,
    padding: '10px 14px',
    borderRadius: '8px',
    border: '1px solid #45475a',
    background: '#313244',
    color: '#cdd6f4',
    fontSize: '14px',
    resize: 'none',
    fontFamily: 'inherit',
    lineHeight: '1.5',
    outline: 'none',
  },
  sendBtn: {
    padding: '10px 20px',
    borderRadius: '8px',
    border: 'none',
    background: '#89b4fa',
    color: '#1e1e2e',
    fontWeight: 700,
    fontSize: '14px',
    cursor: 'pointer',
    flexShrink: 0,
  },
}

function ThreadItem({ thread, active, onClick }) {
  return (
    <div
      onClick={onClick}
      style={{
        padding: '9px 12px',
        borderRadius: '8px',
        cursor: 'pointer',
        background: active ? '#313244' : 'transparent',
        color: active ? '#cdd6f4' : '#a6adc8',
        fontSize: '13px',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}
    >
      {thread.title}
    </div>
  )
}

function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  return (
    <div style={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start' }}>
      <div
        style={{
          maxWidth: '70%',
          padding: '10px 16px',
          borderRadius: isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
          background: isUser ? '#89b4fa' : '#313244',
          color: isUser ? '#1e1e2e' : '#cdd6f4',
          fontSize: '14px',
          lineHeight: '1.6',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}
      >
        {message.content}
      </div>
    </div>
  )
}

export default function App() {
  const [threads, setThreads] = useState([])
  const [activeThread, setActiveThread] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    fetch('/threads')
      .then((r) => r.json())
      .then(setThreads)
      .catch(console.error)
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  async function createThread() {
    const res = await fetch('/threads', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: 'New Chat' }),
    })
    const thread = await res.json()
    setThreads((prev) => [thread, ...prev])
    setActiveThread(thread)
    setMessages([])
  }

  async function loadThread(thread) {
    setActiveThread(thread)
    const res = await fetch(`/threads/${thread.id}/messages`)
    const data = await res.json()
    setMessages(data)
  }

  async function sendMessage() {
    if (!input.trim() || !activeThread || sending) return
    const content = input.trim()
    setInput('')
    setSending(true)

    const tempId = `temp-${Date.now()}`
    setMessages((prev) => [
      ...prev,
      { id: tempId, role: 'user', content, created_at: new Date().toISOString() },
    ])

    try {
      const res = await fetch(`/threads/${activeThread.id}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      })
      const { user_message, assistant_message } = await res.json()
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== tempId),
        user_message,
        assistant_message,
      ])
      setThreads((prev) =>
        prev.map((t) =>
          t.id === activeThread.id
            ? { ...t, title: user_message.content.slice(0, 50), updated_at: user_message.created_at }
            : t
        )
      )
      setActiveThread((t) => ({ ...t, title: user_message.content.slice(0, 50) }))
    } catch (err) {
      console.error(err)
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== tempId),
        { id: 'err', role: 'assistant', content: 'Something went wrong. Please try again.' },
      ])
    } finally {
      setSending(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div style={styles.root}>
      {/* Sidebar */}
      <aside style={styles.sidebar}>
        <p style={styles.sidebarTitle}>Chats</p>
        <button style={styles.newChatBtn} onClick={createThread}>
          + New Chat
        </button>
        <div style={styles.threadList}>
          {threads.map((t) => (
            <ThreadItem
              key={t.id}
              thread={t}
              active={activeThread?.id === t.id}
              onClick={() => loadThread(t)}
            />
          ))}
        </div>
      </aside>

      {/* Main panel */}
      <main style={styles.panel}>
        {!activeThread ? (
          <div style={styles.placeholder}>Select a chat or start a new one</div>
        ) : (
          <>
            <div style={styles.messages}>
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              {sending && (
                <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                  <div
                    style={{
                      padding: '10px 16px',
                      borderRadius: '16px 16px 16px 4px',
                      background: '#313244',
                      color: '#6c7086',
                      fontSize: '14px',
                    }}
                  >
                    ...
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
            <div style={styles.inputRow}>
              <textarea
                style={styles.textarea}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Message… (Enter to send, Shift+Enter for newline)"
                rows={2}
              />
              <button
                style={{
                  ...styles.sendBtn,
                  opacity: !input.trim() || sending ? 0.45 : 1,
                  cursor: !input.trim() || sending ? 'not-allowed' : 'pointer',
                }}
                onClick={sendMessage}
                disabled={!input.trim() || sending}
              >
                Send
              </button>
            </div>
          </>
        )}
      </main>
    </div>
  )
}
