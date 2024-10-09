import { Buffer } from 'buffer'

import Loader from './loader.js'

export const fromHex = (hex) => Buffer.from(hex, 'hex')
export const toHex = (bytes) => Buffer.from(bytes).toString('hex')
export const toBytesNum = (num) =>
  num
    .toString()
    .split('')
    .map((d) => '3' + d)
    .join('')
export const fromAscii = (hex) => Buffer.from(hex).toString('hex')

export function toAscii(hex) {
  hex = hex.toString() //force conversion
  let str = ''
  for (let i = 0; i < hex.length; i += 2) str += String.fromCharCode(parseInt(hex.substr(i, 2), 16))
  return str
}

export const assetsToValue = (assets) => {
  const multiAsset = Loader.Cardano.MultiAsset.new()
  const lovelace = assets.find((asset) => asset.unit === 'lovelace')
  const policies = [
    ...new Set(assets.filter((asset) => asset.unit !== 'lovelace').map((asset) => asset.unit.slice(0, 56))),
  ]
  policies.forEach((policy) => {
    const policyAssets = assets.filter((asset) => asset.unit.slice(0, 56) === policy)
    const assetsValue = Loader.Cardano.Assets.new()
    policyAssets.forEach((asset) => {
      assetsValue.insert(
        Loader.Cardano.AssetName.new(Buffer.from(asset.unit.slice(56), 'hex')),
        Loader.Cardano.BigNum.from_str(asset.quantity),
      )
    })
    multiAsset.insert(Loader.Cardano.ScriptHash.from_bytes(Buffer.from(policy, 'hex')), assetsValue)
  })
  const value = Loader.Cardano.Value.new(Loader.Cardano.BigNum.from_str(lovelace ? lovelace.quantity : '0'))
  if (assets.length > 1 || !lovelace) value.set_multiasset(multiAsset)
  return value
}

export const valueToAssets = (value) => {
  const assets = {}
  assets['lovelace'] = value.coin().to_str()
  if (value.multiasset()) {
    const multiAssets = value.multiasset().keys()
    for (let j = 0; j < multiAssets.len(); j++) {
      const policy = multiAssets.get(j)
      const policyAssets = value.multiasset().get(policy)
      const assetNames = policyAssets.keys()
      for (let k = 0; k < assetNames.len(); k++) {
        const policyAsset = assetNames.get(k)
        const quantity = policyAssets.get(policyAsset)
        const asset =
          Buffer.from(policy.to_bytes(), 'hex').toString('hex') +
          '.' +
          Buffer.from(policyAsset.name(), 'hex').toString('hex')
        assets[asset] = quantity.to_str()
      }
    }
  }
  return assets
}

const SLOT_CONFIG_NETWORK = {
  Mainnet: { zeroTime: 1596059091000, zeroSlot: 4492800, slotLength: 1000 }, // Starting at Shelley era
  Preview: { zeroTime: 1666656000000, zeroSlot: 0, slotLength: 1000 }, // Starting at Shelley era
  Preprod: {
    zeroTime: 1654041600000 + 1728000000,
    zeroSlot: 86400,
    slotLength: 1000,
  },
  Custom: { zeroTime: 0, zeroSlot: 0, slotLength: 0 },
}

function unixTimeToEnclosingSlot(unixTime, slotConfig) {
  const timePassed = unixTime - slotConfig.zeroTime
  const slotsPassed = Math.floor(timePassed / slotConfig.slotLength)
  return slotsPassed + slotConfig.zeroSlot
}

export function unixTimeToSlot(unixTime) {
  return unixTimeToEnclosingSlot(unixTime, SLOT_CONFIG_NETWORK['Preprod'])
}
