import {TypedUseSelectorHook, useDispatch, useSelector} from 'react-redux';
import type {RootState, AppDispatch} from './store';
import {useEffect} from "react";

export const useDidMount = (callback: () => void) => {
  // Replaces componentDidMount
  useEffect(() => {
    callback();
  }, []);
};

export const useWillUnmount = (callback: () => void) => {
  useEffect(() => {
    return () => {
      callback();
    }
  }, []);
};

export const useAppDispatch: () => AppDispatch = useDispatch;
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
