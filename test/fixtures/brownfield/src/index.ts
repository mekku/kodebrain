// Counter API — simple in-memory implementation
let counter = 0;

export function increment(): number {
  // Note: implementation is NOT atomic (spec says atomic)
  return ++counter;
}

export function get(): number {
  return counter;
}
