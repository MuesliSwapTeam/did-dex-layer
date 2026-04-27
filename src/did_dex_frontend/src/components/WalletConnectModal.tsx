import { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Avatar,
  Box,
  Button,
  Dialog,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  Stack,
  Typography
} from '@mui/material';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import CloseIcon from '@mui/icons-material/Close';
import LinkOffIcon from '@mui/icons-material/LinkOff';
import RefreshIcon from '@mui/icons-material/Refresh';
import VerifiedIcon from '@mui/icons-material/Verified';
import {
  clearRememberedWallet,
  connectWallet,
  installedWallets,
  walletMetadata,
  rememberWallet
} from '../wallet';
import { assertBackendPreprodWallet } from '../walletValidation';
import type { WalletDescriptor } from '../wallet';
import type { WalletState } from '../types';

function shortAddress(address: string) {
  return `${address.slice(0, 18)}...${address.slice(-12)}`;
}

function WalletLogo({ wallet }: { wallet: WalletDescriptor }) {
  return (
    <Avatar src={wallet.icon} alt={wallet.label} className="wallet-logo">
      {wallet.label.slice(0, 1).toUpperCase()}
    </Avatar>
  );
}

export default function WalletConnectModal({
  open,
  wallet,
  onClose,
  setWallet
}: {
  open: boolean;
  wallet?: WalletState;
  onClose: () => void;
  setWallet: (wallet?: WalletState) => void;
}) {
  const [wallets, setWallets] = useState<WalletDescriptor[]>([]);
  const [busyWallet, setBusyWallet] = useState<string>();
  const [error, setError] = useState<string>();
  const [loadingWallets, setLoadingWallets] = useState(false);

  const refreshWallets = useCallback(async () => {
    setLoadingWallets(true);
    try {
      setWallets(await installedWallets());
    } finally {
      setLoadingWallets(false);
    }
  }, []);

  useEffect(() => {
    if (!open) return;

    let cancelled = false;
    let retry: ReturnType<typeof window.setTimeout> | undefined;

    const scanWallets = async (remainingAttempts: number) => {
      setLoadingWallets(true);
      let nextWallets: WalletDescriptor[];
      try {
        nextWallets = await installedWallets();
        if (cancelled) return;
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
          setLoadingWallets(false);
        }
        return;
      }

      setWallets(nextWallets);
      if (nextWallets.length || remainingAttempts <= 0) {
        setLoadingWallets(false);
        return;
      }

      retry = window.setTimeout(() => {
        void scanWallets(remainingAttempts - 1);
      }, 250);
    };

    const rescanWallets = () => {
      void refreshWallets();
    };

    const rescanWhenVisible = () => {
      if (document.visibilityState === 'visible') rescanWallets();
    };

    setError(undefined);
    void scanWallets(8);
    window.addEventListener('focus', rescanWallets);
    window.addEventListener('cardano#initialized', rescanWallets);
    window.addEventListener('cardano:initialized', rescanWallets);
    document.addEventListener('visibilitychange', rescanWhenVisible);

    return () => {
      cancelled = true;
      if (retry) window.clearTimeout(retry);
      window.removeEventListener('focus', rescanWallets);
      window.removeEventListener('cardano#initialized', rescanWallets);
      window.removeEventListener('cardano:initialized', rescanWallets);
      document.removeEventListener('visibilitychange', rescanWhenVisible);
    };
  }, [open, refreshWallets]);

  const onConnect = async (name: string) => {
    setBusyWallet(name);
    setError(undefined);
    try {
      const nextWallet = await connectWallet(name);
      await assertBackendPreprodWallet(nextWallet);
      rememberWallet(name);
      setWallet(nextWallet);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyWallet(undefined);
    }
  };

  const onDisconnect = () => {
    clearRememberedWallet();
    setWallet(undefined);
    onClose();
  };

  const connectedWalletDescriptor =
    wallet &&
    (wallets.find((item) => item.id === wallet.name) ?? {
      id: wallet.name,
      isEnabled: true,
      ...walletMetadata(wallet.name)
    });

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs" PaperProps={{ className: 'wallet-dialog' }}>
      <DialogTitle>
        <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={2}>
          <Stack direction="row" spacing={1.25} alignItems="center">
            <Box className="wallet-dialog-mark">
              <AccountBalanceWalletIcon fontSize="small" />
            </Box>
            <Box>
              <Typography variant="h6">Connect wallet</Typography>
              <Typography variant="caption">
                Select an installed Cardano wallet set to Preprod.
              </Typography>
            </Box>
          </Stack>
          <IconButton onClick={onClose} aria-label="Close wallet dialog">
            <CloseIcon />
          </IconButton>
        </Stack>
      </DialogTitle>
      <DialogContent>
        <Stack spacing={2} className="wallet-dialog-body">
          {wallet && (
            <Box className="connected-wallet-card wallet-section-card">
              <Stack direction="row" spacing={1.25} alignItems="center">
                {connectedWalletDescriptor ? (
                  <WalletLogo wallet={connectedWalletDescriptor} />
                ) : (
                  <Avatar className="connected-wallet-icon">
                    <VerifiedIcon />
                  </Avatar>
                )}
                <Box sx={{ minWidth: 0 }}>
                  <Stack direction="row" spacing={0.75} alignItems="center">
                    <Typography variant="caption">Connected wallet</Typography>
                    <VerifiedIcon color="success" fontSize="small" />
                  </Stack>
                  <Typography variant="body1" fontWeight={900}>{wallet.name}</Typography>
                  <Typography className="mono" variant="body2">{shortAddress(wallet.address)}</Typography>
                </Box>
              </Stack>
              <Button startIcon={<LinkOffIcon />} color="secondary" variant="outlined" onClick={onDisconnect}>
                Disconnect
              </Button>
            </Box>
          )}

          <Box className="wallet-section-card">
            <Stack direction="row" justifyContent="space-between" alignItems="center">
              <Typography variant="overline">Installed wallets</Typography>
              <Button startIcon={<RefreshIcon />} size="small" onClick={refreshWallets}>
                Refresh
              </Button>
            </Stack>

            <Stack spacing={1} sx={{ mt: 1.25 }}>
              {wallets.map((item) => (
                <Button
                  key={item.id}
                  className="wallet-option"
                  variant="outlined"
                  disabled={busyWallet !== undefined}
                  onClick={() => onConnect(item.id)}
                >
                  <WalletLogo wallet={item} />
                  <Box className="wallet-option-copy">
                    <Typography variant="body1" fontWeight={900}>{item.label}</Typography>
                    <Typography variant="caption">
                      {item.isEnabled ? 'Approved session available' : 'Approval required'}
                    </Typography>
                  </Box>
                  {item.isEnabled && <VerifiedIcon color="success" fontSize="small" />}
                </Button>
              ))}
              {!wallets.length && loadingWallets && (
                <Alert severity="info">
                  Scanning for installed Cardano wallets...
                </Alert>
              )}
              {!wallets.length && !loadingWallets && (
                <Alert severity="warning">
                No CIP-30 Cardano wallet was detected in this browser.
                </Alert>
              )}
            </Stack>
          </Box>

          {error && <Alert severity="error">{error}</Alert>}
          <Divider className="wallet-dialog-footer-divider" />
        </Stack>
      </DialogContent>
    </Dialog>
  );
}
