export function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function formatPrintTimestamp(date = new Date()) {
  try {
    return new Intl.DateTimeFormat(undefined, {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  } catch {
    return date.toISOString();
  }
}

export function renderPrintTable(headers = [], rows = []) {
  const headHtml = headers
    .map((header) => `<th>${escapeHtml(header)}</th>`)
    .join('');
  const bodyHtml = rows.length
    ? rows
      .map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join('')}</tr>`)
      .join('')
    : `<tr><td colspan="${Math.max(headers.length, 1)}">No data available.</td></tr>`;

  return `
    <table>
      <thead><tr>${headHtml}</tr></thead>
      <tbody>${bodyHtml}</tbody>
    </table>
  `;
}

export function openPrintPdfWindow({ title, subtitle = '', sections = [] }) {
  if (typeof window === 'undefined') return false;
  // Avoid noopener/noreferrer here because some browsers open the popup but block document access,
  // which results in a blank window for print-to-PDF flows.
  const popup = window.open('', '_blank', 'width=1000,height=900');
  if (!popup) return false;

  const safeTitle = escapeHtml(title || 'Document');
  const safeSubtitle = escapeHtml(subtitle || '');
  const sectionsHtml = sections.join('');
  const generatedAt = escapeHtml(formatPrintTimestamp());

  try {
    popup.document.open();
    popup.document.write(`<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>${safeTitle}</title>
    <style>
      :root {
        --ink: #14284a;
        --muted: #5b6778;
        --line: #dbe3ee;
        --soft: #f6f9fc;
      }
      * { box-sizing: border-box; }
      html, body { margin: 0; padding: 0; font-family: Helvetica, Arial, sans-serif; color: var(--ink); }
      body { padding: 24px; background: #fff; }
      h1 { margin: 0 0 6px; font-size: 24px; }
      h2 { margin: 0 0 10px; font-size: 16px; }
      h3 { margin: 10px 0 6px; font-size: 14px; }
      p, li { line-height: 1.35; }
      .meta { color: var(--muted); font-size: 12px; margin-bottom: 16px; }
      .section {
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 14px;
        page-break-inside: avoid;
      }
      .chips { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0 0; }
      .chip {
        border: 1px solid var(--line);
        background: var(--soft);
        border-radius: 999px;
        padding: 4px 8px;
        font-size: 12px;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 8px;
        font-size: 12px;
      }
      th, td {
        border: 1px solid var(--line);
        padding: 6px 8px;
        text-align: left;
        vertical-align: top;
      }
      thead th { background: var(--soft); }
      ul, ol { margin: 6px 0 0; padding-left: 18px; }
      .muted { color: var(--muted); }
      .divider { height: 1px; background: var(--line); margin: 10px 0; }
      @media print {
        body { padding: 12mm; }
        .section { break-inside: avoid; }
      }
    </style>
  </head>
  <body>
    <header>
      <h1>${safeTitle}</h1>
      ${safeSubtitle ? `<div class="meta">${safeSubtitle}</div>` : ''}
      <div class="meta">Generated: ${generatedAt}</div>
    </header>
    ${sectionsHtml}
    <script>
      window.addEventListener('load', function () {
        setTimeout(function () {
          window.focus();
          window.print();
        }, 150);
      });
    </script>
  </body>
</html>`);
    popup.document.close();
  } catch (err) {
    console.error('[printPdf] Failed to write popup document:', err);
    try { popup.close(); } catch {}
    return false;
  }
  return true;
}
