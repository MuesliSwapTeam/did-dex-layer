import { configureStore } from '@reduxjs/toolkit'
import {authSlice} from "./state/auth";
import {actionSlice} from "./state/action";
import {signUpSlice} from "./state/signUp";

export const store = configureStore({
  reducer: {
    auth: authSlice.reducer,
    signUp: signUpSlice.reducer,
    action: actionSlice.reducer
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
