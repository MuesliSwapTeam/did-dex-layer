import {lazy} from 'react';
import {createBrowserRouter, Navigate, Outlet, redirect} from 'react-router-dom';

import {AccessLevel, User} from "../domain/User";
import {AuthPath} from "../app/cfg/RoutePath";
import Loadable from "../components/LoadableComponent";
import Main from "../components/Main";

const LoginForm = Loadable(lazy(() => import("../components/auth/LoginForm")));
const MintingPage = Loadable(lazy(() => import('../components/MintingPage')));

export const createRoutes = (root: string, user?: User) => {
  const createAccessGuard = (levelRequired: AccessLevel) => async () => {
    const accessLevel = user?.access_level || AccessLevel.NONE;
    if (accessLevel < levelRequired) {
      return redirect(root);
    }
    return null;
  };

  const authGuard = async () => {
    if (!user || !user.access_level || user.access_level <= AccessLevel.NONE) {
      return redirect(`${root}${AuthPath.LOGIN}`);
    }
    return null;
  };

  const isLoggedIn = async () => {
    if (user && user.access_level > AccessLevel.NONE) {
      return redirect(`${root}level${user.access_level}`);
    }
    return null;
  };

  return createBrowserRouter([
    {
      path: `${root}`,
      element: <Main><Outlet/></Main>,
      children: [
        {
          path: AuthPath.LOGIN,
          loader: isLoggedIn,
          element: <LoginForm />
        },
        {
          path: '',
          element: <Outlet/>,
          loader: authGuard,
          children: [
            {path: '', index: true, element: <MintingPage />},
            {
              path: 'minting-page',
              loader: createAccessGuard(AccessLevel.LOW),
              element: <MintingPage />,
            },
          ]
        },
        {path: '*', element: <Navigate to="" />}
      ]
    }
  ]);
}
