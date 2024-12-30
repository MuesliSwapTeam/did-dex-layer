import {FC} from "react";
import {AppBar, Box, Button, createTheme, ThemeProvider, Toolbar} from "@mui/material";
import logo from '../muesli_logo.png';
import {useAppDispatch, useAppSelector} from "../app/hooks";
import {AccessLevel} from "../domain/User";
import {logout} from "../app/state/auth";
import LogoutIcon from "@mui/icons-material/Logout";

interface Props {
  children: any;
}

const theme = createTheme({
  palette: {
    primary: {main: '#5D4AEE'},
    secondary: {main: '#f8f8f8'},
    action: {
      disabledOpacity: 0.1,
    }
  },
  typography: {
    fontFamily: 'inherit',
    button: {
      textTransform: 'none',
      fontSize: 16
    }
  }
});

const Main: FC<Props> = ({children}) => {
  const user = useAppSelector((state) => state.auth.user);
  const level = user ? user.access_level : AccessLevel.NONE;
  const dispatch = useAppDispatch();
  const onLogout = () => dispatch(logout());

  return (
    <ThemeProvider theme={theme}>
      <Box>
        {level > AccessLevel.NONE && (
          <AppBar color="secondary" position="static">
            <Toolbar>
              <div style={{paddingTop: 8, paddingRight: 64}}>
                <img src={logo} alt="ProofSpace logo" />
              </div>
              <div style={{flexGrow: 1}} />
              <div>
                <Button onClick={onLogout} startIcon={<LogoutIcon/>} variant={'outlined'}>Logout</Button>
              </div>
            </Toolbar>
          </AppBar>
        )}
        <Box component="main" sx={{ p: 3 }}>
          {children}
        </Box>
      </Box>
    </ThemeProvider>
  );
};

export default Main;
