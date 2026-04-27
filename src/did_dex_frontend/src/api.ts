import type {
  Analytics,
  AppConfig,
  DIDRegistration,
  DIDStatus,
  Order,
  TokenBalance,
  TokenMintTxResponse,
  Trade,
  TradeFillEvent,
  TxBuildResponse
} from './types';

const API_BASE_URL = 'https://preprod.did-dex-api.muesliswap.com';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {})
    }
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  config: () => request<AppConfig>('/api/config'),
  didCheck: (walletAddress: string) =>
    request<DIDStatus>('/api/did/check', {
      method: 'POST',
      body: JSON.stringify({ walletAddress })
    }),
  registerDid: (payload: {
    walletAddress: string;
    displayName: string;
    country: string;
    idType: string;
    idNumber: string;
  }) =>
    request<{ registration: DIDRegistration }>(
      '/api/did/register',
      {
        method: 'POST',
        body: JSON.stringify(payload)
      }
    ),
  didMintTx: (registrationId: number) =>
    request<{ cborHex: string; policyId: string; assetName: string }>('/api/did/mint-tx', {
      method: 'POST',
      body: JSON.stringify({ registrationId })
    }),
  didConfirm: (registrationId: number, txHash: string) =>
    request('/api/did/confirm', {
      method: 'POST',
      body: JSON.stringify({ registrationId, txHash })
    }),
  tokenCheck: (walletAddress: string, pairId: string) =>
    request<TokenBalance>('/api/tokens/check', {
      method: 'POST',
      body: JSON.stringify({ walletAddress, pairId })
    }),
  tokenMintTx: (payload: {
    walletAddress: string;
    pairId: string;
    baseAmount: number;
    quoteAmount: number;
  }) =>
    request<TokenMintTxResponse>('/api/tokens/mint-tx', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  orders: (pairId: string) => request<{ orders: Order[] }>(`/api/orders?pairId=${pairId}`),
  analytics: (pairId: string) => request<Analytics>(`/api/analytics?pairId=${pairId}`),
  trades: (pairId: string) => request<{ trades: Trade[] }>(`/api/trades?pairId=${pairId}`),
  placeOrder: (payload: {
    walletAddress: string;
    pairId: string;
    side: 'sell_base' | 'sell_quote';
    sellAmount: number;
    buyAmount: number;
    allowPartial: boolean;
  }) =>
    request<TxBuildResponse>('/api/tx/place-order', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  cancelOrder: (walletAddress: string, orderRef: string, pairId: string) =>
    request<TxBuildResponse>('/api/tx/cancel-order', {
      method: 'POST',
      body: JSON.stringify({ walletAddress, orderRef, pairId })
    }),
  fillOrder: (walletAddress: string, orderRef: string, pairId: string) =>
    request<TxBuildResponse>('/api/tx/fill-order', {
      method: 'POST',
      body: JSON.stringify({ walletAddress, orderRef, pairId })
    }),
  confirmTx: (walletAddress: string, txHash: string, event: TradeFillEvent) =>
    request<{ trade: Trade }>('/api/tx/confirm', {
      method: 'POST',
      body: JSON.stringify({ walletAddress, txHash, event })
    })
};
