/* ============================================================
   共通 JS — API クライアント、要素ヘルパ、共通レイアウト挿入
   ============================================================ */

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
    else if (k === 'html') e.innerHTML = attrs[k];
    else if (k.startsWith('on') && typeof attrs[k] === 'function') e.addEventListener(k.slice(2), attrs[k]);
    else if (attrs[k] !== false && attrs[k] != null) e.setAttribute(k, attrs[k]);
  }
  for (const c of children) {
    if (c == null || c === false) continue;
    e.appendChild(typeof c === 'string' || typeof c === 'number' ? document.createTextNode(String(c)) : c);
  }
  return e;
}

function fmtJpy(n) {
  if (n == null || n === '-' || isNaN(n)) return '-';
  return '¥' + Number(n).toLocaleString();
}
function fmtPct(n, digits = 1) {
  if (n == null || isNaN(n)) return '-';
  return (n * 100).toFixed(digits) + '%';
}

/* ============================================================
   カテゴリ辞書 — 大分類 (parent) と日本語ラベル
   サーバーは "appliance.air_conditioner" のような ID を返すが、
   UI では「家電 / エアコン」のように人間にやさしい表記にする。
   ============================================================ */
const CATEGORY_PARENTS = {
  appliance: { label: '家電',     icon: '🔌', color: '#0E419A' },
  food:      { label: '食品',     icon: '🍙', color: '#E60012' },
  goods:     { label: '日用品',   icon: '🧴', color: '#8a5a00' },
  med:       { label: '医薬品',   icon: '💊', color: '#a8000c' },
  disaster:  { label: '防災',     icon: '🛟', color: '#c45a00' },
  care:      { label: '介護',     icon: '🧓', color: '#5a3aa8' },
  school:    { label: '学用品',   icon: '🎒', color: '#0a3175' },
};

const CATEGORY_LABELS = {
  'appliance.air_conditioner': 'エアコン',
  'appliance.refrigerator':    '冷蔵庫',
  'appliance.light':           '照明',
  'appliance.washer':          '洗濯機',
  'appliance.kitchen':         'キッチン家電',
  'food.baby':                 '乳幼児食品',
  'food.daily':                '日常食品',
  'goods.baby':                '育児用品',
  'med.rx':                    '処方薬',
  'med.otc':                   '市販薬',
  'med.supplement':            'サプリ・栄養食品',
  'disaster.water':            '保存水',
  'disaster.food':             '非常食',
  'disaster.gear':             '防災用品',
  'care.adult':                '介護消耗品',
  'care.equipment':            '介護用品',
  'school.stationery':         '文房具',
  'school.bag':                'ランドセル',
};

function catParent(id) {
  return (id || '').split('.')[0];
}
function catParentMeta(id) {
  return CATEGORY_PARENTS[catParent(id)] || { label: catParent(id) || 'その他', icon: '📦', color: '#5c6470' };
}
function catLabel(id) {
  return CATEGORY_LABELS[id] || (id || '').split('.').slice(1).join('.') || id;
}
/** "家電 / エアコン" のように親+子で表示 */
function catFullLabel(id) {
  const p = catParentMeta(id).label;
  const c = catLabel(id);
  return p === c ? p : `${p} / ${c}`;
}
/** 検索文字列に対する商品マッチ判定 (商品名 + JAN + 親/子ラベル + ID) */
function productMatches(p, q) {
  if (!q) return true;
  const hay = [
    p.name, p.jan, p.category,
    catLabel(p.category), catParentMeta(p.category).label, catFullLabel(p.category),
  ].join(' ').toLowerCase();
  return q.toLowerCase().split(/\s+/).filter(Boolean).every(t => hay.includes(t));
}

