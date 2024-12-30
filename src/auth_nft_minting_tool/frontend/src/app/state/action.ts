import {createAsyncThunk, createSlice} from "@reduxjs/toolkit";
import {actionApi} from "../api/API";
import {CompleteWatcher} from "../api/CompleteWatcher";

export interface ActionState {
  isLoading?: boolean;
  isSent: boolean;
  isVerificationComplete: boolean;
  isSkillComplete: boolean;
}

const initialState: ActionState = {
  isSent: false,
  isVerificationComplete: false,
  isSkillComplete: false
};

export const actionSlice = createSlice(  {
  name: 'action',
  initialState,
  reducers: {
    setLoading: (state) => {
      state.isLoading = true;
    },
    send: (state) => {
      state.isSent = true;
      state.isLoading = false;
    },
    drop: (state) => {
      state.isSent = false;
      state.isLoading = false;
      state.isSkillComplete = false;
      state.isVerificationComplete = false;
    },
    setVerificationComplete: (state) => {
      state.isVerificationComplete = true;
    },
    setSkillComplete: (state) => {
      state.isSkillComplete = true;
    }
  }
});

const {setLoading, send, drop, setVerificationComplete, setSkillComplete} = actionSlice.actions;

let verificationWatcher: CompleteWatcher | undefined;
let skillWatcher: CompleteWatcher | undefined;

export const sendAnswer = createAsyncThunk('send-answer', async (answer: string, {dispatch}) => {
  if (skillWatcher) {
    skillWatcher.stop();
  }
  dispatch(setLoading());
  await actionApi.sendAnswer(answer);
  skillWatcher = new CompleteWatcher(() => actionApi.isSkillComplete(), () => dispatch(setSkillComplete()));
  skillWatcher.start();
  dispatch(send());
});

export const stopSkillProcess = createAsyncThunk('stop-skill-process', async (_, {dispatch}) => {
  if (skillWatcher) {
    skillWatcher.stop();
  }
});

export const startVerificationProcess = createAsyncThunk('start-verification-process', async (_, {dispatch}) => {
  if (verificationWatcher) {
    verificationWatcher.stop();
  }
  verificationWatcher = new CompleteWatcher(() => actionApi.isVerificationComplete(), () => dispatch(setVerificationComplete()));
  verificationWatcher.start();
});

export const stopVerificationProcess = createAsyncThunk('stop-verification-process', async (_, {dispatch}) => {
  if (verificationWatcher) {
    verificationWatcher.stop();
  }
});

export const dropActionState = createAsyncThunk('drop-action-state', async (_, {dispatch}) => {
  if (skillWatcher) {
    skillWatcher.stop();
  }
  if (verificationWatcher) {
    verificationWatcher.stop();
  }
  dispatch(drop());
});
