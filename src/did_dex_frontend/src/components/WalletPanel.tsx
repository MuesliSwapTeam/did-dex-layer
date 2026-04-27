import { useMemo, useState } from 'react';
import { Alert, Button, MenuItem, Stack, TextField, Typography } from '@mui/material';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import { availableWallets, connectWallet } from '../wallet';
import { assertBackendPreprodWallet } from '../walletValidation';
import type { WalletState } from '../types';

export default function WalletPanel({
  wallet,
  setWallet
}: {
  wallet?: WalletState;
  setWallet: (wallet?: WalletState) => void;
}) {
  const wallets = useMemo(() => availableWallets(), []);
  const [selected, setSelected] = useState(wallets[0] ?? '');
  const [error, setError] = useState<string>();

  const onConnect = async () => {
    setError(undefined);
    try {
      const nextWallet = await connectWallet(selected);
      await assertBackendPreprodWallet(nextWallet);
      setWallet(nextWallet);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <Stack spacing={1.5} className="wallet-panel">
      <Typography variant="h6">Wallet</Typography>
      {wallet ? (
        <Alert severity="success">
          Connected to {wallet.name}: <span className="mono">{wallet.address}</span>
        </Alert>
      ) : (
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.25}>
          <TextField
            select
            size="small"
            label="Wallet"
            value={selected}
            onChange={(event) => setSelected(event.target.value)}
            disabled={!wallets.length}
            sx={{ minWidth: 180, flex: 1 }}
          >
            {wallets.map((name) => (
              <MenuItem key={name} value={name}>{name}</MenuItem>
            ))}
          </TextField>
          <Button
            startIcon={<AccountBalanceWalletIcon />}
            variant="contained"
            disabled={!selected}
            onClick={onConnect}
          >
            Connect
          </Button>
        </Stack>
      )}
      {!wallets.length && <Alert severity="warning">No CIP-30 browser wallet was detected.</Alert>}
      {!wallet && wallets.length > 0 && (
        <Alert severity="info">Only Cardano Preprod wallets can connect.</Alert>
      )}
      {error && <Alert severity="error">{error}</Alert>}
    </Stack>
  );
}
