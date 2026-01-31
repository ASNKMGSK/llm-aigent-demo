import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { loadFromSession, STORAGE_KEYS } from '@/lib/storage';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const auth = loadFromSession(STORAGE_KEYS.AUTH, null);
    if (auth?.username && auth?.password) router.replace('/app');
    else router.replace('/login');
  }, [router]);

  return null;
}
