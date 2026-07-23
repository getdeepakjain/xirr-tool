export function money(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);
}

export function pct(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return `${n.toFixed(2)}%`;
}

export function num(n: number | null | undefined, digits = 2): string {
  if (n === null || n === undefined) return "—";
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits: digits }).format(n);
}

export function signClass(n: number | null | undefined): string {
  if (n === null || n === undefined) return "";
  return n > 0 ? "pos" : n < 0 ? "neg" : "";
}
