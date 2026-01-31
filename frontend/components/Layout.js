// Layout.js
import { useMemo, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import Topbar from '@/components/Topbar';
import { Noto_Sans_KR } from 'next/font/google';

const notoSansKr = Noto_Sans_KR({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  display: 'swap',
});

export default function Layout({
  auth,
  merchants,
  industries,
  selectedMerchant,
  setSelectedMerchant,
  exampleQuestions,
  onExampleQuestion,
  onLogout,
  children,
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const username = useMemo(() => auth?.username || 'USER', [auth?.username]);

  return (
    <div
      className={`${notoSansKr.className} antialiased min-h-screen bg-gradient-to-br from-rose-50 via-sky-50 to-violet-50`}
    >
      {/* 은은한 노이즈 느낌 */}
      <div className="pointer-events-none fixed inset-0 opacity-[0.06] [background-image:radial-gradient(#0f172a_1px,transparent_1px)] [background-size:18px_18px]" />

      <Topbar
        username={username}
        onOpenSidebar={() => setSidebarOpen(true)}
        onLogout={onLogout}
      />

      <div className="mx-auto max-w-[1320px] px-3 sm:px-4">
        <div className="grid grid-cols-12 gap-4 pb-10 pt-3">
          <div className="col-span-12 xl:col-span-3">
            <Sidebar
              auth={auth}
              merchants={merchants}
              industries={industries}
              selectedMerchant={selectedMerchant}
              setSelectedMerchant={setSelectedMerchant}
              exampleQuestions={exampleQuestions}
              onExampleQuestion={onExampleQuestion}
              onLogout={onLogout}
              open={sidebarOpen}
              onClose={() => setSidebarOpen(false)}
            />
          </div>

          <main className="col-span-12 xl:col-span-9">
            <div className="rounded-[32px] border border-white/60 bg-white/55 p-4 shadow-[0_18px_60px_-40px_rgba(15,23,42,0.35)] backdrop-blur md:p-5">
              {children}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
