import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  LinearProgress,
  MenuItem,
  Stack,
  TextField,
  Typography
} from '@mui/material';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import AssignmentIndIcon from '@mui/icons-material/AssignmentInd';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import HowToRegIcon from '@mui/icons-material/HowToReg';
import KeyIcon from '@mui/icons-material/Key';
import PendingActionsIcon from '@mui/icons-material/PendingActions';
import SecurityIcon from '@mui/icons-material/Security';
import TokenIcon from '@mui/icons-material/Token';
import VerifiedUserIcon from '@mui/icons-material/VerifiedUser';
import { api } from '../api';
import { fallbackConfig } from '../configDefaults';
import { signAndSubmit } from '../wallet';
import type { WalletState } from '../types';

const MINT_CONFIRMATION_TIMEOUT_MS = 3 * 60 * 1000;
const MINT_CONFIRMATION_POLL_MS = 5000;

function short(value: string | undefined, start = 14, end = 10) {
  if (!value) return '-';
  if (value.length <= start + end) return value;
  return `${value.slice(0, start)}...${value.slice(-end)}`;
}

function SetupStep({
  active,
  complete,
  icon,
  label,
  value
}: {
  active?: boolean;
  complete?: boolean;
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <Box className={`setup-step ${complete ? 'complete' : ''} ${active ? 'active' : ''}`}>
      <Box className="setup-step-icon">{complete ? <CheckCircleIcon /> : icon}</Box>
      <Box>
        <Typography variant="body2" fontWeight={900}>{label}</Typography>
        <Typography variant="caption">{value}</Typography>
      </Box>
    </Box>
  );
}

