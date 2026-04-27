import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CssBaseline, ThemeProvider, createTheme } from '@mui/material';
import App from './App';
import './styles.css';

const queryClient = new QueryClient();
const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#6366f1', dark: '#4f46e5', light: '#818cf8' },
    secondary: { main: '#ef4444', dark: '#dc2626', light: '#f87171' },
    success: { main: '#22c55e', dark: '#16a34a', light: '#4ade80' },
    warning: { main: '#eab308' },
    info: { main: '#3b82f6' },
    background: { default: '#09090b', paper: '#18181b' },
    text: { primary: '#fafafa', secondary: '#71717a' }
  },
  shape: { borderRadius: 6 },
  typography: {
    fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif',
    h3: { fontWeight: 600, letterSpacing: '-0.025em' },
    h5: { fontWeight: 600, letterSpacing: '-0.015em' },
    h6: { fontWeight: 600, letterSpacing: '-0.01em' },
    body2: { fontSize: '0.8125rem' },
    button: { textTransform: 'none', fontWeight: 500, letterSpacing: 0 },
    overline: { fontWeight: 500, letterSpacing: '0.05em', color: '#71717a', fontSize: '0.6875rem' }
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          border: '1px solid #27272a',
          boxShadow: 'none',
          background: '#18181b'
        }
      }
    },
    MuiButton: {
      styleOverrides: {
        root: { borderRadius: 6, minHeight: 36 },
        containedPrimary: { color: '#fff', '&:hover': { background: '#4f46e5' } }
      }
    },
    MuiTextField: {
      defaultProps: { size: 'small' },
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            background: '#27272a',
            '& fieldset': { borderColor: '#3f3f46' },
            '&:hover fieldset': { borderColor: '#52525b' },
            '&.Mui-focused fieldset': { borderColor: '#6366f1' }
          },
          '& .MuiInputLabel-root': { color: '#71717a' },
          '& .MuiInputBase-input': { color: '#fafafa' }
        }
      }
    },
    MuiTableCell: {
      styleOverrides: {
        root: { borderColor: '#27272a', color: '#fafafa', padding: '8px 12px' },
        head: { background: '#18181b', color: '#71717a', fontWeight: 500, fontSize: '0.75rem' }
      }
    }
  }
});

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <App />
      </ThemeProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
