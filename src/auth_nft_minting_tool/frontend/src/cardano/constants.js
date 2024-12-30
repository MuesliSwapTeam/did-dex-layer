import Loader from './helpers/loader.js'
import { fromHex } from './helpers/utils.js'
import { minting_script } from './plutus_scripts/atala_did_always'

export const ATALA_DID_CONTRACT = () => {
  const plutusScript = Loader.Cardano.PlutusScript.new_v2(fromHex(minting_script))
  return plutusScript
}
