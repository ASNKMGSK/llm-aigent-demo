import { cn } from '@/lib/cn';

export function Skeleton({ className = '' }) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-2xl bg-gradient-to-r from-white/60 via-white/80 to-white/60',
        className
      )}
    />
  );
}

export function SkeletonCard() {
  return (
    <div className="rounded-3xl border border-white/60 bg-white/55 p-4 shadow-sm backdrop-blur">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="mt-3 h-8 w-40" />
      <Skeleton className="mt-3 h-3 w-32" />
    </div>
  );
}
