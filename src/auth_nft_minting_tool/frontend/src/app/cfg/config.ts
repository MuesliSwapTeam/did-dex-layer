class ConfigData {
  readonly BACKEND: string = process.env.REACT_APP_BACKEND || 'https://api.did.muesliswap.com';
  readonly ROOT: string = process.env.REACT_APP_ROOT_PATH || '/';
  readonly ENV: string = process.env.REACT_APP_ENV || 'production';
  readonly FRONT_HOST: string = process.env.REACT_APP_FRONT_HOST || 'https://demo.did.muesliswap.com';
  // readonly SSI_OAUTH_CRED: string = process.env.REACT_APP_SSI_OAUTH_CRED || 'Wv5tREzxvixFw9MpUxcu1J:3:CL:509:tag';
  readonly DEEP_LINK_PROTOCOL: string= process.env.REACT_APP_DEEP_LINK_PROTOCOL || 'zakaio';
  readonly OAUTH_CLIENT_ID: string = process.env.REACT_APP_OAUTH_CLIENT_ID || 'd3d336e7-8b60-47b3-81ad-394906412e68';
  readonly SERVICE_DID: string = process.env.REACT_APP_SERVICE_DID || '5EgBxxf6KdASWk9q7romzn';
  readonly SIGN_UP_CRED_ID: string = process.env.REACT_APP_SIGN_UP_CRED_ID || '5EgBxxf6KdASWk9q7romzn:3:CL:710:tag';
  readonly OAUTH_ACTION_ID: string = process.env.REACT_APP_OAUTH_ACTION_ID || '1';
  readonly OAUTH_INSTANCE_ID: string = process.env.REACT_APP_OAUTH_INSTANCE_ID || '653fbfd4af49506f80a2dcfc';
  readonly SIGN_UP_ACTION_ID: string = process.env.REACT_APP_SIGN_UP_ACTION_ID || '1';
  readonly SIGN_UP_INSTANCE_ID: string = process.env.REACT_APP_SIGN_UP_INSTANCE_ID || '651423ac74de4bb197887296';
  readonly VERIFY_ACTION_ID: string = process.env.REACT_APP_VERIFY_ACTION_ID || '3';
  readonly VERIFY_INSTANCE_ID: string = process.env.REACT_APP_VERIFY_INSTANCE_ID || '651425fb74de4bb19788b04a';
}

export const deepLinkPrefix = () => `${appConfig().DEEP_LINK_PROTOCOL}://${appConfig().FRONT_HOST}/native/execute/`;

let _appConfig: ConfigData = new ConfigData();

export const appConfig = () => {
  if (_appConfig === undefined) {
    throw new Error('Attempt to use appConfig which is not defined');
  } else {
    return _appConfig;
  }
};

export const createLink = (value: string) => `${appConfig().ROOT}${value}`;
