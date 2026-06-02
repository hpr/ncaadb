import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import '@mantine/core/styles.css';
import { MantineProvider, createTheme } from '@mantine/core';
import App from './App';

import LinLibertineBold from '/fonts/LinLibertine_RB.otf?url';

const fontFace = new FontFace('Linux Libertine', `url(${LinLibertineBold})`, { weight: '700' });
document.fonts.add(fontFace);
fontFace.load();

const theme = createTheme({
  primaryColor: 'blue',
  fontFamily: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif',
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <MantineProvider theme={theme} defaultColorScheme="dark">
      <App />
    </MantineProvider>
  </StrictMode>,
);
