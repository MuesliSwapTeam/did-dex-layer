import React from 'react';
import './App.css';
import {useAppDispatch, useAppSelector, useDidMount} from "./app/hooks";
import {LoaderView} from "./components/LoaderView";
import {createRoutes} from "./routes";
import {appConfig} from "./app/cfg/config";
import {status} from "./app/state/auth";
import {RouterProvider} from "react-router-dom";

const App = () => {
  const dispatch = useAppDispatch();

  const user = useAppSelector((state) => state.auth.user);
  const isLoading = useAppSelector((state) => state.auth.isLoading);

  useDidMount(() => dispatch(status()));

  if (isLoading) {
    return <LoaderView />;
  }

  return (
    <RouterProvider router={createRoutes(appConfig().ROOT, user)} fallbackElement={<LoaderView />} />
  );
}

export default App;