export default function RegisterPage({
  wallet
}: {
  wallet?: WalletState;
  setWallet: (wallet?: WalletState) => void;
}) {
  const queryClient = useQueryClient();
  const config = useQuery({ queryKey: ['config'], queryFn: api.config });
  const appConfig = config.data ?? fallbackConfig;
  const [form, setForm] = useState({
    displayName: '',
    country: 'DK',
    idType: 'PASSPORT',
    idNumber: ''
  });
  const [txHash, setTxHash] = useState<string>();
  const [mintSubmittedAt, setMintSubmittedAt] = useState<number>();
  const [mintTimedOut, setMintTimedOut] = useState(false);

  const didStatus = useQuery({
    queryKey: ['did-status', wallet?.address],
    queryFn: () => api.didCheck(wallet!.address),
    enabled: Boolean(wallet),
    refetchInterval: mintSubmittedAt && !mintTimedOut ? MINT_CONFIRMATION_POLL_MS : 10000
  });

  const registerMutation = useMutation({
    mutationFn: () => api.registerDid({ walletAddress: wallet!.address, ...form }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['did-status'] })
  });

  const mintMutation = useMutation({
    mutationFn: async () => {
      const registration = registerMutation.data?.registration ?? didStatus.data?.registration;
      if (!wallet || !registration?.id) throw new Error('No approved registration is available.');
      if (didStatus.data?.hasDid) throw new Error('This wallet already holds a DID NFT.');
      const mintTx = await api.didMintTx(registration.id);
      const submitted = await signAndSubmit(wallet, mintTx.cborHex);
      setTxHash(submitted);
      setMintSubmittedAt(Date.now());
      setMintTimedOut(false);
      try {
        await api.didConfirm(registration.id, submitted);
      } finally {
        await queryClient.invalidateQueries({ queryKey: ['did-status'] });
      }
      return submitted;
    }
  });

  const registration = registerMutation.data?.registration ?? didStatus.data?.registration;
  const identityReady = Boolean(form.displayName.trim() && form.country.trim() && form.idType && form.idNumber.trim());
  const hasDid = Boolean(didStatus.data?.hasDid);
  const identityComplete = identityReady || Boolean(registration) || hasDid;
  const registrationComplete = Boolean(registration) || hasDid;
  const identityStepLabel = identityComplete
    ? identityReady
      ? 'Profile ready'
      : registration
        ? 'Profile registered'
        : 'Profile verified'
    : 'Profile incomplete';
  const identityChipLabel = identityComplete
    ? identityReady
      ? 'Profile ready'
      : registration
        ? 'Registered'
        : 'Verified'
    : 'Incomplete';
  const credentialTypeLabel = form.idType.replace('_', ' ');
  const previewApplicant = form.displayName || (registration ? `Registration #${registration.id}` : hasDid ? 'Wallet DID' : '-');
  const previewJurisdiction = identityReady ? form.country : registration || hasDid ? 'Verified' : form.country || '-';
  const previewCredential = identityReady ? credentialTypeLabel : registration || hasDid ? 'DID credential' : credentialTypeLabel;
  const isMintConfirmationPending = Boolean(mintSubmittedAt && !mintTimedOut && !hasDid);
  const submittedTxHash = txHash ?? registration?.tx_hash;
  const mintStatusLabel = hasDid
    ? 'DID active'
    : isMintConfirmationPending
      ? 'Mint pending'
      : mintTimedOut
        ? 'Confirmation timeout'
        : registration
          ? registration.status
          : 'Ready for validation';
  const mintStatusIcon = isMintConfirmationPending
    ? <CircularProgress className="chip-spinner" size={16} />
    : hasDid
      ? <VerifiedUserIcon />
      : mintTimedOut
        ? <PendingActionsIcon />
        : <TokenIcon />;
  const mintStatusColor = hasDid
    ? 'success'
    : isMintConfirmationPending
      ? 'warning'
      : mintTimedOut
        ? 'warning'
        : registration
          ? 'primary'
          : 'default';
  const progress = useMemo(() => {
    const completed = [Boolean(wallet), identityComplete, registrationComplete, hasDid].filter(Boolean).length;
    return Math.round((completed / 4) * 100);
  }, [hasDid, identityComplete, registrationComplete, wallet]);
  const actionError = hasDid ? undefined : registerMutation.error || mintMutation.error;
  const mintButtonDisabled = !wallet || !registration || mintMutation.isPending || isMintConfirmationPending || hasDid;
  const mintButtonLabel = mintMutation.isPending
    ? 'Preparing mint...'
    : isMintConfirmationPending
      ? 'Mint pending'
      : mintTimedOut
        ? 'Retry mint DID NFT'
        : 'Mint DID NFT';

  useEffect(() => {
    setTxHash(undefined);
    setMintSubmittedAt(undefined);
    setMintTimedOut(false);
  }, [wallet?.address]);

  useEffect(() => {
    if (!mintSubmittedAt || hasDid || mintTimedOut) return undefined;
    const remaining = MINT_CONFIRMATION_TIMEOUT_MS - (Date.now() - mintSubmittedAt);
    if (remaining <= 0) {
      setMintTimedOut(true);
      return undefined;
    }
    const timeout = window.setTimeout(() => {
      setMintTimedOut(true);
    }, remaining);
    return () => window.clearTimeout(timeout);
  }, [hasDid, mintSubmittedAt, mintTimedOut]);

  useEffect(() => {
    if (!hasDid || !mintSubmittedAt) return;
    setMintSubmittedAt(undefined);
    setMintTimedOut(false);
  }, [hasDid, mintSubmittedAt]);

  return (
    <Box className="did-setup-page">
      <Card className="did-setup-hero">
        <CardContent>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} justifyContent="space-between">
            <Box>
              <Typography variant="h3" className="market-title" sx={{ mt: 1.5 }}>
                DID Setup
              </Typography>
              <Typography className="market-subtitle">
                Bind a wallet, validate an identity record, and mint the DID NFT used by the orderbook.
              </Typography>
            </Box>
            <Box className="setup-score-card">
              <span>{progress}%</span>
              <small>setup complete</small>
              <LinearProgress variant="determinate" value={progress} />
            </Box>
          </Stack>
        </CardContent>
      </Card>

      <Grid container spacing={2.5}>
        <Grid item xs={12} md={4}>
          <Stack spacing={2.5}>
            <Card className="panel-card setup-progress-card">
              <CardContent>
                <Stack spacing={2}>
                  <Box>
                    <Typography variant="overline">Readiness</Typography>
                    <Typography variant="h5">Setup Progress</Typography>
                  </Box>
                  <Stack spacing={1.25}>
                    <SetupStep
                      complete={Boolean(wallet)}
                      active={!wallet}
                      icon={<AccountBalanceWalletIcon />}
                      label="Wallet"
                      value={wallet ? wallet.name : 'Connection required'}
                    />
                    <SetupStep
                      complete={identityComplete}
                      active={Boolean(wallet) && !identityComplete}
                      icon={<AssignmentIndIcon />}
                      label="Identity"
                      value={identityStepLabel}
                    />
                    <SetupStep
                      complete={registrationComplete}
                      active={identityComplete && !registrationComplete}
                      icon={<HowToRegIcon />}
                      label="Registration"
                      value={registration ? `#${registration.id} ${registration.status}` : hasDid ? 'On-chain DID found' : 'Not submitted'}
                    />
                    <SetupStep
                      complete={hasDid}
                      active={Boolean(registration) && !hasDid}
                      icon={<TokenIcon />}
                      label="DID NFT"
                      value={hasDid ? 'Active' : isMintConfirmationPending ? 'Mint pending' : submittedTxHash ? 'Submitted' : 'Pending mint'}
                    />
                  </Stack>
                </Stack>
              </CardContent>
            </Card>

          </Stack>
        </Grid>

        <Grid item xs={12} md={8}>
          <Stack spacing={2.5}>
            <Card className="panel-card did-form-card">
              <CardContent>
                <Stack spacing={2.5}>
                  <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} justifyContent="space-between">
                    <Stack direction="row" spacing={1.25} alignItems="center">
                      <AssignmentIndIcon color="primary" />
                      <Box>
                        <Typography variant="overline">Identity record</Typography>
                        <Typography variant="h5">Verification Profile</Typography>
                      </Box>
                    </Stack>
                    <Chip
                      icon={identityComplete ? <CheckCircleIcon /> : <PendingActionsIcon />}
                      label={identityChipLabel}
                      color={identityComplete ? 'success' : 'warning'}
                      variant="outlined"
                    />
                  </Stack>

                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth
                        label="Name"
                        value={form.displayName}
                        onChange={(event) => setForm({ ...form, displayName: event.target.value })}
                      />
                    </Grid>
                    <Grid item xs={12} sm={3}>
                      <TextField
                        fullWidth
                        label="Country"
                        value={form.country}
                        inputProps={{ maxLength: 2 }}
                        onChange={(event) => setForm({ ...form, country: event.target.value.toUpperCase() })}
                      />
                    </Grid>
                    <Grid item xs={12} sm={3}>
                      <TextField
                        select
                        fullWidth
                        label="ID Type"
                        value={form.idType}
                        onChange={(event) => setForm({ ...form, idType: event.target.value })}
                      >
                        <MenuItem value="PASSPORT">Passport</MenuItem>
                        <MenuItem value="NATIONAL_ID">National ID</MenuItem>
                        <MenuItem value="DRIVERS_LICENSE">Driver license</MenuItem>
                      </TextField>
                    </Grid>
                    <Grid item xs={12}>
                      <TextField
                        fullWidth
                        label="ID Number"
                        value={form.idNumber}
                        onChange={(event) => setForm({ ...form, idNumber: event.target.value })}
                      />
                    </Grid>
                  </Grid>

                  <Box className="credential-preview">
                    <Box>
                      <Typography variant="caption">Applicant</Typography>
                      <strong>{previewApplicant}</strong>
                    </Box>
                    <Box>
                      <Typography variant="caption">Jurisdiction</Typography>
                      <strong>{previewJurisdiction}</strong>
                    </Box>
                    <Box>
                      <Typography variant="caption">Credential</Typography>
                      <strong>{previewCredential}</strong>
                    </Box>
                  </Box>
                </Stack>
              </CardContent>
            </Card>

            <Card className="panel-card did-mint-card">
              <CardContent>
                <Stack spacing={2.5}>
                  <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} justifyContent="space-between">
                    <Stack direction="row" spacing={1.25} alignItems="center">
                      <KeyIcon color="primary" />
                      <Box>
                        <Typography variant="overline">Minting</Typography>
                        <Typography variant="h5">Registration & DID NFT</Typography>
                      </Box>
                    </Stack>
                    <Chip
                      icon={mintStatusIcon}
                      label={mintStatusLabel}
                      color={mintStatusColor}
                    />
                  </Stack>

                  <Grid container spacing={1.5}>
                    <Grid item xs={12} md={4}>
                      <Box className="mint-stat">
                        <span>Registration</span>
                        <strong>{registration ? `#${registration.id}` : '-'}</strong>
                      </Box>
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <Box className="mint-stat">
                        <span>Status</span>
                        <strong className={isMintConfirmationPending ? 'status-with-spinner' : undefined}>
                          {isMintConfirmationPending && <CircularProgress className="inline-spinner" size={16} />}
                          {hasDid ? 'minted' : isMintConfirmationPending ? 'pending' : mintTimedOut ? 'timeout' : registration?.status ?? '-'}
                        </strong>
                      </Box>
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <Box className="mint-stat">
                        <span>Asset name</span>
                        <code>{registration?.asset_name ? short(registration.asset_name, 10, 8) : '-'}</code>
                      </Box>
                    </Grid>
                  </Grid>

                  <Box className="kyc-provider-box">
                    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} justifyContent="space-between">
                      <Stack direction="row" spacing={1.25} alignItems="center">
                        <SecurityIcon color="primary" />
                        <Box>
                          <Typography variant="overline">KYC provider layer</Typography>
                          <Typography variant="h6">Compliant DID issuance controls</Typography>
                        </Box>
                      </Stack>
                      <Chip icon={<VerifiedUserIcon />} label="Issuer controlled" color="success" variant="outlined" />
                    </Stack>
                    <Typography variant="body2" className="kyc-provider-copy">
                      Minting is gated by an approved identity record and the permissioned issuer policy. Our code allows to easily plugin any external KYC provider for further authentication checks. 
                    </Typography>
                    <Box className="kyc-provider-grid">
                      <Box className="kyc-provider-option active">
                        <span>NONE</span>
                        <Chip label="Current review mode" size="small" color="success" />
                      </Box>
                      <Box className="kyc-provider-option disabled">
                        <span>External KYC</span>
                        <Chip label="Disabled" size="small" variant="outlined" />
                      </Box>
                      <Box className="kyc-provider-option disabled">
                        <span>Institutional KYC</span>
                        <Chip label="Disabled" size="small" variant="outlined" />
                      </Box>
                    </Box>
                  </Box>

                  {submittedTxHash && (
                    <Alert
                      severity={hasDid ? 'success' : mintTimedOut ? 'warning' : 'info'}
                      icon={isMintConfirmationPending ? <CircularProgress size={18} /> : undefined}
                    >
                      Submitted transaction: <span className="mono">{submittedTxHash}</span>
                    </Alert>
                  )}
                  {isMintConfirmationPending && (
                    <Alert severity="warning" icon={<CircularProgress size={18} />}>
                      Minting is pending. This status will stay active until the wallet DID is detected or 3 minutes pass.
                    </Alert>
                  )}
                  {mintTimedOut && !hasDid && (
                    <Alert severity="warning">
                      The DID NFT was not detected in the wallet within 3 minutes.
                    </Alert>
                  )}
                  {actionError && (
                    <Alert severity="error">
                      {actionError instanceof Error ? actionError.message : 'Registration failed'}
                    </Alert>
                  )}
                  {hasDid && (
                    <Alert icon={<VerifiedUserIcon />} severity="success">
                      This wallet already holds a valid DID DEX NFT.
                    </Alert>
                  )}

                  <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} className="mint-action-row">
                    <Button
                      variant="contained"
                      startIcon={<HowToRegIcon />}
                      disabled={!wallet || !identityReady || registerMutation.isPending || isMintConfirmationPending || hasDid}
                      onClick={() => registerMutation.mutate()}
                    >
                      Validate ID
                    </Button>
                    <Button
                      className="mint-primary-button"
                      variant="contained"
                      size="large"
                      startIcon={mintMutation.isPending || isMintConfirmationPending ? <CircularProgress size={18} /> : <TokenIcon />}
                      disabled={mintButtonDisabled}
                      onClick={() => mintMutation.mutate()}
                    >
                      {mintButtonLabel}
                    </Button>
                  </Stack>
                </Stack>
              </CardContent>
            </Card>
          </Stack>
        </Grid>
      </Grid>
    </Box>
  );
}
