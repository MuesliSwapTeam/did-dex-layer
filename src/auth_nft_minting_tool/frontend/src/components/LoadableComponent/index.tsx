import React, {Suspense, JSXElementConstructor} from "react";

import {LoaderView} from "../LoaderView";

export default function inject<TProps, TInjectedKeys extends keyof TProps>(
  Component: JSXElementConstructor<TProps>,
  injector?: Pick<TProps, TInjectedKeys>
) {
  return function Injected(props: Omit<TProps, TInjectedKeys>): React.JSX.Element {
    return (
      <Suspense fallback={<LoaderView />}>
        <Component {...(props as TProps)} {...injector} />
      </Suspense>
    );
  };
}
