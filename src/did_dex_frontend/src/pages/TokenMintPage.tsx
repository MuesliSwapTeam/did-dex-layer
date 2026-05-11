import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Grid,
  MenuItem,
  Stack,
  TextField,
  Typography
} from '@mui/material';
import AddCircleIcon from '@mui/icons-material/AddCircle';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import TokenIcon from '@mui/icons-material/Token';
import { api, sanitizeErrorMessage } from '../api';
import { fallbackConfig } from '../configDefaults';
import { signAndSubmit } from '../wallet';
import type { AssetConfig, WalletState } from '../types';

function fmt(value: number | undefined) {
  if (value === undefined || Number.isNaN(value)) return '-';
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(value);
}

function short(value: string | undefined, start = 14, end = 10) {
  if (!value) return '-';
  if (value.length <= start + end) return value;
  return `${value.slice(0, start)}...${value.slice(-end)}`;
}

function isAda(asset: AssetConfig | undefined) {
  return asset?.policy_id === '' && asset?.asset_name === '';
}

export default function TokenMintPage({ wallet }: { wallet?: WalletState; setWallet: (wallet?: WalletState) => void }) {
  const queryClient = useQueryClient();
  const config = useQuery({ queryKey: ['config'], queryFn: api.config });
  const appConfig = config.data ?? fallbackConfig;
  const [pairId, setPairId] = useState(appConfig.pairs[0]?.id ?? 'muesli-swap');
  const [amounts, setAmounts] = useState({ baseAmount: 1_000_000, quoteAmount: 1_000_000 });
  const [txHash, setTxHash] = useState<string>();
  const pair = appConfig.pairs.find((item) => item.id === pairId) ?? appConfig.pairs[0];
  const balance = useQuery({
    queryKey: ['token-balance', wallet?.address, pairId],
    queryFn: () => api.tokenCheck(wallet!.address, pairId),
    enabled: Boolean(wallet),
    refetchInterval: 10000
  });

  const baseIsAda = isAda(pair?.base);
  const quoteIsAda = isAda(pair?.quote);
  const canMint = Boolean(
    wallet &&
    pair &&
    (baseIsAda || amounts.baseAmount > 0) &&
    (quoteIsAda || amounts.quoteAmount > 0) &&
    (!baseIsAda || !quoteIsAda)
  );
  const mintMutation = useMutation({
    mutationFn: async () => {
      if (!wallet) throw new Error('Connect a wallet first.');
      const mintTx = await api.tokenMintTx({
        walletAddress: wallet.address,
        pairId,
        baseAmount: amounts.baseAmount,
        quoteAmount: amounts.quoteAmount
      });
      const submitted = await signAndSubmit(wallet, mintTx.cborHex);
      setTxHash(submitted);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['token-balance'] }),
        queryClient.invalidateQueries({ queryKey: ['orders'] }),
        queryClient.invalidateQueries({ queryKey: ['analytics'] })
      ]);
      return submitted;
    }
  });

  const tokenRows = useMemo(() => {
    if (!pair) return [];
    return [
      {
        key: 'base',
        ticker: pair.base.ticker,
        held: balance.data?.base.amount
      },
      {
        key: 'quote',
        ticker: pair.quote.ticker,
        held: balance.data?.quote.amount
      }
    ];
  }, [balance.data?.base.amount, balance.data?.quote.amount, pair]);

  return (
    <Box className="did-setup-page">
      <Card className="did-setup-hero">
        <CardContent>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} justifyContent="space-between">
            <Box>
              <Typography variant="h3" className="market-title" sx={{ mt: 1.5 }}>
                Test Tokens
              </Typography>
              <Typography className="market-subtitle">
                Mint the configured Preprod pair assets into the connected wallet.
              </Typography>
            </Box>
            <Box className="setup-score-card">
              <span>{balance.data?.hasBase && balance.data?.hasQuote ? '2/2' : balance.data?.hasBase || balance.data?.hasQuote ? '1/2' : '0/2'}</span>
              <small>tokens held</small>
            </Box>
          </Stack>
        </CardContent>
      </Card>

      <Grid container spacing={2.5}>
        <Grid item xs={12} md={5}>
          <Card className="panel-card">
            <CardContent>
              <Stack spacing={2.25}>
                <Box>
                  <Typography variant="overline">Mint</Typography>
                  <Typography variant="h5">Pair Faucet</Typography>
                </Box>

                <TextField
                  select
                  label="Pair"
                  value={pairId}
                  onChange={(event) => setPairId(event.target.value)}
                  fullWidth
                >
                  {appConfig.pairs.map((item) => (
                    <MenuItem key={item.id} value={item.id}>
                      {item.base.ticker}/{item.quote.ticker}
                    </MenuItem>
                  ))}
                </TextField>

                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
                  <TextField
                    label={`${pair?.base.ticker ?? 'Base'} amount`}
                    type="number"
                    value={amounts.baseAmount}
                    onChange={(event) => setAmounts({ ...amounts, baseAmount: Number(event.target.value) })}
                    fullWidth
                    disabled={baseIsAda}
                    helperText={baseIsAda ? 'ADA is funded from the Preprod faucet.' : 'Mintable test token amount'}
                    inputProps={{ min: 1, max: 10_000_000 }}
                  />
                  <TextField
                    label={`${pair?.quote.ticker ?? 'Quote'} amount`}
                    type="number"
                    value={amounts.quoteAmount}
                    onChange={(event) => setAmounts({ ...amounts, quoteAmount: Number(event.target.value) })}
                    fullWidth
                    disabled={quoteIsAda}
                    helperText={quoteIsAda ? 'ADA is funded from the Preprod faucet.' : 'Mintable test token amount'}
                    inputProps={{ min: 1, max: 10_000_000 }}
                  />
                </Stack>

                <Button
                  variant="contained"
                  size="large"
                  startIcon={<AddCircleIcon />}
                  disabled={!canMint || mintMutation.isPending}
                  onClick={() => mintMutation.mutate()}
                >
                  {mintMutation.isPending ? 'Preparing mint...' : 'Mint Test Tokens'}
                </Button>

                {!wallet && <Alert severity="info">Connect a Preprod wallet before minting.</Alert>}
                {(baseIsAda || quoteIsAda) && (
                  <Alert severity="info">
                    ADA is native testnet currency. This faucet only mints the configured MUESLI and SWAP assets.
                  </Alert>
                )}
                {mintMutation.error && (
                  <Alert severity="error">
                    {mintMutation.error instanceof Error ? sanitizeErrorMessage(mintMutation.error.message, 'Mint failed') : 'Mint failed'}
                  </Alert>
                )}
                {txHash && (
                  <Alert severity="success">
                    Submitted {short(txHash)}
                  </Alert>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={7}>
          <Card className="panel-card">
            <CardContent>
              <Stack spacing={2}>
                <Box>
                  <Typography variant="overline">Wallet</Typography>
                  <Typography variant="h5">Token Balances</Typography>
                </Box>
                <Grid container spacing={1.5}>
                  {tokenRows.map((token) => (
                    <Grid item xs={12} sm={6} key={token.key}>
                      <Box className={`token-balance-card ${token.held ? 'is-funded' : 'is-empty'}`}>
                        <Box className="token-balance-card-head">
                          <Box className="token-balance-icon">
                          {token.held ? <CheckCircleIcon /> : <TokenIcon />}
                          </Box>
                          <Box>
                            <Typography variant="overline">{token.ticker}</Typography>
                            <Typography variant="caption" className="token-balance-status">
                              {token.held ? 'Available' : ''}
                            </Typography>
                          </Box>
                        </Box>
                        <Typography className="token-balance-value">{fmt(token.held)}</Typography>
                        <Typography variant="caption" className="token-balance-label">Wallet balance</Typography>
                      </Box>
                    </Grid>
                  ))}
                </Grid>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
