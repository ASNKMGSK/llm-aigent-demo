import { Toaster } from 'react-hot-toast';

export default function ToastProvider() {
  return (
    <Toaster
      position="top-right"
      toastOptions={{
        duration: 2600,
        style: {
          background: 'rgba(255,255,255,0.92)',
          color: '#0f172a',
          border: '1px solid rgba(15,23,42,0.10)',
          borderRadius: '14px',
          boxShadow: '0 18px 32px rgba(15,23,42,0.10)',
        },
      }}
    />
  );
}
