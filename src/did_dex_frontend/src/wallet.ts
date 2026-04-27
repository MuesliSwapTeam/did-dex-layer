import type { CIP30WalletApi, WalletState } from './types';

export interface WalletDescriptor {
  id: string;
  icon?: string;
  isEnabled: boolean;
  label: string;
}

interface CIP30WalletConnector {
  enable?: () => Promise<CIP30WalletApi>;
  icon?: string;
  isEnabled?: () => Promise<boolean>;
  name?: string;
}

declare global {
  interface Window {
    cardano?: Record<string, CIP30WalletConnector | undefined>;
  }
}

const LAST_WALLET_KEY = 'did-dex:last-wallet';
export const PREPROD_NETWORK_ID = 0;
export const PREPROD_WALLET_ERROR =
  'This interface only supports Cardano Preprod wallets. Switch your wallet network to Preprod and reconnect.';

function walletConnector(name: string): CIP30WalletConnector | undefined {
  if (typeof window === 'undefined') return undefined;
  try {
    return window.cardano?.[name];
  } catch {
    return undefined;
  }
}

export function availableWallets(): string[] {
  if (typeof window === 'undefined' || !window.cardano) return [];

  return Reflect.ownKeys(window.cardano)
    .filter((name): name is string => typeof name === 'string')
    .filter((name) => typeof walletConnector(name)?.enable === 'function')
    .sort((left, right) => {
      const leftLabel = walletConnector(left)?.name ?? left;
      const rightLabel = walletConnector(right)?.name ?? right;
      return leftLabel.localeCompare(rightLabel);
    });
}

export function walletMetadata(name: string) {
  const connector = walletConnector(name);
  return {
    icon: connector?.icon,
    label: connector?.name ?? name
  };
}

export async function walletSessionEnabled(name: string): Promise<boolean> {
  const connector = walletConnector(name);
  if (typeof connector?.isEnabled !== 'function') return false;
  return connector.isEnabled().catch(() => false);
}

export async function installedWallets(): Promise<WalletDescriptor[]> {
  const wallets = availableWallets().map(async (id) => {
    const metadata = walletMetadata(id);
    return {
      id,
      icon: metadata.icon,
      isEnabled: await walletSessionEnabled(id),
      label: metadata.label
    };
  });
  return Promise.all(wallets);
}

export function rememberWallet(name: string) {
  window.localStorage.setItem(LAST_WALLET_KEY, name);
}

export function clearRememberedWallet() {
  window.localStorage.removeItem(LAST_WALLET_KEY);
}

export function rememberedWallet() {
  return window.localStorage.getItem(LAST_WALLET_KEY);
}

function fromHex(hex: string): Uint8Array {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < bytes.length; i += 1) {
    bytes[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  }
  return bytes;
}

function toHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');
}

async function walletAddressHex(api: CIP30WalletApi): Promise<string | undefined> {
  if (typeof api.getChangeAddress === 'function') {
    const changeAddress = await api.getChangeAddress().catch(() => undefined);
    if (changeAddress) return changeAddress;
  }

  const used = await api.getUsedAddresses();
  return used[0] ?? (await api.getUnusedAddresses())[0];
}

async function addressHexToBech32(addressHex: string, networkId: number): Promise<string> {
  const CSL = await import('@emurgo/cardano-serialization-lib-browser');
  const address = CSL.Address.from_bytes(fromHex(addressHex));
  if (address.network_id() !== networkId) throw new Error(PREPROD_WALLET_ERROR);
  if (address.network_id() !== PREPROD_NETWORK_ID) throw new Error(PREPROD_WALLET_ERROR);
  if (!address.payment_cred()) throw new Error('Wallet did not return a payment address.');
  return address.to_bech32('addr_test');
}

export async function connectWallet(name: string): Promise<WalletState> {
  const connector = walletConnector(name);
  if (typeof connector?.enable !== 'function') throw new Error(`Wallet ${name} is not available.`);
  const api = await connector.enable();
  if (typeof api.getNetworkId !== 'function') throw new Error(PREPROD_WALLET_ERROR);
  const networkId = await api.getNetworkId();
  if (networkId !== PREPROD_NETWORK_ID) throw new Error(PREPROD_WALLET_ERROR);
  const addressHex = await walletAddressHex(api);
  if (!addressHex) throw new Error('Wallet did not return an address.');
  return { name, api, address: await addressHexToBech32(addressHex, networkId), networkId };
}

export async function reconnectApprovedWallet(): Promise<WalletState | undefined> {
  const name = rememberedWallet();
  if (!name) return undefined;
  const connector = walletConnector(name);
  if (!connector) return undefined;
  if (typeof connector.isEnabled !== 'function') return undefined;
  if (!(await connector.isEnabled())) return undefined;
  return connectWallet(name);
}

export async function signAndSubmit(wallet: WalletState, cborHex: string): Promise<string> {
  const CSL = await import('@emurgo/cardano-serialization-lib-browser');
  const tx = CSL.Transaction.from_bytes(fromHex(cborHex));
  const walletWitnessHex = await wallet.api.signTx(cborHex, true);
  const walletWitness = CSL.TransactionWitnessSet.from_bytes(fromHex(walletWitnessHex));
  const witnessSet = tx.witness_set();

  const existingVkeys = witnessSet.vkeys() ?? CSL.Vkeywitnesses.new();
  const walletVkeys = walletWitness.vkeys();
  if (walletVkeys) {
    for (let i = 0; i < walletVkeys.len(); i += 1) {
      existingVkeys.add(walletVkeys.get(i));
    }
  }
  witnessSet.set_vkeys(existingVkeys);

  const signed = CSL.Transaction.new(tx.body(), witnessSet, tx.auxiliary_data());
  return wallet.api.submitTx(toHex(signed.to_bytes()));
}
