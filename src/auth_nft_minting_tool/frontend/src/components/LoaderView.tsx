import {Box} from '@mui/material';
import * as React from 'react';
import {CSSProperties} from 'react';

interface IProps {
  style?: CSSProperties;
}

export class LoaderView extends React.Component<IProps> {
  render() {
    return <Box textAlign="center">Loading...</Box>;
  }
}
