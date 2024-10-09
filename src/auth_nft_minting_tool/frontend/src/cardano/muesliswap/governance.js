import { initTx, finalizeTX } from './base'
import Loader from '../helpers/loader.js'
import { fromHex, toHex } from '../helpers/utils.js'
import { ATALA_DID_CONTRACT } from '../constants'
import { sha256 } from 'js-sha256';

const CIP25 = 721
const TRANSACTION_MESSAGE = 674
const ATALA_DID = 2001
const CHALLENGE_RESPONSE = 2002

export const cardanoInit = async () => {
  await Loader.load()
}

// TODO: we might just take the wallet address and parse it?
export async function mintToken(wallet, atalaDid, challenge) {
  const { txBuilder, datums, outputs } = await initTx(false)

  const walletAddress = Loader.Cardano.BaseAddress.from_address(
    Loader.Cardano.Address.from_bytes(fromHex(await wallet.getAddress())),
  )

  const utxos = (await wallet.getUtxos()).map((utxo) =>
    Loader.Cardano.TransactionUnspentOutput.from_bytes(fromHex(utxo)),
  )

  const newMetadata = {
    [CIP25]: {},
    [TRANSACTION_MESSAGE]: {},
    [ATALA_DID]: {},
  }

  newMetadata[TRANSACTION_MESSAGE] = { msg: ['Mint Atala PRISM DID authentication NFT'] }
  newMetadata[ATALA_DID] = atalaDid
  newMetadata[CHALLENGE_RESPONSE] = sha256(challenge)
  console.log(challenge, sha256(challenge))

  const policyIdHex = 'af78c4045c506fe71a85b942e032e968587eb132363b4a364b5cae00' // '358587601623527cb63a89afba9873a97c407df960d19e21e11f6d15' //
  const assetNameHex = toHex(sha256(atalaDid).slice(0, 32))
  const nftMeta = {
    name: 'Mint Atala DID authentication NFT',
    description: ['An NFT that authenticates a user ', 'via his/her Atala PRISM DID.'],
  }
  const cip25Meta = { version: 2 }
  cip25Meta['0x' + assetNameHex] = nftMeta

  newMetadata[CIP25]['0x' + policyIdHex] = cip25Meta
  const mintBuilder = Loader.Cardano.MintBuilder.new()

  const plutusScript = ATALA_DID_CONTRACT()

  const plutusScriptSource = Loader.Cardano.PlutusScriptSource.new(plutusScript)

  const redeemerList = Loader.Cardano.PlutusList.new()
  redeemerList.add(Loader.Cardano.PlutusData.new_bytes(fromHex("abcd")))
  redeemerList.add(Loader.Cardano.PlutusData.new_bytes(fromHex("abcd")))

  const redeemerData = Loader.Cardano.PlutusData.new_constr_plutus_data(
    Loader.Cardano.ConstrPlutusData.new(Loader.Cardano.BigNum.from_str('0'), redeemerList),
  )

  const redeemer = Loader.Cardano.Redeemer.new(
    Loader.Cardano.RedeemerTag.new_mint(),
    Loader.Cardano.BigNum.from_str('0'),
    redeemerData,
    Loader.Cardano.ExUnits.new(Loader.Cardano.BigNum.from_str('1010000'), Loader.Cardano.BigNum.from_str('500000000')),
  )

  // add required signers
  txBuilder.add_required_signer(
    Loader.Cardano.Ed25519KeyHash.from_bytes(walletAddress.payment_cred().to_keyhash().to_bytes()),
  )
  txBuilder.add_required_signer(
    Loader.Cardano.Ed25519KeyHash.from_bytes(walletAddress.stake_cred().to_keyhash().to_bytes()),
  )
  /*txBuilder.add_required_signer(
    Loader.Cardano.Ed25519KeyHash.from_hex("2ec86e38df0ec36f44da9d8fcb8c6abd15189049382b079ff0c314b9")
  )*/

  const mintWitness = Loader.Cardano.MintWitness.new_plutus_script(plutusScriptSource, redeemer)
  const assetName = Loader.Cardano.AssetName.new(fromHex(assetNameHex))
  mintBuilder.add_asset(mintWitness, assetName, Loader.Cardano.Int.from_str('1'))
  txBuilder.set_mint_builder(mintBuilder)

  const txCbor = await finalizeTX(
    wallet,
    txBuilder,
    walletAddress,
    utxos,
    outputs,
    datums,
    newMetadata,
    null,
    null,
    false,
    false,
    true,
  )

  const txHash = await wallet.submitTx(toHex(txCbor))
  console.log(txHash)

  return txCbor
}

export async function getAllDelegationTokens(wallet) {
  const policyId = '3c84b8302198a7fe0beaafb9bbefd53010b047413d8832f3a76b9241'
  var tokenList = []

  if (!wallet) return tokenList

  const valueHex = await wallet.getBalance()
  const value = Loader.Cardano.Value.from_bytes(fromHex(valueHex))

  if (!value.multiasset()) {
    return tokenList
  }

  const scriptHashPolicyId = Loader.Cardano.ScriptHash.from_bytes(fromHex(policyId))
  const policy = value.multiasset().get(scriptHashPolicyId)

  if (policy) {
    var keys = policy.keys()

    for (var i = 0; i < keys.len(); i++) {
      tokenList.push(toHex(keys.get(i).name()))
    }
  }

  return tokenList
}
