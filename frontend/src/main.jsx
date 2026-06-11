import React from 'react'
import ReactDOM from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import App from './App'
import { ThemeProvider } from './contexts/ThemeContext'
import { VoiceProvider } from './contexts/VoiceContext'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ThemeProvider>
      <VoiceProvider>
        <HashRouter>
          <App />
        </HashRouter>
      </VoiceProvider>
    </ThemeProvider>
  </React.StrictMode>
)
