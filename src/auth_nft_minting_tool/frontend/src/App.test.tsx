import React from 'react';
import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';

jest.mock('./app/api/API', () => ({
  actionApi: {},
  authApi: {
    getStatus: jest.fn(() => new Promise(() => {}))
  }
}));

jest.mock('./app/api/Fetch', () => ({
  dropToken: jest.fn(),
  setToken: jest.fn()
}));

jest.mock('ssi-auth-lib', () => ({
  ENV: {
    PROD: 'prod',
    STAGE: 'stage',
    TEST: 'test'
  },
  WebLinker: {
    startWithSSIOAuth: jest.fn(),
    stop: jest.fn()
  }
}));

test('renders the application loading state', () => {
  const App = require('./App').default;
  const { store } = require('./app/store');

  render(
    <Provider store={store}>
      <App />
    </Provider>
  );

  expect(screen.getByText(/loading/i)).toBeInTheDocument();
});
