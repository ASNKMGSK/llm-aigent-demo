export function cn(...classes) {
  return classes.flat().filter(Boolean).join(' ');
}
