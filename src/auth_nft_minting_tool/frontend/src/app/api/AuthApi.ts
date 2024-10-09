import {httpGetJSON, token} from './Fetch';
import {appConfig} from '../cfg/config';
import {AccessLevel, User} from "../../domain/User";

export class AuthApi {

  async getStatus(): Promise<User> {
    /*await wait(3000);
    return {did: '123', accessLevel: AccessLevel.HIGH};*/
    let resp: User = {connect_did: 'unknown', atala_did: 'unknown', challenge: 'null', challenge_timestamp: 'null', access_level: AccessLevel.NONE};
    try {
      // TODO: use axios again when deploy to production
      //   resp = await httpGetJSON(`${appConfig().BACKEND}/status`, token(), {ignoreErrors: true});

      const headers = new Headers();
      headers.append('Authorization', `Bearer ${token()}`);
      headers.append('Content-Type', 'application/json');

      const r = await fetch(`${appConfig().BACKEND}/status`, { method: 'GET', headers: headers });
      resp = await r.json();
    } catch (e) {
      // do nothing
    }
    return resp;
  }

  async getSignUpCode(): Promise<string> {
    const resp = await httpGetJSON(`${appConfig().BACKEND}/generate-sign-up-code`);
    return resp.code;
  }

  async checkIsComplete(code: string): Promise<boolean> {
    const resp = await httpGetJSON(`${appConfig().BACKEND}/is-code-done/${code}`);
    return resp.done;
  }
}
