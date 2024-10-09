import Axios, {AxiosRequestConfig} from 'axios';
import {errorsHandler} from '../cfg/ErrorsHandler';

const TOKEN_NAME = 'ssi-auth-demo';

export const GET = 'GET';
export const POST = 'POST';
export const PUT = 'PUT';

export interface ErrorHandleOptions {
  ignoreErrors?: boolean;
  parser?: (err: any) => {error: string; stackTrace?: string};
}

export const token = () => {
  const tkn = localStorage.getItem(TOKEN_NAME);
  return tkn || undefined;
};

export const setToken = (value: string) => localStorage.setItem(TOKEN_NAME, value);

export const dropToken = () => localStorage.removeItem(TOKEN_NAME);

export const addToken = (
  config?: AxiosRequestConfig,
  token?: string
): AxiosRequestConfig | undefined => {
  if (!token) {
    return config;
  }
  const cfg: AxiosRequestConfig = config || {};
  const headers = cfg.headers || {};
  headers['Authorization'] = `Bearer ${token}`;
  cfg.headers = headers;
  return cfg;
};

export async function fetchJsonUrl(url: string, method?: string, body?: string): Promise<any> {
  const init: RequestInit = {
    credentials: 'include'
  };
  if (method && method !== GET) {
    init.method = method;
    init.body = body;
    init.headers = {
      'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8'
    };
  } else {
    init.cache = 'no-store';
  }
  const res = await fetch(url, init);
  if (!res.ok) {
    const eText = await res.text();
    console.log(eText);
    try {
      const eres = JSON.parse(eText);
      throw new Error(`${eres.error}\n${eres.stack}`);
    } catch (e) {
      let ind = eText.indexOf('<pre>');
      let msg = eText;
      if (ind >= 0) {
        msg = eText.substr(ind + 5);
        ind = msg.indexOf('</pre>');
        if (ind) {
          msg = msg.substr(0, ind);
        }
      }
      console.log(e);
      throw new Error(msg);
    }
  }
  let result = {};
  try {
    result = await res.json();
  } catch (e) {
    console.log("Can't parse json:", e);
  }
  return result;
}

const handleHTTPError = (err: any, opt?: ErrorHandleOptions) => {
  console.log(err);
  console.log(err.response);
  let resError: any = {error: err.message};
  if (err.response && err.response.data /*&& err.response.data.error*/) {
    resError = err.response.data;
    if (resError.details) {
      resError.error = resError.details;
    }
  }
  if (!opt) {
    errorsHandler.handleError(resError);
  } else if (!opt.ignoreErrors) {
    const parser = opt.parser !== undefined ? opt.parser : (e: any) => e;
    errorsHandler.handleError(parser(resError));
  } else {
    throw err;
  }
};

export const httpGetJSON = async (
  url: string,
  token?: string,
  opt?: ErrorHandleOptions
): Promise<any> => {
  try {
    const result = await Axios.get(url, addToken({withCredentials: true}, token));
    return result.data;
  } catch (err) {
    handleHTTPError(err, opt);
  }
};

export const httpGetDownload = async (
  url: string,
  token?: string,
  opt?: ErrorHandleOptions
): Promise<any> => {
  try {
    const result = await Axios.get(
      url,
      addToken({withCredentials: true, responseType: 'blob'}, token)
    );
    return result.data;
  } catch (err) {
    handleHTTPError(err, opt);
  }
};

export const httpPostJSON = async (
  url: string,
  data: any,
  token?: string,
  opt?: ErrorHandleOptions
) => {
  try {
    const result = await Axios.post(
      url,
      data,
      addToken(
        {
          headers: {Accept: 'application/json'},
          withCredentials: true
        },
        token
      )
    );
    return result.data;
  } catch (err) {
    handleHTTPError(err, opt);
  }
};

export const httpPostRaw = async (
  url: string,
  data: any,
  token?: string,
  opt?: ErrorHandleOptions
) => {
  try {
    const result = await Axios.post(
      url,
      data,
      addToken(
        {
          withCredentials: true
        },
        token
      )
    );
    return result.data;
  } catch (err) {
    handleHTTPError(err, opt);
  }
};

export const httpPostDownload = async (
  url: string,
  data: any,
  token?: string,
  opt?: ErrorHandleOptions
) => {
  try {
    const result = await Axios.post(
      url,
      data,
      addToken(
        {
          withCredentials: true,
          responseType: 'blob'
        },
        token
      )
    );
    return result.data;
  } catch (err) {
    handleHTTPError(err, opt);
  }
};

export const httpPutJSON = async (
  url: string,
  data: any,
  token?: string,
  opt?: ErrorHandleOptions
) => {
  try {
    const result = await Axios.put(
      url,
      data,
      addToken(
        {
          headers: {Accept: 'application/json'},
          withCredentials: true
        },
        token
      )
    );
    return result.data;
  } catch (err) {
    handleHTTPError(err, opt);
  }
};

export const httpPutRaw = async (
  url: string,
  data: any,
  token?: string,
  opt?: ErrorHandleOptions
) => {
  try {
    const result = await Axios.put(
      url,
      data,
      addToken(
        {
          headers: {},
          withCredentials: true
        },
        token
      )
    );
    return result.data;
  } catch (err) {
    handleHTTPError(err, opt);
  }
};

export const httpPostFormUrlencoded = async (
  url: string,
  data: any,
  token?: string,
  opt?: ErrorHandleOptions
) => {
  try {
    let body = '';
    Object.keys(data).forEach((k) => (body = `${body}&${k}=${data[k]}`));
    const result = await fetchJsonUrl(url, POST, body);
    return result;
  } catch (err) {
    handleHTTPError(err, opt);
  }
};

export const httpPostEmpty = async (url: string, token?: string, opt?: ErrorHandleOptions) => {
  try {
    const result = await Axios.post(url, undefined, addToken({withCredentials: true}, token));
    return result.data;
  } catch (err) {
    handleHTTPError(err, opt);
  }
};

export const httpDelete = async (url: string, token?: string, opt?: ErrorHandleOptions) => {
  try {
    const result = await Axios.delete(url, addToken({withCredentials: true}, token));
    return result.data;
  } catch (err) {
    handleHTTPError(err, opt);
  }
};

export const httpPutFile = async (
  url: string,
  file: File,
  fname: string,
  token?: string,
  opt?: ErrorHandleOptions
) => {
  try {
    const formData = new FormData();
    formData.append(fname, file);
    const result = await Axios.put(
      url,
      formData,
      addToken(
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          withCredentials: true
        },
        token
      )
    );
    return result.data;
  } catch (err) {
    handleHTTPError(err, opt);
  }
};
