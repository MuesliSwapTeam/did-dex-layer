export interface AssetConfig {
  policy_id: string;
  asset_name: string;
  ticker: string;
  decimals: number;
}

export interface PairConfig {
  id: string;
  base: AssetConfig;
  quote: AssetConfig;
}

export interface AppConfig {
  network: string;
  didPolicyId: string;
  orderbookScriptHash: string;
  orderbookAddress: string;
  fees: {
    minUtxo: number;
    returnReward: number;
    batchReward: number;
  };
  pairs: PairConfig[];
}

export interface DIDRegistration {
  id: number;
  wallet_address: string;
  id_hash: string;
  asset_name: string;
  policy_id: string;
  status: string;
  tx_hash?: string;
  created_at: string;
  minted_at?: string;
}

export interface DIDStatus {
  walletAddress: string;
  hasDid: boolean;
  policyId: string;
  addressValid?: boolean;
  chainAvailable: boolean;
  error?: string;
  registration?: DIDRegistration;
}

export interface TokenBalance {
  walletAddress: string;
  pairId: string;
  base: AssetConfig & { amount: number };
  quote: AssetConfig & { amount: number };
  hasBase: boolean;
  hasQuote: boolean;
}

export interface TokenMintTxResponse {
  cborHex: string;
  policyId: string;
  base: { assetName: string; amount: number };
  quote: { assetName: string; amount: number };
}

export interface Order {
  ref: string;
  pairId: string;
  ownerAddress: string;
  side: 'sell_base' | 'sell_quote';
  sellUnit: string;
  buyUnit: string;
  sellAmount: number;
  buyAmount: number;
  price: number;
  batchReward: number;
  allowPartial: boolean;
}

export interface Analytics {
  pairId: string;
  depth: {
    bids: Array<{ price: number; amount: number }>;
    asks: Array<{ price: number; amount: number }>;
  };
  spread: number | null;
  recentFills: Trade[];
  history: Array<{ time: string; price: number; volume: number }>;
  volume24h?: number;
  tradeCount24h?: number;
}

export interface TradeFillEvent {
  type: 'fill';
  pairId: string;
  orderRef: string;
  makerAddress: string;
  takerAddress: string;
  side: 'sell_base' | 'sell_quote';
  price: number;
  amount: number;
  quoteAmount: number;
}

export interface Trade extends TradeFillEvent {
  txHash: string;
  time: string;
}

export interface TxBuildResponse {
  cborHex: string;
  event?: TradeFillEvent;
}

export interface WalletState {
  name: string;
  api: CIP30WalletApi;
  address: string;
  networkId: number;
}

export interface CIP30WalletApi {
  getNetworkId(): Promise<number>;
  getChangeAddress?: () => Promise<string>;
  getUsedAddresses(): Promise<string[]>;
  getUnusedAddresses(): Promise<string[]>;
  signTx(tx: string, partialSign?: boolean): Promise<string>;
  submitTx(tx: string): Promise<string>;
}
