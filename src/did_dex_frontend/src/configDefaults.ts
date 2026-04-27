import type { AppConfig } from './types';

export const fallbackConfig: AppConfig = {
  network: 'preprod',
  didPolicyId: '3280db0e2bf08e6f96463a238d4faa8c4c7d7885a65199c9dd91abd8',
  orderbookScriptHash: '0146cf769189d1b86e56e14d5c76c490163e238526839c4126563f13',
  orderbookAddress: 'addr_test1wqq5dnmkjxyarwrw2ms56hrkcjgpv03rs5ng88zpyetr7yca9xgcc',
  fees: {
    minUtxo: 2300000,
    returnReward: 650000,
    batchReward: 650000
  },
  pairs: [
    {
      id: 'ada-muesli',
      base: {
        policy_id: '',
        asset_name: '',
        ticker: 'ADA',
        decimals: 6
      },
      quote: {
        policy_id: '672ae1e79585ad1543ef6b4b6c8989a17adcea3040f77ede128d9217',
        asset_name: '6d7565736c69',
        ticker: 'MUESLI',
        decimals: 0
      }
    },
    {
      id: 'ada-swap',
      base: {
        policy_id: '',
        asset_name: '',
        ticker: 'ADA',
        decimals: 6
      },
      quote: {
        policy_id: '672ae1e79585ad1543ef6b4b6c8989a17adcea3040f77ede128d9217',
        asset_name: '73776170',
        ticker: 'SWAP',
        decimals: 0
      }
    },
    {
      id: 'muesli-swap',
      base: {
        policy_id: '672ae1e79585ad1543ef6b4b6c8989a17adcea3040f77ede128d9217',
        asset_name: '6d7565736c69',
        ticker: 'MUESLI',
        decimals: 0
      },
      quote: {
        policy_id: '672ae1e79585ad1543ef6b4b6c8989a17adcea3040f77ede128d9217',
        asset_name: '73776170',
        ticker: 'SWAP',
        decimals: 0
      }
    }
  ]
};