/* ===== 銀杏マーク (東京都シンボル風) を SVG で ===== */
const GINGKO_SVG = `
<svg class="gingko" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <defs>
    <linearGradient id="gk" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#00b048"/>
      <stop offset="100%" stop-color="#007a30"/>
    </linearGradient>
  </defs>
  <circle cx="32" cy="32" r="30" fill="#fff" stroke="#00A040" stroke-width="2"/>
  <path d="M32 14
           C 22 18, 16 28, 18 38
           C 19 44, 24 48, 32 48
           C 40 48, 45 44, 46 38
           C 48 28, 42 18, 32 14 Z"
        fill="url(#gk)"/>
  <path d="M32 30 L32 52" stroke="#007a30" stroke-width="2" stroke-linecap="round"/>
  <path d="M24 22 L20 18 M40 22 L44 18 M22 32 L16 32 M42 32 L48 32"
        stroke="#fff" stroke-width="1.5" opacity="0.5" stroke-linecap="round"/>
</svg>`;

/* ===== ページ別タイトル ===== */
const PAGE_META = {
  '/ui/index.html':    { title: 'JPN PBM',          sub: '東京都ステーブルコイン助成金 統合プラットフォーム', key: 'home' },
  '/ui/tokyo.html':    { title: '東京都管理',         sub: '助成金プログラムの設計・予算ロック・取消',           key: 'tokyo' },
  '/ui/citizen.html':  { title: '住民マイページ',      sub: 'マイナンバー認証 / PBM 申請 / ウォレット',         key: 'citizen' },
  '/ui/retailer.html': { title: '加盟店レジ',         sub: 'JAN コードスキャンで PBM 自動適用',                  key: 'retailer' },
  '/ui/ebpm.html':     { title: 'EBPM ダッシュボード', sub: '匿名集計による政策効果の可視化',                     key: 'ebpm' },
};

function renderChrome() {
  const path = location.pathname.replace(/\/$/, '/index.html');
  const meta = PAGE_META[path] || PAGE_META['/ui/index.html'];

  const header = el('div', { class: 'tmg-bar' });
  const logoWrap = el('div', { class: 'logo' });
  logoWrap.innerHTML = GINGKO_SVG;
  header.appendChild(logoWrap);
  header.appendChild(el('div', { class: 'brand' },
    el('span', { class: 'org' }, 'TOKYO METROPOLITAN GOVERNMENT — DEMO'),
    el('span', { class: 'name' }, '東京都ステーブルコイン助成金 ', el('em', {}, 'PBM'))
  ));
  header.appendChild(el('div', { class: 'spacer' }));
  header.appendChild(el('div', { class: 'meta' }, 'JPYC × マイナンバー × JAN'));

  const accent = el('div', { class: 'tmg-accent' });

  const navItems = [
    ['home',     '/ui/index.html',    'トップ'],
    ['tokyo',    '/ui/tokyo.html',    '東京都管理'],
    ['citizen',  '/ui/citizen.html',  '住民マイページ'],
    ['retailer', '/ui/retailer.html', '加盟店レジ'],
    ['ebpm',     '/ui/ebpm.html',     'EBPM Dashboard'],
    ['docs',     '/docs',             'API Docs'],
  ];
  const nav = el('nav', { class: 'nav' });
  for (const [k, href, label] of navItems) {
    nav.appendChild(el('a', { href, class: k === meta.key ? 'active' : '' }, label));
  }

  const hero = el('div', { class: 'hero' },
    el('h1', {}, meta.title, meta.key === 'home' ? null : el('span', { class: 'pill' }, 'MVP デモ')),
    el('p', {}, meta.sub)
  );

  const slot = document.getElementById('chrome');
  if (slot) {
    slot.appendChild(header);
    slot.appendChild(accent);
    slot.appendChild(nav);
    slot.appendChild(hero);
  } else {
    document.body.prepend(hero);
    document.body.prepend(nav);
    document.body.prepend(accent);
    document.body.prepend(header);
  }
  document.title = meta.title + ' — JPN PBM';
}

document.addEventListener('DOMContentLoaded', renderChrome);
