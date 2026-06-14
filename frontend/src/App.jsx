import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

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

function ThinkingSection({ steps, streaming }) {
  const [open, setOpen] = useState(true)
  if (!steps || steps.length === 0) return null

  return (
    <div style={{ marginBottom: '8px' }}>
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          background: 'none',
          border: 'none',
          color: '#6c7086',
          fontSize: '12px',
          cursor: 'pointer',
          padding: '2px 0',
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
        }}
      >
        <span>{open ? '▾' : '▸'}</span>
        <span>
          {streaming ? 'Thinking…' : `Reasoning (${steps.length} step${steps.length > 1 ? 's' : ''})`}
        </span>
      </button>

      {open && (
        <div
          style={{
            marginTop: '6px',
            padding: '8px 12px',
            background: '#181825',
            borderLeft: '2px solid #45475a',
            borderRadius: '4px',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
          }}
        >
          {steps.map((step, i) => {
            if (step.step === 'planner') {
              return (
                <div key={i} style={{ fontSize: '12px', color: '#a6adc8' }}>
                  <span style={{ color: '#89dceb' }}>Planner</span>
                  {' → '}complexity: <strong>{step.complexity}</strong>
                  {', max retries: '}<strong>{step.max_retries}</strong>
                </div>
              )
            }
            if (step.step === 'tool_call') {
              return (
                <div key={i} style={{ fontSize: '12px', color: '#a6adc8' }}>
                  <span style={{ color: '#a6e3a1' }}>▶ {step.tool}</span>
                  {' '}
                  <span style={{ color: '#6c7086' }}>{JSON.stringify(step.input)}</span>
                </div>
              )
            }
            if (step.step === 'tool_result') {
              return (
                <div key={i} style={{ fontSize: '12px', color: '#6c7086', paddingLeft: '12px' }}>
                  ← {step.output}
                </div>
              )
            }
            return null
          })}
        </div>
      )}
    </div>
  )
}

function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  const isEmpty = message.streaming && message.content === ''
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
          wordBreak: 'break-word',
          minWidth: isEmpty ? '40px' : undefined,
          minHeight: isEmpty ? '20px' : undefined,
        }}
      >
        {isUser ? (
          <span style={{ whiteSpace: 'pre-wrap' }}>{message.content}</span>
        ) : (
          <>
            <ThinkingSection steps={message.steps} streaming={message.streaming} />
            <div className="markdown">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
              {message.streaming && <span className="cursor">▌</span>}
            </div>
          </>
        )}
        {isUser && message.streaming && <span className="cursor">▌</span>}
      </div>
    </div>
  )
}

function parseSSEChunk(buffer) {
  const events = []
  const parts = buffer.split('\n\n')
  const remaining = parts.pop() // incomplete trailing chunk
  for (const part of parts) {
    if (!part.startsWith('data: ')) continue
    try {
      events.push(JSON.parse(part.slice(6)))
    } catch {
      // skip malformed event
    }
  }
  return { events, remaining }
}

export default function App() {
  const [threads, setThreads] = useState([])
  const [activeThread, setActiveThread] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    fetch('/threads')
      .then((r) => r.json())
      .then(setThreads)
      .catch(console.error)
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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
    setMessages(await res.json())
  }

  async function sendMessage() {
    if (!input.trim() || !activeThread || streaming) return
    const content = input.trim()
    setInput('')
    setStreaming(true)

    const isFirstMessage = messages.length === 0
    const tempUserId = `temp-user-${Date.now()}`
    const streamingId = `streaming-${Date.now()}`

    // Optimistic: user bubble + empty streaming assistant bubble
    setMessages((prev) => [
      ...prev,
      { id: tempUserId, role: 'user', content, created_at: new Date().toISOString() },
      { id: streamingId, role: 'assistant', content: '', streaming: true },
    ])

    try {
      const response = await fetch(`/threads/${activeThread.id}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      })

      if (!response.ok) {
        throw new Error(`Server error ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let assistantContent = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const { events, remaining } = parseSSEChunk(buffer)
        buffer = remaining

        for (const data of events) {
          if (data.user_message_id) {
            setMessages((prev) =>
              prev.map((m) => (m.id === tempUserId ? { ...m, id: data.user_message_id } : m))
            )
          } else if (data.step && data.step !== 'planner') {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === streamingId ? { ...m, steps: [...(m.steps || []), data] } : m
              )
            )
          } else if (data.token) {
            assistantContent += data.token
            const snap = assistantContent
            setMessages((prev) =>
              prev.map((m) => (m.id === streamingId ? { ...m, content: snap } : m))
            )
          } else if (data.done) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === streamingId ? { ...m, id: data.message_id, streaming: false } : m
              )
            )
            // Update sidebar title + ordering
            const newTitle = isFirstMessage ? content.slice(0, 50) : null
            setThreads((prev) => {
              const updated = prev.map((t) =>
                t.id === activeThread.id
                  ? { ...t, ...(newTitle ? { title: newTitle } : {}) }
                  : t
              )
              // Bubble to top
              const idx = updated.findIndex((t) => t.id === activeThread.id)
              if (idx > 0) {
                const [moved] = updated.splice(idx, 1)
                return [moved, ...updated]
              }
              return updated
            })
            if (newTitle) {
              setActiveThread((t) => ({ ...t, title: newTitle }))
            }
          } else if (data.error) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === streamingId
                  ? { ...m, content: `Error: ${data.error}`, streaming: false }
                  : m
              )
            )
          }
        }
      }
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === streamingId
            ? { ...m, content: 'Something went wrong. Please try again.', streaming: false }
            : m
        )
      )
    } finally {
      setStreaming(false)
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
                disabled={streaming}
              />
              <button
                style={{
                  ...styles.sendBtn,
                  opacity: !input.trim() || streaming ? 0.45 : 1,
                  cursor: !input.trim() || streaming ? 'not-allowed' : 'pointer',
                }}
                onClick={sendMessage}
                disabled={!input.trim() || streaming}
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
