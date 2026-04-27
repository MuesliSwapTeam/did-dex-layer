import { afterEach, describe, expect, it, vi } from 'vitest';
import { PREPROD_WALLET_ERROR, availableWallets, connectWallet, installedWallets } from './wallet';

function setCardano(value: Record<string, unknown>) {
  Object.defineProperty(window, 'cardano', {
    configurable: true,
    value
  });
}

afterEach(() => {
  delete window.cardano;
});

describe('wallet discovery', () => {
  it('detects enumerable CIP-30 connectors and skips non-wallet properties', () => {
    setCardano({
      eternl: {
        enable: vi.fn(),
        name: 'Eternl'
      },
      metadata: {
        name: 'not a wallet'
      }
    });

    expect(availableWallets()).toEqual(['eternl']);
  });

  it('detects non-enumerable injected wallet connectors', () => {
    const cardano = {};
    Object.defineProperty(cardano, 'lace', {
      configurable: true,
      enumerable: false,
      value: {
        enable: vi.fn(),
        name: 'Lace'
      }
    });
    setCardano(cardano);

    expect(Object.keys(window.cardano ?? {})).toEqual([]);
    expect(availableWallets()).toEqual(['lace']);
  });

  it('returns wallet metadata and session state', async () => {
    setCardano({
      lace: {
        enable: vi.fn(),
        icon: 'data:image/svg+xml,lacesvg',
        isEnabled: vi.fn().mockResolvedValue(true),
        name: 'Lace'
      }
    });

    await expect(installedWallets()).resolves.toEqual([
      {
        icon: 'data:image/svg+xml,lacesvg',
        id: 'lace',
        isEnabled: true,
        label: 'Lace'
      }
    ]);
  });

  it('rejects wallets that are not on Preprod', async () => {
    const getUsedAddresses = vi.fn();
    setCardano({
      nami: {
        enable: vi.fn().mockResolvedValue({
          getNetworkId: vi.fn().mockResolvedValue(1),
          getUsedAddresses,
          getUnusedAddresses: vi.fn()
        }),
        name: 'Nami'
      }
    });

    await expect(connectWallet('nami')).rejects.toThrow(PREPROD_WALLET_ERROR);
    expect(getUsedAddresses).not.toHaveBeenCalled();
  });
});
