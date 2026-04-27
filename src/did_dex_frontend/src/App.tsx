import { useEffect, useMemo, useState } from 'react';
import { Link, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { BrowserRouter } from 'react-router-dom';
import { AppBar, Box, Button, Container, Stack, Toolbar, Typography } from '@mui/material';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import WalletConnectModal from './components/WalletConnectModal';
import MarketsPage from './pages/MarketsPage';
import RegisterPage from './pages/RegisterPage';
import DexPage from './pages/DexPage';
import TokenMintPage from './pages/TokenMintPage';
import { clearRememberedWallet, reconnectApprovedWallet } from './wallet';
import { assertBackendPreprodWallet } from './walletValidation';
import type { WalletState } from './types';

function shortAddress(address: string) {
  return `${address.slice(0, 8)}...${address.slice(-6)}`;
}

function Shell({ wallet, setWallet }: { wallet?: WalletState; setWallet: (wallet?: WalletState) => void }) {
  const location = useLocation();
  const [walletModalOpen, setWalletModalOpen] = useState(false);
  const active = useMemo(() => {
    if (location.pathname.startsWith('/markets') || location.pathname === '/dex') return 'markets';
    if (location.pathname.startsWith('/tokens')) return 'tokens';
    if (location.pathname.startsWith('/did') || location.pathname.startsWith('/register')) return 'did';
    return 'markets';
  }, [location.pathname]);

  const isTrading = location.pathname.startsWith('/markets/');

  return (
    <Box className="app-shell">
      <AppBar position="sticky" elevation={0} className="topbar">
        <Toolbar className="topbar-toolbar">
          <Stack direction="row" alignItems="center" spacing={1} className="brand-stack">
            <Box className="brand-mark">
              <ShowChartIcon sx={{ fontSize: 18 }} />
            </Box>
            <Box>
              <Typography variant="h6" fontWeight={600} sx={{ fontSize: '0.9375rem', lineHeight: 1.2 }}>DID DEX</Typography>
              <Typography variant="caption">Cardano Orderbook</Typography>
            </Box>
          </Stack>
          <Stack direction="row" alignItems="center" spacing={0.5} className="nav-stack">
            <Button component={Link} to="/markets" variant={active === 'markets' ? 'contained' : 'text'} size="small">
              Markets
            </Button>
            <Button component={Link} to="/did" variant={active === 'did' ? 'contained' : 'text'} size="small">
              DID
            </Button>
            <Button component={Link} to="/tokens" variant={active === 'tokens' ? 'contained' : 'text'} size="small">
              Tokens
            </Button>
          </Stack>
          <Stack direction="row" alignItems="center" spacing={1} className="wallet-status">
            <Button
              startIcon={<AccountBalanceWalletIcon />}
              variant="outlined"
              className="wallet-connect-button"
              onClick={() => setWalletModalOpen(true)}
            >
              {wallet ? (
                <Stack spacing={0} alignItems="flex-start">
                  <Typography variant="caption">{wallet.name}</Typography>
                  <Typography variant="body2" className="mono" sx={{ fontSize: '0.75rem' }}>{shortAddress(wallet.address)}</Typography>
                </Stack>
              ) : (
                'Connect Wallet'
              )}
            </Button>
          </Stack>
        </Toolbar>
      </AppBar>
      {isTrading ? (
        <Routes>
          <Route path="/markets/:pairId" element={<DexPage wallet={wallet} setWallet={setWallet} />} />
        </Routes>
      ) : (
        <Container maxWidth="lg" sx={{ py: 2 }}>
          <Routes>
            <Route path="/markets" element={<MarketsPage />} />
            <Route path="/did" element={<RegisterPage wallet={wallet} setWallet={setWallet} />} />
            <Route path="/tokens" element={<TokenMintPage wallet={wallet} setWallet={setWallet} />} />
            <Route path="/register" element={<Navigate to="/did" replace />} />
            <Route path="/dex" element={<Navigate to="/markets/muesli-swap" replace />} />
            <Route path="*" element={<Navigate to="/markets" replace />} />
          </Routes>
        </Container>
      )}
      <WalletConnectModal
        open={walletModalOpen}
        wallet={wallet}
        onClose={() => setWalletModalOpen(false)}
        setWallet={setWallet}
      />
    </Box>
  );
}

function DesktopOnlyNotice() {
  return (
    <Box className="desktop-only-notice">
      <Box className="desktop-only-card">
        <Box className="brand-mark">
          <ShowChartIcon sx={{ fontSize: 18 }} />
        </Box>
        <Typography variant="h5" fontWeight={700}>
          Desktop required
        </Typography>
        <Typography>
          This website currently only supports desktop devices. Please open DID DEX on a laptop or desktop browser.
        </Typography>
      </Box>
    </Box>
  );
}

export default function App() {
  const [wallet, setWallet] = useState<WalletState>();
  useEffect(() => {
    let cancelled = false;
    reconnectApprovedWallet()
      .then(async (approvedWallet) => {
        if (!approvedWallet) return;
        await assertBackendPreprodWallet(approvedWallet);
        if (!cancelled) setWallet(approvedWallet);
      })
      .catch(() => {
        clearRememberedWallet();
        if (!cancelled) setWallet(undefined);
      })
    return () => {
      cancelled = true;
    };
  }, []);
  return (
    <BrowserRouter>
      <DesktopOnlyNotice />
      <Shell wallet={wallet} setWallet={setWallet} />
    </BrowserRouter>
  );
}
