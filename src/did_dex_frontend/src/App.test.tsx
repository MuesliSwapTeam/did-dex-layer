import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ThemeProvider, createTheme } from '@mui/material';
import App from './App';

vi.mock('./wallet', () => ({
  PREPROD_WALLET_ERROR: 'This interface only supports Cardano Preprod wallets.',
  availableWallets: () => [],
  clearRememberedWallet: vi.fn(),
  connectWallet: vi.fn(),
  installedWallets: vi.fn().mockResolvedValue([]),
  reconnectApprovedWallet: vi.fn().mockResolvedValue(undefined),
  rememberWallet: vi.fn(),
  signAndSubmit: vi.fn()
}));

vi.stubGlobal(
  'ResizeObserver',
  class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
);

describe('DID DEX app', () => {
  it('renders the DEX navigation', () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <ThemeProvider theme={createTheme()}>
          <App />
        </ThemeProvider>
      </QueryClientProvider>
    );

    expect(screen.getByText('DID DEX')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Markets' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'DID' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Tokens' })).toBeInTheDocument();
  });
});
