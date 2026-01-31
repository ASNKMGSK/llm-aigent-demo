// lib/utils.js
export function cn(...args) {
  const out = [];

  const push = (v) => {
    if (!v) return;
    if (typeof v === 'string') return out.push(v);
    if (Array.isArray(v)) return v.forEach(push);
    if (typeof v === 'object') {
      for (const [k, val] of Object.entries(v)) {
        if (val) out.push(k);
      }
    }
  };

  args.forEach(push);
  return out.join(' ');
}
