import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  render() {
    if (this.state.error != null) {
      const msg =
        this.state.error instanceof Error
          ? this.state.error.message
          : String(this.state.error)
      return (
        <div
          style={{
            minHeight: '100dvh',
            padding: 24,
            fontFamily: 'system-ui, sans-serif',
            background: '#fef2f2',
            color: '#7f1d1d',
            boxSizing: 'border-box',
          }}
        >
          <h1 style={{ fontSize: 18, marginBottom: 12 }}>Something broke</h1>
          <pre
            style={{
              whiteSpace: 'pre-wrap',
              fontSize: 13,
              background: '#fff',
              padding: 16,
              borderRadius: 8,
              border: '1px solid #fecaca',
            }}
          >
            {msg}
          </pre>
          <p style={{ marginTop: 16, fontSize: 14, color: '#991b1b' }}>
            Open the browser devtools console (F12) for the full stack trace.
          </p>
        </div>
      )
    }
    return this.props.children
  }
}
