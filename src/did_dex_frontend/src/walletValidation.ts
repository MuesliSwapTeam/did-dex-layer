import { api } from './api';
import type { WalletState } from './types';
import { PREPROD_WALLET_ERROR } from './wallet';

export async function assertBackendPreprodWallet(wallet: WalletState): Promise<void> {
  const status = await api.didCheck(wallet.address);
  if (status.addressValid === false) {
    throw new Error(status.error || PREPROD_WALLET_ERROR);
  }
}
