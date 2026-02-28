export function getAdminSlugFromHostname() {
  if (typeof window === 'undefined') return '';
  const hostname = (window.location?.hostname || '').toLowerCase();
  if (!hostname) return '';

  const isIpv4 = /^\d{1,3}(\.\d{1,3}){3}$/.test(hostname);
  if (isIpv4) return '';
  if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === 'lvh.me') return '';

  if (hostname.endsWith('.lvh.me')) {
    const slug = hostname.slice(0, -'.lvh.me'.length);
    return slug && slug !== 'www' ? slug : '';
  }

  const parts = hostname.split('.').filter(Boolean);
  if (parts.length >= 3) {
    const sub = parts[0];
    if (sub && sub !== 'www') return sub;
  }

  return '';
}
