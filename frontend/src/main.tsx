import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './styles/prototype.css'
import './index.css'
import App from './App.tsx'
import AgentStudioPage from './screens/Agent/StandalonePage.tsx'

const isAgentStudio = window.location.hash === '#agent-studio'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {isAgentStudio ? (
      <AgentStudioPage />
    ) : (
      <BrowserRouter>
        <App />
      </BrowserRouter>
    )}
  </StrictMode>,
)
