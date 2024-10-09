import {User} from "../../domain/User";
import {createAsyncThunk, createSlice, PayloadAction} from "@reduxjs/toolkit";
import {authApi} from "../api/API";
import {dropToken, setToken} from "../api/Fetch";
import {dropActionState} from "./action";

export interface AuthState {
  isLoading?: boolean;
  user?: User;
}

const initialState: AuthState = {
  user: undefined,
  isLoading: true, // TODO: hack. Investigate what and were Vova add bug.
};

export const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setLoading: (state) => {
      state.isLoading = true;
    },
    setUser: (state, action: PayloadAction<User>) => {
      state.user = action.payload;
      state.isLoading = false;
    },
    dropUser: (state) => {
      state.user = undefined;
    },
  }
});

const {setLoading, setUser, dropUser} = authSlice.actions;

export const status = createAsyncThunk('status', async (_, {dispatch}) => {
  dispatch(setLoading());
  const user = await authApi.getStatus();
  dispatch(setUser(user));
});

export const logout = createAsyncThunk('logout', async (_, {dispatch}) => {
  dropToken();
  dispatch(dropUser());
});

export const updateToken = createAsyncThunk('update-token', async (token: string, {dispatch}) => {
  await dispatch(dropActionState());
  setToken(token);
  await dispatch(status());
});
