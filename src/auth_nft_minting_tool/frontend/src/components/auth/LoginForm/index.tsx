import {FC, useEffect, useState} from "react";
import Button from "@mui/material/Button";
import * as ProofSpace from 'ssi-auth-lib';
import {CSSProperties} from "react";
import {useAppDispatch, useWillUnmount} from "../../../app/hooks";
import {appConfig} from "../../../app/cfg/config";
import {updateToken} from "../../../app/state/auth";
import {Typography} from "@mui/material";
import logoBig from "../../../muesli_logo.png";

const ELEMENT = 'signInQr';

// const SignUpButton = (props: {disabled?: boolean}) => {
//   const navigate = useNavigate();
//   const handleClick = () => navigate(`${appConfig().ROOT}${AuthPath.SIGN_UP}`);
//   return (
//     <Button disabled={props.disabled} onClick={handleClick}>Sign Up</Button>
//   );
// };

interface IProps {
  style?: CSSProperties;
}

const LoginForm: FC<IProps> = ({style}) => {
  const dispatch = useAppDispatch();
  const [isExpired, setIsExpired] = useState(false);

  useWillUnmount(() => {
    ProofSpace.WebLinker.stop();
  });

  useEffect(() => {
    const elem = document.getElementById(ELEMENT) as HTMLDivElement;

    if (elem && !isExpired) {
      let env = ProofSpace.ENV.PROD;
      console.log("ENVV is", appConfig().ENV)
      console.log("CLIENT is", appConfig().OAUTH_CLIENT_ID)
      if (appConfig().ENV === 'test') {
        env = ProofSpace.ENV.TEST;
      } else if (appConfig().ENV === 'stage') {
        env = ProofSpace.ENV.STAGE;
      }
      ProofSpace.WebLinker.startWithSSIOAuth(elem, {
        env,
        clientId: appConfig().OAUTH_CLIENT_ID,
        serviceDid: appConfig().SERVICE_DID,
        interactionId: appConfig().OAUTH_ACTION_ID,
        instanceId: appConfig().OAUTH_INSTANCE_ID,
        size: 400,
        button: {
          text: 'Authorize via ProofSpace',
          style: 'height: 64px; background-color: #5D4AEE; border-color: #5D4AEE; border: 1px; color: #FFFFFF; padding: 16px; font-size: 16px'
        },
        loadingButton: {
          style: 'height: 64px; background-color: #5D4AEE; border-color: #5D4AEE; border: 1px; color: #FFFFFF; padding: 16px; font-size: 16px; opacity: 0.3'
        }
      }).then((result) => {
        dispatch(updateToken(result.access_token));
      }).catch((e) => {
        ProofSpace.WebLinker.stop();
        setIsExpired(true);
      });
    }
  }, [dispatch, isExpired]);

  return (
    <div style={{textAlign: 'center', alignContent: 'center'}}>
      <div>
        <img src={logoBig} alt="MuesliSwap logo" />
      </div>
      <Typography sx={{ fontSize: 25, fontWeight: 500 }} component="div">
        Atala PRISM DID Authentication Demo
      </Typography>
      <div>
        <Typography sx={{ fontSize: 20, fontWeight: 500 }} component="div">
          Please scan the QR-code to login.
        </Typography>
        <div style={{paddingTop: 16}}/>
        {isExpired ? (
            <div style={{paddingTop: 16}}>
              <div>Login session is expired, please, try again</div>
              <Button variant={'outlined'} onClick={() => setIsExpired(false)}>Try again</Button>
            </div>) :
          (<div id={ELEMENT}/>)
        }
      </div>
    </div>
  );
}

export default LoginForm;
