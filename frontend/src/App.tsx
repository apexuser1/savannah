import { useMemo, useState } from 'react'
import {
  AppBar,
  Box,
  Chip,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  useMediaQuery,
  useTheme
} from '@mui/material'
import MenuIcon from '@mui/icons-material/Menu'
import DashboardIcon from '@mui/icons-material/Dashboard'
import PsychologyAltIcon from '@mui/icons-material/PsychologyAlt'
import TuneIcon from '@mui/icons-material/Tune'
import {
  Route,
  Routes,
  useLocation,
  useNavigate,
  type Location
} from 'react-router-dom'
import DashboardPage from './pages/DashboardPage'
import WhatIfPage from './pages/WhatIfPage'
import OptimisationsPage from './pages/OptimisationsPage'
import DetailDrawer from './components/DetailDrawer'

const drawerWidth = 260

const navItems = [
  { label: 'Dashboard', path: '/', icon: <DashboardIcon /> },
  { label: 'What-If', path: '/what-if', icon: <PsychologyAltIcon /> },
  { label: 'Optimisations', path: '/optimisations', icon: <TuneIcon /> }
]

function App() {
  const theme = useTheme()
  const isDesktop = useMediaQuery(theme.breakpoints.up('md'))
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const state = location.state as { backgroundLocation?: Location } | null
  const routeLocation = state?.backgroundLocation || location

  const activeIndex = useMemo(() => {
    if (routeLocation.pathname.startsWith('/what-if')) {
      return 1
    }
    if (routeLocation.pathname.startsWith('/optimisations')) {
      return 2
    }
    return 0
  }, [routeLocation.pathname])

  const title = useMemo(() => {
    if (routeLocation.pathname.startsWith('/what-if')) {
      return 'What-If Scenarios'
    }
    if (routeLocation.pathname.startsWith('/optimisations')) {
      return 'Optimisations'
    }
    return 'Dashboard'
  }, [routeLocation.pathname])

  const subtitle = useMemo(() => {
    if (routeLocation.pathname.startsWith('/what-if')) {
      return 'Define scenarios, run evaluations, and apply score deltas'
    }
    if (routeLocation.pathname.startsWith('/optimisations')) {
      return 'Explore relaxations and candidate targets'
    }
    return 'Jobs, applications, and scenario filters'
  }, [routeLocation.pathname])

  const handleDrawerToggle = () => {
    setMobileOpen((open) => !open)
  }

  const drawerContent = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Toolbar sx={{ px: 3 }}>
        <Box>
          <Typography variant="h6">Talent Lens</Typography>
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            Resume Job Matcher
          </Typography>
        </Box>
      </Toolbar>
      <Divider />
      <List sx={{ px: 1.5, pt: 1 }}>
        {navItems.map((item, index) => (
          <ListItemButton
            key={item.label}
            selected={index === activeIndex}
            onClick={() => {
              navigate(item.path)
              setMobileOpen(false)
            }}
            sx={{
              borderRadius: 2,
              mb: 0.5
            }}
          >
            <ListItemIcon sx={{ minWidth: 40 }}>{item.icon}</ListItemIcon>
            <ListItemText primary={item.label} />
          </ListItemButton>
        ))}
      </List>
      <Box sx={{ mt: 'auto', px: 3, pb: 2 }}>
        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
          API: http://localhost:8000
        </Typography>
      </Box>
    </Box>
  )

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppBar
        position="fixed"
        color="transparent"
        elevation={0}
        sx={{
          backdropFilter: 'blur(14px)',
          borderBottom: '1px solid',
          borderColor: 'divider',
          zIndex: (value) => value.zIndex.drawer + 1
        }}
      >
        <Toolbar sx={{ px: { xs: 2, md: 4 } }}>
          {!isDesktop && (
            <IconButton edge="start" onClick={handleDrawerToggle}>
              <MenuIcon />
            </IconButton>
          )}
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h6">{title}</Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
              {subtitle}
            </Typography>
          </Box>
          <Chip label="Prototype" color="secondary" size="small" />
        </Toolbar>
      </AppBar>

      <Box component="nav">
        <Drawer
          variant={isDesktop ? 'permanent' : 'temporary'}
          open={isDesktop || mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            width: drawerWidth,
            flexShrink: 0,
            '& .MuiDrawer-paper': {
              width: drawerWidth,
              borderRight: '1px solid',
              borderColor: 'divider'
            }
          }}
        >
          {drawerContent}
        </Drawer>
      </Box>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          px: { xs: 2, md: 4 },
          py: { xs: 3, md: 4 }
        }}
      >
        <Toolbar />
        <Routes location={routeLocation}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/jobs/:jobId" element={<DashboardPage />} />
          <Route path="/applications/:applicationId" element={<DashboardPage />} />
          <Route path="/applications/:applicationId/appraisal" element={<DashboardPage />} />
          <Route path="/candidates/:candidateId/resume" element={<DashboardPage />} />
          <Route path="/candidates/:candidateId" element={<DashboardPage />} />
          <Route path="/what-if" element={<WhatIfPage />} />
          <Route path="/optimisations" element={<OptimisationsPage />} />
        </Routes>
      </Box>

      <DetailDrawer />
    </Box>
  )
}

export default App
