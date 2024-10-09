import { FC, useState, useCallback, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, Stack, Typography, Button } from "@mui/material";
import { ConnectWalletButton } from '@cardano-foundation/cardano-connect-with-wallet';
import {useAppSelector} from "../app/hooks";

const PREV_WALLET_LS_ID = "did-preferred-wallet-connector"


interface ICardanoLib {
    cardanoInit: () => Promise<undefined>
    mintToken: (wallet: IWallet, s1: string, s2: string) => Promise<undefined>
}

interface IWallet {
    getUsedAddresses: () => Promise<string[]>
    getUnusedAddresses: () => Promise<string[]>
    getAddress: () => Promise<string>
}

const MintingPage: FC<{}> = () => {
    const [cardanoLib, setCardanoLib] = useState<ICardanoLib>()
    const [wallet, setWallet] = useState<IWallet>()
    const [error, setError] = useState<Error>()

    const connectWallet = useCallback((connector: string) => {
        // remember wallet for page reloads
        window.localStorage.setItem(PREV_WALLET_LS_ID, connector)
        // Initialize cardano lib
        import('../cardano/muesliswap/governance').then(async (lib) => {
            await lib.cardanoInit()
            setCardanoLib(lib as any as ICardanoLib)
        });
        // Initialize wallet
        (window as any).cardano[connector].enable().then(async (oldWallet: IWallet) => {
            const wallet: IWallet = ({
                ...oldWallet,
                getAddress: async () => {
                    const addr = await oldWallet.getUsedAddresses();
                    if (!addr.length) {
                        return (await oldWallet.getUnusedAddresses())[0]
                    }
                    return addr[0]
                }
            })
            setWallet(wallet)
        })
    }, [])

    const initialLoad = useRef(true)
    useEffect(() => {
        if (!initialLoad.current) return

        initialLoad.current = false
        const prevConnector = window.localStorage.getItem(PREV_WALLET_LS_ID)
        if (prevConnector != null) {
            connectWallet(prevConnector)
        }
    }, [connectWallet])

    const user = useAppSelector((state) => state.auth.user);
    const atala_did = user?.atala_did.split(":").slice(-1)[0] || 'unknown';
    const challenge = user?.challenge || 'null';

    return (
        <Stack direction={'row'}>
            <Card sx={{ width: '100%' }}>
                <CardHeader
                    style={{ backgroundColor: '#f7f2a1' }}
                    title={(
                        <Typography sx={{ fontSize: 26, fontWeight: 400 }} component="div">
                            Welcome!
                        </Typography>
                    )}
                />
                <CardContent sx={{ minHeight: '300px' }}>
                    <ConnectWalletButton
                        limitNetwork={"testnet" as never}
                        message="Please sign Augusta Ada King, Countess of Lovelace"
                        onConnect={connectWallet}
                        onDisconnect={() => setWallet(undefined)}
                    />
                    <div style={{ height: "50px" }} />
                    <Button disabled={!wallet || !cardanoLib} onClick={() => {
                        try {
                            cardanoLib!.mintToken(wallet!, atala_did, challenge)
                        } catch (e: any) {
                            console.error(e)
                            setError(e as Error)
                        }
                    }}>Mint</Button>
                    {error != null && <CardContent>
                        <p>An error occured: {error.message}</p>
                    </CardContent>}
                </CardContent>
            </Card>
        </Stack>
    )
};

export default MintingPage;
