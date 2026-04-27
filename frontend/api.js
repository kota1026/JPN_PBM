async function api(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
  const res = await fetch(path, { ...opts, headers });
  const text = await res.text();
  let body;
  try { body = text ? JSON.parse(text) : null; } catch { body = text; }
  if (!res.ok) {
    const msg = (body && body.detail) ? body.detail : (text || res.statusText);
    throw new Error(`${res.status} ${msg}`);
  }
  return body;
}

function el(tag, attrs = {}, ...children) {
  const e = document.createElement(tag);
  for (const k in attrs) {
    if (k === 'class') e.className = attrs[k];
    else if (k.startsWith('on') && typeof attrs[k] === 'function') e.addEventListener(k.slice(2), attrs[k]);
    else e.setAttribute(k, attrs[k]);
  }
  for (const c of children) {
    if (c == null) continue;
    e.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
  }
  return e;
}

function fmtJpy(n) {
  if (n == null || n === '-') return '-';
  return '¥' + Number(n).toLocaleString();
}

const NAV = `
<nav>
  <a href="/ui/index.html">トップ</a>
  <a href="/ui/tokyo.html">東京都</a>
  <a href="/ui/citizen.html">住民</a>
  <a href="/ui/retailer.html">加盟店</a>
  <a href="/ui/ebpm.html">EBPM</a>
</nav>`;
document.addEventListener('DOMContentLoaded', () => {
  const nav = document.getElementById('nav');
  if (nav) nav.outerHTML = NAV;
});
