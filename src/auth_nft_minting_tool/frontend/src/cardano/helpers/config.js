import Loader from './loader.js'

async function muesliRequest(endpoint, body) {
  return await fetch('https://api.muesliswap.com' + endpoint, {
    method: body ? 'POST' : 'GET',
    body,
  }).then((res) => res.json())
}

async function blockfrostRequest(endpoint, body) {
  return await fetch('https://cardano-mainnet.blockfrost.io/api/v0' + endpoint, {
    headers: {
      project_id: 'mainnetoxChT32SOnqWIHAwiLXT0uXQoD8UXyMH',
      'User-Agent': 'muesliswap',
    },
    method: body ? 'POST' : 'GET',
    body,
  }).then((res) => res.json())
}

export const getPlutusScript = async (scriptHash) => {
  const script = await blockfrostRequest('/scripts/' + scriptHash + '/cbor')
  return script
}

export const getMintMetadata = async (assetName) => {
  const assetDetails = await blockfrostRequest('/assets/' + assetName)
  const mintTxHash = assetDetails['initial_mint_tx_hash']
  const metadata = await blockfrostRequest('/txs/' + mintTxHash + '/metadata/')
  return metadata
}

export const getProtocolParameters = async () => {
  const p = await muesliRequest(`/chain/epoch-parameters`)

  const protocolParameters = {
    linearFee: {
      minFeeA: p.min_fee_a.toString(),
      minFeeB: p.min_fee_b.toString(),
    },
    minUtxo: '1000000',
    coinsPerUtxoByte: p.coins_per_utxo_word,
    poolDeposit: p.pool_deposit,
    keyDeposit: p.key_deposit,
    maxValSize: parseInt(p.max_val_size),
    maxTxSize: parseInt(p.max_tx_size),
    priceMem: parseFloat(p.price_mem),
    priceStep: parseFloat(p.price_step),
    costModels: Object.fromEntries(
      Object.entries(p.cost_models).map(([k, m]) => [k, Object.values(m).map((v) => v.toString())]),
    ),
  }

  return protocolParameters
}

// the problem is that the current version of the serialization lib doesn't allow
// datums to be added as witnesses without spending a script output
// this is problematic in cases where we need to attach the datum without spending a script
// e.g. sundaeswap, minswap etc. - as the serialization lib ignores the datum witness in the fee
// computation we introduce a random hack to get the required fee by adding it to the baseFee linearB
export const getTXBuilderConfig = async (protocolParameters, addDatumWitness, multiDatum = false) => {
  await Loader.load()

  //TODO: change this to Plutus vasil cost model

  const Fraction = require('fractional').Fraction

  const priceMemFranction = new Fraction(protocolParameters.priceMem)
  const priceMemFranctionNumerator = Loader.Cardano.BigNum.from_str(priceMemFranction.numerator.toString())
  const priceMemFranctionDenominator = Loader.Cardano.BigNum.from_str(priceMemFranction.denominator.toString())
  const priceMem = Loader.Cardano.UnitInterval.new(priceMemFranctionNumerator, priceMemFranctionDenominator)

  const priceStepFranction = new Fraction(protocolParameters.priceStep)
  const priceStepFranctionNumerator = Loader.Cardano.BigNum.from_str(priceStepFranction.numerator.toString())
  const priceStepFranctionDenominator = Loader.Cardano.BigNum.from_str(priceStepFranction.denominator.toString())

  const priceStep = Loader.Cardano.UnitInterval.new(priceStepFranctionNumerator, priceStepFranctionDenominator)

  const exUnitPrices = Loader.Cardano.ExUnitPrices.new(priceMem, priceStep)

  // TODO figure out how to get the param for coins_per_utxo_byte directly
  const coinsPerUtxoByte = Math.ceil(Number(protocolParameters.coinsPerUtxoByte))

  // hack to get eternl to accept transactions
  let extraFee = 4401
  // see description above for extra fee
  // in case of multi-dex aggregator we need to add 4 times the fee amount
  if (addDatumWitness) extraFee += 15000
  if (multiDatum) extraFee += 3 * 15000

  // used protocolParameters.coinsPerUtxoWord instead of '100'
  const txBuilderConfig = Loader.Cardano.TransactionBuilderConfigBuilder.new()
    .coins_per_utxo_byte(Loader.Cardano.BigNum.from_str(coinsPerUtxoByte.toString()))
    .fee_algo(
      Loader.Cardano.LinearFee.new(
        Loader.Cardano.BigNum.from_str(protocolParameters.linearFee.minFeeA),
        Loader.Cardano.BigNum.from_str((Number(protocolParameters.linearFee.minFeeB) + extraFee).toString()),
      ),
    )
    .key_deposit(Loader.Cardano.BigNum.from_str(protocolParameters.keyDeposit))
    .pool_deposit(Loader.Cardano.BigNum.from_str(protocolParameters.poolDeposit))
    .max_tx_size(protocolParameters.maxTxSize)
    .max_value_size(protocolParameters.maxValSize)
    .ex_unit_prices(exUnitPrices)
    .prefer_pure_change(false)
    .build()

  return txBuilderConfig
}
