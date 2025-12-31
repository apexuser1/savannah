import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { CssBaseline, ThemeProvider } from '@mui/material'
import { BrowserRouter } from 'react-router-dom'
import '@fontsource/space-grotesk/400.css'
import '@fontsource/space-grotesk/600.css'
import './index.css'
import App from './App.tsx'
import theme from './theme'
import { ScenarioProvider } from './context/ScenarioContext'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <ScenarioProvider>
          <App />
        </ScenarioProvider>
      </BrowserRouter>
    </ThemeProvider>
  </StrictMode>,
)
