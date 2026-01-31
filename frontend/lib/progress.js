import NProgress from 'nprogress';

let configured = false;
let inflight = 0;

export function configureProgress() {
  if (configured) return;
  configured = true;

  NProgress.configure({
    showSpinner: false,
    trickle: true,
    trickleSpeed: 140,
    minimum: 0.15,
  });
}

export function progressStart() {
  if (typeof window === 'undefined') return;
  configureProgress();
  inflight += 1;
  if (inflight === 1) NProgress.start();
}

export function progressDone() {
  if (typeof window === 'undefined') return;
  configureProgress();
  inflight = Math.max(0, inflight - 1);
  if (inflight === 0) NProgress.done(true);
}

export function progressReset() {
  inflight = 0;
  if (typeof window !== 'undefined') NProgress.done(true);
}
