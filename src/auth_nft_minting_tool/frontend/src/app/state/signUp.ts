import {createAsyncThunk, createSlice, PayloadAction} from "@reduxjs/toolkit";
import {CompleteWatcher} from "../api/CompleteWatcher";
import {authApi} from "../api/API";

export interface SignUpState {
  isLoading?: boolean;
  code?: string;
  isComplete: boolean;
}

const initialState: SignUpState = {
  isComplete: false,
  isLoading: false
};

export const signUpSlice = createSlice({
  name: 'signUp',
  initialState,
  reducers: {
    setLoading: (state) => {
      state.isLoading = true;
    },
    setCode: (state, action: PayloadAction<string>) => {
      state.code = action.payload;
      state.isLoading = false;
    },
    dropCode: (state) => {
      state.code = undefined;
    },
    setComplete: (state, action: PayloadAction<boolean>) => {
      state.isComplete = action.payload;
    }
  }
});

const {setLoading, setCode, dropCode, setComplete} = signUpSlice.actions;

let watcher: CompleteWatcher | undefined;

export const getSignUpCode = createAsyncThunk('get-sign-up-code', async (_, {dispatch}) => {
  dispatch(setLoading());
  dispatch(setComplete(false));
  dispatch(dropCode());
  if (watcher) {
    watcher.stop();
  }
  const code = await authApi.getSignUpCode();
  watcher = new CompleteWatcher(() => authApi.checkIsComplete(code), () => dispatch(setComplete(true)));
  watcher.start();
  dispatch(setCode(code));
});

export const stopSignUpProcess = createAsyncThunk('stop-sign-up-process', async(_, {dispatch}) => {
  if (watcher) {
    watcher.stop();
  }
  dispatch(setComplete(false));
  dispatch(dropCode());
});
