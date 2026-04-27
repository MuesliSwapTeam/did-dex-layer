export function formatNumber(value: number | null | undefined, maximumFractionDigits = 6) {
  if (value === null || value === undefined || Number.isNaN(value)) return '-';
  return new Intl.NumberFormat('en-US', { maximumFractionDigits }).format(value);
}

export function formatPrice(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return '-';
  if (value === 0) return '0';

  const absolute = Math.abs(value);
  if (absolute < 0.000000000001) {
    return `${value < 0 ? '-' : ''}<0.000000000001`;
  }

  const maximumFractionDigits =
    absolute >= 1 ? 4 : absolute >= 0.01 ? 6 : absolute >= 0.0001 ? 8 : 12;

  return new Intl.NumberFormat('en-US', { maximumFractionDigits }).format(value);
}
