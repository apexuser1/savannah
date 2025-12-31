import { createTheme } from '@mui/material/styles'

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1f6f5b'
    },
    secondary: {
      main: '#d66b2d'
    },
    background: {
      default: '#f6f3ee',
      paper: '#ffffff'
    }
  },
  typography: {
    fontFamily: '"Space Grotesk", "Segoe UI", sans-serif',
    h4: {
      fontWeight: 600,
      letterSpacing: -0.4
    },
    h6: {
      fontWeight: 600,
      letterSpacing: -0.2
    }
  },
  shape: {
    borderRadius: 12
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundImage:
            'radial-gradient(circle at 12% 15%, rgba(31, 111, 91, 0.12), transparent 45%), radial-gradient(circle at 85% 10%, rgba(214, 107, 45, 0.12), transparent 40%)'
        }
      }
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none'
        }
      }
    }
  }
})

export default theme
