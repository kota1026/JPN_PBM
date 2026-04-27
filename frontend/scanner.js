/* ============================================================
   バーコード/QR スキャナ + QR ジェネレータ
   - 1D (EAN-13/JAN/Code128) と 2D (QR) を統一インターフェースで
   - 環境別に: BarcodeDetector ネイティブ → ZXing CDN フォールバック
   - QR 描画: qrcode-generator CDN
   ============================================================ */

const ZXING_CDN     = 'https://cdn.jsdelivr.net/npm/@zxing/browser@0.1.5/umd/index.min.js';
const QRCODE_CDN    = 'https://cdn.jsdelivr.net/npm/qrcode-generator@1.4.4/qrcode.min.js';

const _loaded = {};
function loadScript(src) {
  if (_loaded[src]) return _loaded[src];
  return _loaded[src] = new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = src;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error('script load failed: ' + src));
    document.head.appendChild(s);
  });
}

/* ===== カメラ + 検出器 ===== */

const NATIVE_SUPPORTED_FORMATS = ['ean_13', 'ean_8', 'code_128', 'qr_code'];

async function getNativeDetector() {
  if (!('BarcodeDetector' in window)) return null;
  try {
    const supported = await window.BarcodeDetector.getSupportedFormats();
    const ok = NATIVE_SUPPORTED_FORMATS.filter(f => supported.includes(f));
    if (!ok.length) return null;
    return new window.BarcodeDetector({ formats: ok });
  } catch { return null; }
}

async function getZxingReader() {
  await loadScript(ZXING_CDN);
  const Z = window.ZXingBrowser;
  if (!Z) throw new Error('ZXing failed to load');
  return new Z.BrowserMultiFormatReader();
}

/**
 * Open camera and scan for the first valid barcode.
 *
 * @param {HTMLVideoElement} videoEl
 * @param {(text: string, format: string) => boolean|void} onResult
 *        return true to keep scanning, falsy to stop.
 * @returns {Promise<{stop: ()=>void}>}
 */
export async function startScanner(videoEl, onResult) {
  const constraints = { video: { facingMode: 'environment' }, audio: false };
  const stream = await navigator.mediaDevices.getUserMedia(constraints);
  videoEl.srcObject = stream;
  videoEl.setAttribute('playsinline', 'true');
  await videoEl.play();

  let stopped = false;
  const stop = () => {
    if (stopped) return;
    stopped = true;
    try { stream.getTracks().forEach(t => t.stop()); } catch {}
    try { videoEl.srcObject = null; } catch {}
  };

  const native = await getNativeDetector();

  if (native) {
    const tick = async () => {
      if (stopped) return;
      try {
        const codes = await native.detect(videoEl);
        for (const c of codes) {
          const cont = onResult(c.rawValue, c.format);
          if (!cont) { stop(); return; }
        }
      } catch {/* ignore frame */ }
      requestAnimationFrame(tick);
    };
    tick();
  } else {
    const reader = await getZxingReader();
    reader.decodeFromVideoElementContinuously(videoEl, (result, err, ctrl) => {
      if (stopped) { try { ctrl.stop(); } catch {} ; return; }
      if (result) {
        const cont = onResult(result.getText(), result.getBarcodeFormat ? String(result.getBarcodeFormat()).toLowerCase() : 'unknown');
        if (!cont) { try { ctrl.stop(); } catch {} ; stop(); }
      }
    });
  }

  return { stop };
}

/* ===== QR 描画 ===== */
export async function drawQR(targetEl, text, opts = {}) {
  await loadScript(QRCODE_CDN);
  const QR = window.qrcode;
  if (!QR) throw new Error('qrcode-generator failed to load');
  const qr = QR(0, opts.errorLevel || 'M');
  qr.addData(text);
  qr.make();
  // svg をはめ込む (rasterize した png より綺麗)
  const cellSize = opts.cellSize || 4;
  const margin = opts.margin || 2;
  targetEl.innerHTML = qr.createSvgTag({ cellSize, margin, scalable: true });
  const svg = targetEl.querySelector('svg');
  if (svg) {
    svg.style.width = (opts.width || 200) + 'px';
    svg.style.height = (opts.width || 200) + 'px';
    svg.style.display = 'block';
  }
}

/* ===== モーダル付きスキャナ呼び出し =====
   呼ぶ側はこれ 1 行で OK:
   const code = await scanOnce({ title: 'バーコードをかざす', formatHint: 'JAN/EAN-13' });
*/
export function scanOnce(opts = {}) {
  return new Promise((resolve, reject) => {
    const overlay = document.createElement('div');
    overlay.className = 'scanner-overlay';
    overlay.innerHTML = `
      <div class="scanner-modal">
        <div class="scanner-head">
          <strong>${opts.title || 'バーコードをスキャン'}</strong>
          <button type="button" class="ghost scanner-close">閉じる</button>
        </div>
        <video class="scanner-video" muted playsinline></video>
        <div class="scanner-hint">
          ${opts.formatHint || 'JAN / EAN-13 / QR コードを画面中央にかざしてください'}
        </div>
        <div class="scanner-status">準備中…</div>
      </div>`;
    document.body.appendChild(overlay);
    const video = overlay.querySelector('video');
    const status = overlay.querySelector('.scanner-status');
    let handle = null;
    const cleanup = () => {
      if (handle) { try { handle.stop(); } catch {} }
      overlay.remove();
    };
    overlay.querySelector('.scanner-close').addEventListener('click', () => {
      cleanup();
      reject(new Error('cancelled'));
    });
    overlay.addEventListener('click', (ev) => {
      if (ev.target === overlay) { cleanup(); reject(new Error('cancelled')); }
    });
    startScanner(video, (text, format) => {
      if (opts.filter && !opts.filter(text, format)) {
        status.textContent = '対象外コード: ' + text;
        return true; // keep scanning
      }
      status.textContent = '読取り: ' + text;
      cleanup();
      resolve({ text, format });
      return false;
    }).then(h => { handle = h; status.textContent = 'カメラ起動中… コードを読み取ります'; })
      .catch(err => {
        status.textContent = 'カメラ起動失敗: ' + err.message;
        const manual = document.createElement('div');
        manual.className = 'scanner-manual';
        manual.innerHTML = `
          <p class="note">カメラが利用できません。手入力してください:</p>
          <input class="scanner-manual-input" placeholder="JAN / コードを入力">
          <button class="scanner-manual-go">送信</button>`;
        overlay.querySelector('.scanner-modal').appendChild(manual);
        manual.querySelector('.scanner-manual-go').addEventListener('click', () => {
          const v = manual.querySelector('input').value.trim();
          if (!v) return;
          cleanup();
          resolve({ text: v, format: 'manual' });
        });
      });
  });
}
