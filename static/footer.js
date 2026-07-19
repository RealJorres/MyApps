/**
 * Jorres Apps — Shared Site Footer
 * Served at /static/footer.js
 *
 * Replaces the 200-line copy-pasted <!-- SITE-FOOTER-START --> block
 * in every sub-app. One file to maintain instead of 129.
 *
 * Include just before </body> in every sub-app:
 *   <script src="/static/footer.js"></script>
 *
 * To update footer content, edit THIS file only.
 */
(function () {
  'use strict';

  // ── Global safety net: swallow benign clipboard-permission rejections ─────
  // Many app "Copy" buttons call navigator.clipboard.writeText() without a
  // .catch(). In a non-secure context, or when the browser/user denies the
  // clipboard permission, the returned promise rejects; left unhandled it
  // surfaces as a noisy console error / uncaught pageerror. Suppress ONLY that
  // specific rejection so genuine application errors still bubble up normally.
  window.addEventListener('unhandledrejection', function (e) {
    var r = e && e.reason;
    var name = r && r.name;
    var msg = (r && (r.message || String(r))) || '';
    if (name === 'NotAllowedError' || /clipboard|writeText|Write permission/i.test(msg)) {
      e.preventDefault();
    }
  });

  // ── Inject CSS ────────────────────────────────────────────────────────────
  var style = document.createElement('style');
  style.textContent = [
    '.site-footer{background:#0d1117;border-top:1px solid rgba(255,255,255,.08);padding:.75rem 1.5rem;display:flex;align-items:center;justify-content:center;gap:1.25rem;flex-wrap:wrap;font-size:.76rem;color:#64748b;margin-top:auto}',
    '.ft-btn{color:#64748b;background:none;border:none;cursor:pointer;font-size:.76rem;font-family:inherit;padding:0;transition:color .15s;text-decoration:none}',
    '.ft-btn:hover{color:#94a3b8}',
    '.ft-btn:focus-visible{outline:2px solid #2f57ff;outline-offset:2px;border-radius:2px}',
    '.ft-sep{color:#334155;user-select:none}',
    '.ft-modal-backdrop{display:none;position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:9999;align-items:center;justify-content:center;padding:1rem}',
    '.ft-modal-backdrop.open{display:flex}',
    '.ft-modal{background:#16202d;border:1px solid #2a475e;border-radius:12px;width:100%;max-width:520px;max-height:90vh;overflow:hidden;display:flex;flex-direction:column;box-shadow:0 24px 64px rgba(0,0,0,.5);animation:ft-pop .18s ease}',
    '@keyframes ft-pop{from{opacity:0;transform:scale(.95)}to{opacity:1;transform:scale(1)}}',
    '.ft-modal-head{display:flex;align-items:center;justify-content:space-between;padding:1rem 1.25rem;border-bottom:1px solid #2a475e;background:#1d3148;flex-shrink:0}',
    '.ft-modal-head h3{font-size:.95rem;font-weight:700;color:#fff}',
    '.ft-close{background:none;border:none;color:#94a3b8;font-size:1.2rem;cursor:pointer;line-height:1;padding:.25rem .45rem;border-radius:4px;transition:background .12s,color .12s}',
    '.ft-close:hover{color:#fff;background:rgba(255,255,255,.08)}',
    '.ft-close:focus-visible{outline:2px solid #2f57ff;outline-offset:2px}',
    '.ft-modal-body{padding:1.25rem;overflow-y:auto;color:#c6d4df;font-size:.82rem;line-height:1.65}',
    '.ft-modal-body h4{color:#e2e8f0;font-size:.83rem;font-weight:700;margin:.9rem 0 .3rem}',
    '.ft-modal-body h4:first-child{margin-top:0}',
    '.ft-modal-body p{margin-bottom:.5rem;color:#93a8b8}',
    '.ft-field{display:flex;flex-direction:column;gap:.3rem;margin-bottom:.85rem}',
    '.ft-field label{font-size:.75rem;font-weight:600;color:#93a8b8}',
    '.ft-field input,.ft-field textarea,.ft-field select{background:#0f172a;border:1px solid #2a475e;border-radius:6px;padding:.5rem .75rem;color:#e2e8f0;font-size:.85rem;font-family:inherit;width:100%;transition:border-color .15s;box-sizing:border-box}',
    '.ft-field input:focus,.ft-field textarea:focus,.ft-field select:focus{outline:none;border-color:#2f57ff}',
    '.ft-field textarea{resize:vertical;min-height:100px}',
    '.ft-field select option{background:#0f172a}',
    '.ft-submit{width:100%;padding:.65rem;background:#2f57ff;color:#fff;border:none;border-radius:7px;font-size:.88rem;font-weight:700;cursor:pointer;font-family:inherit;transition:background .15s}',
    '.ft-submit:hover{background:#1a2f8f}',
    '.ft-submit:focus-visible{outline:2px solid #2f57ff;outline-offset:2px}',
    '.ft-submit:disabled{background:#1e3a5f;color:#475569;cursor:not-allowed}',
    '#ft-bug-status{margin-top:.75rem;font-size:.8rem;text-align:center;min-height:1.4em}',
  ].join('');
  document.head.appendChild(style);

  // ── Build HTML ────────────────────────────────────────────────────────────
  var html = [
    '<footer class="site-footer" role="contentinfo">',
    '  <span>© 2026 Jorres Apps</span>',
    '  <span class="ft-sep" aria-hidden="true">·</span>',
    '  <button class="ft-btn" onclick="ftOpen(\'ft-privacy\')" aria-haspopup="dialog">Privacy</button>',
    '  <span class="ft-sep" aria-hidden="true">·</span>',
    '  <button class="ft-btn" onclick="ftOpen(\'ft-terms\')" aria-haspopup="dialog">Terms &amp; Conditions</button>',
    '  <span class="ft-sep" aria-hidden="true">·</span>',
    '  <button class="ft-btn" onclick="ftOpen(\'ft-bug\')" aria-haspopup="dialog">Report a Bug</button>',
    '</footer>',

    // Privacy Policy Modal
    '<div class="ft-modal-backdrop" id="ft-privacy" role="dialog" aria-modal="true" aria-label="Privacy Policy" onclick="ftOutside(event,\'ft-privacy\')">',
    '  <div class="ft-modal">',
    '    <div class="ft-modal-head">',
    '      <h3>Privacy Policy</h3>',
    '      <button class="ft-close" onclick="ftClose(\'ft-privacy\')" aria-label="Close">&#x2715;</button>',
    '    </div>',
    '    <div class="ft-modal-body">',
    '      <p style="color:#4ade80;font-weight:600">The short version: Jorres Apps collects nothing about you. No data leaves your browser. No accounts. No tracking. Free forever.</p>',
    '      <h4>What we collect</h4>',
    '      <p><strong>Nothing.</strong> No personal information is collected, stored, or transmitted. There are no analytics scripts, tracking pixels, or third-party data collectors on our pages.</p>',
    '      <h4>Cookies</h4>',
    '      <p>We do not use cookies of any kind &mdash; not for sessions, not for preferences, not for advertising.</p>',
    '      <h4>Local storage</h4>',
    '      <p>Some tools save data to your browser&rsquo;s localStorage so your work persists between visits (e.g. Notepad, Kanban Board, Journal). This data stays entirely on your device, is never transmitted to our server or any third party, and can be cleared at any time via your browser settings.</p>',
    '      <h4>Server logs</h4>',
    '      <p>Our hosting provider (Render.com) may retain standard HTTP access logs (IP address, timestamp, requested URL) for security and operational purposes. These are not used by us for analytics or marketing.</p>',
    '      <h4>Bug reports</h4>',
    '      <p>When you voluntarily submit a bug report, we receive the text you enter (app name, description, and optional email). This is used solely to fix reported issues and is never shared or sold.</p>',
    '      <h4>Third-party API tools</h4>',
    '      <p>A few tools (e.g. DNS Lookup, IP Info, Whois Lookup) query public APIs on your behalf. These requests originate from our server and contain no identifying information beyond the query itself.</p>',
    '      <h4>Children</h4>',
    '      <p>Jorres Apps is not directed at children under 13. We do not knowingly collect data from children.</p>',
    '      <h4>Contact</h4>',
    '      <p>Questions? Email <a href="mailto:joshuarelatorres28@gmail.com" style="color:#2f57ff">joshuarelatorres28@gmail.com</a> or use the Bug Report form.</p>',
    '    </div>',
    '  </div>',
    '</div>',

    // Terms & Conditions Modal
    '<div class="ft-modal-backdrop" id="ft-terms" role="dialog" aria-modal="true" aria-label="Terms and Conditions" onclick="ftOutside(event,\'ft-terms\')">',
    '  <div class="ft-modal">',
    '    <div class="ft-modal-head">',
    '      <h3>Terms &amp; Conditions</h3>',
    '      <button class="ft-close" onclick="ftClose(\'ft-terms\')" aria-label="Close">&#x2715;</button>',
    '    </div>',
    '    <div class="ft-modal-body">',
    '      <h4>1. Acceptance</h4>',
    '      <p>By accessing or using Jorres Apps you agree to these terms. If you do not agree, please discontinue use.</p>',
    '      <h4>2. Free Service &mdash; No Warranty</h4>',
    '      <p>All tools are provided free of charge and &ldquo;as is&rdquo;, without any warranty of accuracy, completeness, fitness for a particular purpose, or uninterrupted availability.</p>',
    '      <h4>3. Data &amp; Privacy</h4>',
    '      <p>We do not collect, store, or sell any personal data. Some apps save data to your browser&rsquo;s localStorage &mdash; this data stays on your device only and can be cleared at any time through your browser settings. No cookies, no tracking.</p>',
    '      <h4>4. No Account Required</h4>',
    '      <p>No sign-up, login, or personal information is required to use any tool on this site.</p>',
    '      <h4>5. Acceptable Use</h4>',
    '      <p>You agree not to use these tools for any unlawful or harmful purpose. Automated scraping or abuse of the service is prohibited.</p>',
    '      <h4>6. Third-Party Services</h4>',
    '      <p>Certain tools (e.g. DNS Lookup, IP Info, Currency Converter) may query third-party APIs. Their respective terms and privacy policies apply to those requests.</p>',
    '      <h4>7. Changes</h4>',
    '      <p>We reserve the right to update, modify, add, or remove any tool at any time and to revise these terms without prior notice.</p>',
    '      <h4>8. Limitation of Liability</h4>',
    '      <p>Jorres Apps and its creator shall not be liable for any direct, indirect, incidental, or consequential damages arising from your use of, or inability to use, the site.</p>',
    '      <h4>9. Contact</h4>',
    '      <p>For questions, concerns, or bug reports, use the Bug Report form or email <a href="mailto:joshuarelatorres28@gmail.com" style="color:#2f57ff">joshuarelatorres28@gmail.com</a>.</p>',
    '    </div>',
    '  </div>',
    '</div>',

    // Bug Report Modal
    '<div class="ft-modal-backdrop" id="ft-bug" role="dialog" aria-modal="true" aria-label="Report a Bug" onclick="ftOutside(event,\'ft-bug\')">',
    '  <div class="ft-modal">',
    '    <div class="ft-modal-head">',
    '      <h3>Report a Bug</h3>',
    '      <button class="ft-close" onclick="ftClose(\'ft-bug\')" aria-label="Close">&#x2715;</button>',
    '    </div>',
    '    <div class="ft-modal-body">',
    '      <div class="ft-field">',
    '        <label for="ft-bug-app">App / Page</label>',
    '        <input id="ft-bug-app" placeholder="e.g. Chess, Password Tools, main page…" autocomplete="off">',
    '      </div>',
    '      <div class="ft-field">',
    '        <label for="ft-bug-type">Issue Type</label>',
    '        <select id="ft-bug-type">',
    '          <option value="Bug">Bug / Error</option>',
    '          <option value="UI">UI / Layout issue</option>',
    '          <option value="Feature">Feature suggestion</option>',
    '          <option value="Other">Other</option>',
    '        </select>',
    '      </div>',
    '      <div class="ft-field">',
    '        <label for="ft-bug-desc">Description <span style="color:#ef4444" aria-hidden="true">*</span><span class="sr-only">(required)</span></label>',
    '        <textarea id="ft-bug-desc" placeholder="What happened? What did you expect? Steps to reproduce?" aria-required="true"></textarea>',
    '      </div>',
    '      <div class="ft-field">',
    '        <label for="ft-bug-email">Your email <span style="font-weight:400;color:#475569">(optional &mdash; for follow-up)</span></label>',
    '        <input id="ft-bug-email" type="email" placeholder="you@example.com" autocomplete="email">',
    '      </div>',
    '      <button class="ft-submit" id="ft-bug-btn" onclick="ftSubmitBug()">Send Report</button>',
    '      <div id="ft-bug-status" role="alert" aria-live="polite"></div>',
    '    </div>',
    '  </div>',
    '</div>',
  ].join('\n');

  // Insert footer HTML before </body> (or append to body)
  var container = document.createElement('div');
  container.innerHTML = html;
  while (container.firstChild) {
    document.body.appendChild(container.firstChild);
  }

  // ── JS logic ──────────────────────────────────────────────────────────────
  function ftOpen(id) {
    var el = document.getElementById(id);
    if (el) { el.classList.add('open'); }
    // Focus first focusable element in modal
    setTimeout(function () {
      var first = el && el.querySelector('button, input, select, textarea, a[href]');
      if (first) first.focus();
    }, 50);
  }

  function ftClose(id) {
    var el = document.getElementById(id);
    if (el) { el.classList.remove('open'); }
    var s = document.getElementById('ft-bug-status');
    if (s) s.textContent = '';
  }

  function ftOutside(e, id) {
    if (e.target === document.getElementById(id)) ftClose(id);
  }

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      document.querySelectorAll('.ft-modal-backdrop.open').forEach(function (m) {
        m.classList.remove('open');
      });
    }
  });

  window.ftOpen   = ftOpen;
  window.ftClose  = ftClose;
  window.ftOutside = ftOutside;

  window.ftSubmitBug = async function () {
    var desc = (document.getElementById('ft-bug-desc').value || '').trim();
    if (!desc) {
      document.getElementById('ft-bug-status').innerHTML =
        '<span style="color:#f87171">Please describe the issue first.</span>';
      return;
    }
    var btn    = document.getElementById('ft-bug-btn');
    var status = document.getElementById('ft-bug-status');
    btn.disabled = true; btn.textContent = 'Sending…'; status.textContent = '';
    try {
      var resp = await fetch('/api/bug-report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          app:   (document.getElementById('ft-bug-app').value || '').trim() || window.location.pathname,
          type:  (document.getElementById('ft-bug-type').value || 'Bug'),
          desc:  desc,
          email: (document.getElementById('ft-bug-email').value || '').trim(),
          page:  window.location.href,
        }),
      });
      var data = {};
      try { data = await resp.json(); } catch (_) { /* ignore */ }
      if (resp.ok && data.ok) {
        status.innerHTML = '<span style="color:#4ade80">Report sent — thank you!</span>';
        ['ft-bug-app', 'ft-bug-desc', 'ft-bug-email'].forEach(function (id) {
          var el = document.getElementById(id); if (el) el.value = '';
        });
        var sel = document.getElementById('ft-bug-type');
        if (sel) sel.selectedIndex = 0;
        setTimeout(function () { ftClose('ft-bug'); }, 2200);
      } else {
        status.innerHTML = '<span style="color:#f87171">' +
          (data.error || 'Server error (HTTP ' + resp.status + '). Please try again.') + '</span>';
      }
    } catch (e) {
      status.innerHTML = '<span style="color:#f87171">Could not reach the server — check your connection and try again.</span>';
    }
    btn.disabled = false; btn.textContent = 'Send Report';
  };
})();
