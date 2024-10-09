import {httpGetJSON, httpPostJSON, token} from "./Fetch";
import {appConfig} from "../cfg/config";

export class ActionApi {
  async sendAnswer(answer: string) {
    /*await wait(3000);
    return {ok: true};*/
    const resp = await httpPostJSON(`${appConfig().BACKEND}/confirm-skill`, {answer}, token());
    return resp;
  }

  async isVerificationComplete(): Promise<boolean> {
    const resp = await httpGetJSON(`${appConfig().BACKEND}/is-verification-complete`, token());
    return resp.done;
  }

  async isSkillComplete(): Promise<boolean> {
    const resp = await httpGetJSON(`${appConfig().BACKEND}/is-skill-complete`, token());
    return resp.done;
  }
}
