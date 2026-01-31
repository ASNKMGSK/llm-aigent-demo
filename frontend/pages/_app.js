import '@/styles/globals.css';
import '@/styles/nprogress.css';

import { useEffect } from 'react';
import Router from 'next/router';

import ToastProvider from '@/components/ToastProvider';
import { progressStart, progressDone, progressReset } from '@/lib/progress';

export default function App({ Component, pageProps }) {
  useEffect(() => {
    const handleStart = () => progressStart();
    const handleStop = () => progressDone();

    Router.events.on('routeChangeStart', handleStart);
    Router.events.on('routeChangeComplete', handleStop);
    Router.events.on('routeChangeError', handleStop);

    return () => {
      Router.events.off('routeChangeStart', handleStart);
      Router.events.off('routeChangeComplete', handleStop);
      Router.events.off('routeChangeError', handleStop);
      progressReset();
    };
  }, []);

  return (
    <>
      <Component {...pageProps} />
      <ToastProvider />
    </>
  );
}
