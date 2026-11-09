"""Demo pages for the Phase 8 interface."""

from __future__ import annotations

from fastapi.responses import HTMLResponse


def chat_page() -> HTMLResponse:
    return HTMLResponse(
        """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
    <title>Atelier support</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&display=swap" rel="stylesheet" />
    <style>
      :root {
        --bg: #dce4e9;
        --workspace-bg: rgba(220,229,235,0.72);
        --panel-bg: rgba(239,243,246,0.78);
        --composer-bg: rgba(216,226,233,0.54);
        --composer-surface: rgba(244,247,249,0.48);
        --user-bubble: rgba(105,137,155,0.16);
        --ink: #1b2b35;
        --muted: #5b6d78;
        --line: rgba(43, 69, 84, 0.18);
        --line-soft: rgba(43,69,84,0.12);
        --steel: #55778b;
        --steel-strong: #52778d;
        --user-meta: #506b7b;
        --thumb: rgba(92,126,145,0.72);
        --thumb-hover: rgba(64,103,124,0.9);
        --focus: rgba(67,112,137,0.75);
        --button-shadow: 0 7px 16px rgba(43,69,84,0.2);
      }

      body[data-theme="dark"] {
        --bg: #1a252c;
        --workspace-bg: #202c33;
        --panel-bg: #26343c;
        --composer-bg: #202d35;
        --composer-surface: #2b3a43;
        --user-bubble: #354b58;
        --ink: #e7edf1;
        --muted: #aab9c2;
        --line: rgba(190,207,216,0.18);
        --line-soft: rgba(190,207,216,0.13);
        --steel: #86a3b3;
        --steel-strong: #68899b;
        --user-meta: #c2d2db;
        --thumb: rgba(132,163,180,0.76);
        --thumb-hover: rgba(161,187,201,0.95);
        --focus: rgba(145,183,204,0.86);
        --button-shadow: 0 7px 16px rgba(0,0,0,0.28);
      }

      * { box-sizing: border-box; }
      html, body { height: 100%; overflow: hidden; }
      body {
        margin: 0;
        height: 100vh;
        height: 100dvh;
        min-height: 0;
        background: var(--bg);
        color: var(--ink);
        font: 16px/1.55 "DM Sans", "Segoe UI", sans-serif;
      }
      button, textarea { font: inherit; }

      .page {
        height: 100vh;
        height: 100dvh;
        min-height: 0;
        display: grid;
        place-items: center;
        padding: 68px 26px 26px;
        overflow: hidden;
      }

      .workspace {
        width: min(920px, 100%);
        height: min(900px, calc(100dvh - 94px));
        min-height: 0;
        display: grid;
        grid-template-columns: minmax(0, 1fr);
        background: var(--workspace-bg);
        backdrop-filter: blur(18px);
        overflow: hidden;
      }

      .chat-panel {
        display: flex;
        flex-direction: column;
        min-height: 0;
        overflow: hidden;
        background: var(--panel-bg);
      }

      .panel-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        padding: 20px 26px 18px;
        border-bottom: 1px solid var(--line);
      }

      .brand {
        display: inline-flex;
        align-items: center;
        gap: 12px;
        font-family: "Newsreader", Georgia, serif;
        font-size: 1.22rem;
        font-weight: 500;
      }

      .brand-mark {
        width: 42px;
        height: 42px;
        border-radius: 50%;
        display: grid;
        place-items: center;
        background: var(--steel);
        color: #f5f8fa;
        font-size: 0.9rem;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.42);
      }

      .header-actions {
        display: flex;
        align-items: center;
        gap: 10px;
      }

      .mini-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 4px 0;
        background: transparent;
        border: 0;
        color: var(--muted);
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }

      .mini-pill::before {
        content: "";
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #5c8a77;
        box-shadow: 0 0 0 4px rgba(92,138,119,0.13);
      }

      .theme-toggle {
        position: fixed;
        top: max(12px, env(safe-area-inset-top));
        right: max(20px, env(safe-area-inset-right));
        z-index: 20;
        width: 40px;
        height: 40px;
        display: grid;
        place-items: center;
        border: 1px solid var(--line);
        border-radius: 50%;
        background: transparent;
        color: var(--ink);
        cursor: pointer;
        transition: background-color 160ms ease, color 160ms ease, border-color 160ms ease;
      }

      .theme-toggle:hover { background: var(--user-bubble); }
      .theme-toggle svg { width: 19px; height: 19px; fill: none; stroke: currentColor; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; }
      .theme-icon-sun { display: none; }
      body[data-theme="dark"] .theme-icon-moon { display: none; }
      body[data-theme="dark"] .theme-icon-sun { display: block; }

      .ghost-button {
        border: 1px solid var(--line);
        background: rgba(255,255,255,0.4);
        color: var(--ink);
        border-radius: 999px;
        padding: 9px 14px;
        cursor: pointer;
      }

      .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
      }

      .meta-strip {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0;
        margin: 0 26px;
        padding: 16px 0;
        border-bottom: 1px solid var(--line-soft);
      }

      .meta-card {
        padding: 4px 16px;
        background: transparent;
      }

      .meta-card + .meta-card {
        border-left: 1px solid var(--line-soft);
      }

      .meta-label {
        display: block;
        font-size: 0.72rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 6px;
      }

      .meta-value {
        font-weight: 700;
        letter-spacing: -0.02em;
      }

      .thread-frame {
        flex: 1;
        min-height: 0;
        position: relative;
        overflow: hidden;
      }

      .thread {
        width: 100%;
        height: 100%;
        min-height: 0;
        overflow-y: auto;
        overscroll-behavior: contain;
        scrollbar-width: none;
        padding: 22px 42px 18px 26px;
      }

      .thread::-webkit-scrollbar { display: none; width: 0; height: 0; }

      .custom-scrollbar {
        position: absolute;
        inset: 14px 8px 14px auto;
        width: 14px;
        opacity: 0;
        touch-action: none;
        transition: opacity 180ms ease;
      }

      .custom-scrollbar.visible,
      .custom-scrollbar:hover,
      .custom-scrollbar:focus-visible,
      .custom-scrollbar.dragging { opacity: 1; }

      .custom-scrollbar[hidden] { display: none; }

      .custom-scrollbar-thumb {
        position: absolute;
        top: 0;
        right: 4px;
        width: 6px;
        min-height: 32px;
        border-radius: 999px;
        background: var(--thumb);
        box-shadow: inset 0 0 0 1px rgba(255,255,255,0.26);
        cursor: grab;
        transition: width 150ms ease, right 150ms ease, background 150ms ease;
      }

      .custom-scrollbar:hover .custom-scrollbar-thumb,
      .custom-scrollbar:focus-visible .custom-scrollbar-thumb {
        right: 3px;
        width: 8px;
        background: var(--thumb-hover);
      }

      .custom-scrollbar.dragging .custom-scrollbar-thumb { cursor: grabbing; }
      .custom-scrollbar:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }

      @media (max-width: 600px) {
        .thread { padding: 18px 34px 18px 18px; }
      }

      .thread::before {
        content: none;
      }

      .turn {
        position: relative;
        display: grid;
        grid-template-columns: minmax(0, 1fr);
        gap: 16px;
        margin: 16px 0;
        align-items: start;
      }

      .turn.customer {
        grid-template-columns: minmax(0, 1fr);
        justify-items: end;
      }

      .bubble {
        max-width: min(82%, 460px);
        padding: 12px 0;
        background: transparent;
        border: 0;
        box-shadow: none;
      }

      .turn.customer .bubble {
        padding: 12px 18px;
        background: var(--user-bubble);
        color: var(--ink);
      }

      .bubble-meta {
        font-size: 0.7rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 6px;
      }

      .turn.customer .bubble-meta {
        color: var(--user-meta);
      }

      .bubble p {
        margin: 0;
        font-family: "Newsreader", Georgia, serif;
        font-size: 1.2rem;
        line-height: 1.65;
      }

      .empty-state {
        min-height: 260px;
        display: grid;
        align-content: center;
        justify-items: center;
        gap: 8px;
        color: var(--muted);
        text-align: center;
      }

      .empty-state[hidden] { display: none; }

      .empty-state strong {
        color: var(--ink);
        font-family: "Newsreader", Georgia, serif;
        font-size: 1.65rem;
        font-weight: 400;
      }

      .empty-state span { font-size: 0.9rem; }
      .turn.pending .bubble { color: var(--muted); font-style: italic; }
      .send-button:disabled { opacity: 0.55; cursor: wait; }
      .send-button:hover:not(:disabled) { transform: translateY(-1px); filter: brightness(1.08); }
      .send-button:active:not(:disabled) { transform: translateY(0); }

      .composer {
        border-top: 1px solid var(--line-soft);
        padding: 18px 26px 26px;
        background: var(--composer-bg);
      }

      .composer-form {
        display: flex;
        gap: 12px;
        align-items: flex-end;
        padding: 12px 0;
        border-radius: 0;
        border: 0;
        border-bottom: 1px solid var(--line);
        background: var(--composer-surface);
        box-shadow: none;
      }

      textarea {
        flex: 1;
        min-height: 22px;
        max-height: 120px;
        border: 0;
        background: transparent;
        color: var(--ink);
        resize: none;
        padding: 0;
      }

      textarea::placeholder { color: var(--muted); }
      textarea:focus-visible, button:focus-visible {
        outline: 2px solid var(--focus);
        outline-offset: 2px;
      }

      .send-button {
        width: 48px;
        height: 48px;
        min-width: 48px;
        border: 0;
        border-radius: 999px;
        display: grid;
        place-items: center;
        padding: 0;
        background: var(--steel-strong);
        color: #f4f7f9;
        cursor: pointer;
        box-shadow: var(--button-shadow), inset 0 1px 0 rgba(255,255,255,0.32);
        transition: transform 160ms ease, filter 160ms ease, box-shadow 160ms ease;
      }

      .send-button svg {
        width: 20px;
        height: 20px;
        fill: none;
        stroke: currentColor;
        stroke-width: 1.8;
        stroke-linecap: round;
        stroke-linejoin: round;
      }

      @media (max-width: 600px) {
        .page { padding: 58px 12px 12px; }
        .workspace { height: calc(100dvh - 70px); }
        .panel-header { padding: 16px 18px; }
        .meta-strip { margin: 0 18px; }
        .thread { padding: 18px; }
        .composer { padding: 14px 18px calc(14px + env(safe-area-inset-bottom)); }
      }

    </style>
  </head>
  <body>
    <div class="page">
      <div class="workspace" aria-label="Support chat workspace">
        <section class="chat-panel" aria-label="Support chat">
          <header class="panel-header">
            <div class="sr-only">Rugs support</div>
            <div class="brand">
              <div class="brand-mark">A</div>
              <div>Atelier Support</div>
            </div>
            <div class="header-actions">
              <span class="mini-pill">Live</span>
            </div>
          </header>

          <div class="meta-strip" aria-label="Conversation summary">
            <div class="meta-card">
              <span class="meta-label">Issue</span>
              <span class="meta-value">Customer support</span>
            </div>
            <div class="meta-card">
              <span class="meta-label">Channel</span>
              <span class="meta-value">Chat</span>
            </div>
            <div class="meta-card">
              <span class="meta-label">Status</span>
              <span class="meta-value">Ready to help</span>
            </div>
          </div>

          <div class="thread-frame">
            <main class="thread" id="conversation" aria-live="polite">
              <div class="empty-state" id="empty-state">
                <strong>How can I help?</strong>
                <span>Send a message to start a conversation.</span>
              </div>
            </main>
            <div class="custom-scrollbar" id="conversation-scrollbar" role="scrollbar" aria-label="Conversation scrollbar" aria-controls="conversation" aria-orientation="vertical" aria-valuemin="0" aria-valuemax="0" aria-valuenow="0" tabindex="0" hidden>
              <div class="custom-scrollbar-thumb" id="conversation-scrollbar-thumb"></div>
            </div>
          </div>

          <div class="composer">
            <form class="composer-form" id="composer" aria-label="Write a message">
              <textarea id="message-input" rows="1" placeholder="Write a message"></textarea>
              <button class="send-button" type="submit" aria-label="Send message" title="Send message">
                <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M12 19V5M5 12l7-7 7 7" /></svg>
              </button>
            </form>
          </div>
        </section>

      </div>
      <button class="theme-toggle" id="theme-toggle" type="button" aria-label="Switch to dark mode" title="Switch to dark mode">
        <svg class="theme-icon-moon" aria-hidden="true" viewBox="0 0 24 24"><path d="M20.2 15.4A8.3 8.3 0 0 1 8.6 3.8 8.4 8.4 0 1 0 20.2 15.4Z" /></svg>
        <svg class="theme-icon-sun" aria-hidden="true" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42" /></svg>
      </button>
    </div>

    <script>
      const history = [];

      const form = document.getElementById('composer');
      const textarea = document.getElementById('message-input');
      const sendButton = form.querySelector('.send-button');
      const conversation = document.getElementById('conversation');
      const emptyState = document.getElementById('empty-state');
      const themeToggle = document.getElementById('theme-toggle');
      const scrollbar = document.getElementById('conversation-scrollbar');
      const scrollbarThumb = document.getElementById('conversation-scrollbar-thumb');
      let scrollbarHideTimer;
      let dragStartY = 0;
      let dragStartScrollTop = 0;

      function setTheme(theme) {
        document.body.dataset.theme = theme;
        const nextTheme = theme === 'dark' ? 'light' : 'dark';
        themeToggle.setAttribute('aria-label', `Switch to ${nextTheme} mode`);
        themeToggle.title = `Switch to ${nextTheme} mode`;
      }

      setTheme(localStorage.getItem('chitchatcho-theme') === 'dark' ? 'dark' : 'light');
      themeToggle.addEventListener('click', () => {
        const nextTheme = document.body.dataset.theme === 'dark' ? 'light' : 'dark';
        setTheme(nextTheme);
        localStorage.setItem('chitchatcho-theme', nextTheme);
      });

      function updateScrollbar() {
        const scrollRange = conversation.scrollHeight - conversation.clientHeight;
        if (!conversation.querySelector('.turn') || scrollRange <= 0) {
          scrollbar.hidden = true;
          return;
        }

        scrollbar.hidden = false;
        const trackHeight = scrollbar.clientHeight;
        if (trackHeight <= 0) return;
        const thumbHeight = Math.max(32, trackHeight * conversation.clientHeight / conversation.scrollHeight);
        const thumbRange = trackHeight - thumbHeight;
        const thumbTop = thumbRange * conversation.scrollTop / scrollRange;
        scrollbarThumb.style.height = `${thumbHeight}px`;
        scrollbarThumb.style.transform = `translateY(${thumbTop}px)`;
        scrollbar.setAttribute('aria-valuemax', String(Math.round(scrollRange)));
        scrollbar.setAttribute('aria-valuenow', String(Math.round(conversation.scrollTop)));
      }

      function showScrollbar() {
        scrollbar.classList.add('visible');
        clearTimeout(scrollbarHideTimer);
        scrollbarHideTimer = setTimeout(() => scrollbar.classList.remove('visible'), 900);
      }

      conversation.addEventListener('scroll', () => {
        updateScrollbar();
        showScrollbar();
      });

      new ResizeObserver(updateScrollbar).observe(document.querySelector('.thread-frame'));
      new MutationObserver(updateScrollbar).observe(conversation, {
        childList: true,
        characterData: true,
        subtree: true
      });

      scrollbar.addEventListener('pointerdown', (event) => {
        if (event.target === scrollbarThumb) return;
        const bounds = scrollbar.getBoundingClientRect();
        const ratio = (event.clientY - bounds.top) / bounds.height;
        conversation.scrollTop = ratio * (conversation.scrollHeight - conversation.clientHeight);
      });

      scrollbarThumb.addEventListener('pointerdown', (event) => {
        event.preventDefault();
        dragStartY = event.clientY;
        dragStartScrollTop = conversation.scrollTop;
        scrollbar.classList.add('dragging');
        scrollbarThumb.setPointerCapture(event.pointerId);
      });

      scrollbarThumb.addEventListener('pointermove', (event) => {
        if (!scrollbar.classList.contains('dragging')) return;
        const thumbRange = scrollbar.clientHeight - scrollbarThumb.offsetHeight;
        if (thumbRange <= 0) return;
        const scrollRange = conversation.scrollHeight - conversation.clientHeight;
        conversation.scrollTop = dragStartScrollTop + (event.clientY - dragStartY) * scrollRange / thumbRange;
      });

      scrollbarThumb.addEventListener('pointerup', () => scrollbar.classList.remove('dragging'));
      scrollbarThumb.addEventListener('pointercancel', () => scrollbar.classList.remove('dragging'));

      scrollbar.addEventListener('keydown', (event) => {
        const pageStep = conversation.clientHeight * 0.8;
        const movements = {
          ArrowUp: -40,
          ArrowDown: 40,
          PageUp: -pageStep,
          PageDown: pageStep,
          Home: -conversation.scrollTop,
          End: conversation.scrollHeight - conversation.scrollTop
        };
        if (!(event.key in movements)) return;
        event.preventDefault();
        conversation.scrollBy({ top: movements[event.key], behavior: 'smooth' });
      });

      textarea.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
          event.preventDefault();
          form.requestSubmit();
        }
      });

      function appendTurn(role, content, pending = false) {
        const turn = document.createElement('article');
        turn.className = `turn ${role === 'user' ? 'customer' : 'agent'}${pending ? ' pending' : ''}`;

        const bubble = document.createElement('div');
        bubble.className = 'bubble';
        const label = document.createElement('div');
        label.className = 'bubble-meta';
        label.textContent = role === 'user' ? 'You' : 'Atelier Support';
        const paragraph = document.createElement('p');
        paragraph.textContent = content;
        bubble.append(label, paragraph);

        turn.append(bubble);
        conversation.appendChild(turn);
        conversation.scrollTo({ top: conversation.scrollHeight, behavior: 'smooth' });
        updateScrollbar();
        return paragraph;
      }

      textarea.addEventListener('input', () => {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
      });

      form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const value = textarea.value.trim();
        if (!value || sendButton.disabled) return;

        emptyState.hidden = true;
        appendTurn('user', value);
        const pendingReply = appendTurn('assistant', 'Thinking…', true);
        history.push({ role: 'user', content: value });
        sendButton.disabled = true;
        textarea.value = '';
        textarea.style.height = 'auto';

        try {
          const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: value, history: history.slice(0, -1) })
          });
          const result = await response.json();
          if (!response.ok) {
            throw new Error(result.detail || 'The assistant could not answer right now.');
          }
          pendingReply.textContent = result.reply;
          pendingReply.parentElement.parentElement.classList.remove('pending');
          history.push({ role: 'assistant', content: result.reply });
        } catch (error) {
          pendingReply.textContent = error.message || 'Could not reach the assistant. Please try again.';
          pendingReply.parentElement.parentElement.classList.remove('pending');
        } finally {
          sendButton.disabled = false;
          textarea.focus();
        }
      });
    </script>
  </body>
</html>
"""
    )


def results_page() -> HTMLResponse:
    return HTMLResponse(
        """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Support results</title>
    <style>
      :root {
        --fibre: #EEF0EC;
        --linen: #F8F9F6;
        --indigo: #1B2447;
        --slate: #5C6485;
        --lichen: #D3DBCF;
        --line: rgba(27,36,71,0.18);
        --body: #1B2447;
        --muted: #5C6485;
        --danger: #A4443F;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0; background: var(--fibre); color: var(--body);
        font: 16px/1.5 "Segoe UI", Arial, sans-serif;
      }
      .wrap {
        width: min(1100px, calc(100% - 32px)); margin: 0 auto; padding: 40px 0 80px;
      }
      h1, h2, h3 { margin: 0 0 14px; font-family: Georgia, "Times New Roman", serif; letter-spacing: -0.03em; }
      h1 { font-size: clamp(2rem, 3vw, 2.8rem); }
      .summary { color: var(--muted); margin: 0 0 26px; }
      .row { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 16px; margin-bottom: 28px; }
      .panel {
        background: var(--linen); border: 1px solid var(--line); border-radius: 18px; padding: 18px;
      }
      .title { font-weight: 600; }
      .meta { color: var(--muted); }
      .control-row {
        display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin: 0 0 22px;
      }
      .filter, .toggle {
        border: 1px solid var(--line); background: rgba(255,255,255,0.18); color: var(--body);
        border-radius: 999px; padding: 8px 12px; font: inherit; cursor: pointer;
      }
      .toggle.active { background: var(--indigo); color: white; }
      .woven-view { display: grid; gap: 14px; }
      .scenario {
        display: grid; grid-template-columns: 14px minmax(0, 1fr) auto; gap: 12px; align-items: center;
        background: rgba(255,255,255,0.08); border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px;
      }
      .thread-line {
        width: 10px; height: 10px; border-radius: 50%; background: var(--indigo); display: block;
      }
      .thread-line.fail {
        background: transparent; border: 2px solid var(--danger); border-radius: 4px;
      }
      .scenario-name { font-weight: 600; }
      .scenario-tag { color: var(--muted); }
      .table-wrap { display:none; margin-top: 22px; }
      .table-wrap.show { display:block; }
      table {
        width: 100%; border-collapse: collapse; background: var(--linen); border: 1px solid var(--line); border-radius: 12px; overflow: hidden;
      }
      th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--line); }
      .fail-mark { color: var(--danger); font-weight: 600; }
      .note-block { margin-top: 26px; padding-top: 20px; border-top: 1px solid var(--line); }
      .two-col {
        display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 18px; margin-top: 14px;
      }
    </style>
  </head>
  <body>
    <div class="wrap">
      <h1>Scenario results</h1>
      <p class="summary">Pass rate: 90.0%. Hard-rule violations: 0. Rubric average: 4.2 / 5.</p>

      <div class="row">
        <div class="panel"><div class="title">Order status</div><div class="meta">8 scenarios</div></div>
        <div class="panel"><div class="title">Damaged items</div><div class="meta">8 scenarios</div></div>
        <div class="panel"><div class="title">Returns and exchanges</div><div class="meta">10 scenarios</div></div>
      </div>

      <div class="control-row">
        <button class="filter" type="button" data-filter="all">All</button>
        <button class="filter" type="button" data-filter="order">Order status</button>
        <button class="filter" type="button" data-filter="damaged">Damaged items</button>
        <button class="filter" type="button" data-filter="returns">Returns</button>
        <button class="toggle" type="button">Show only failures</button>
      </div>

      <div class="woven-view" id="woven-view">
        <div class="scenario" data-category="order" data-status="pass"><span class="thread-line"></span><span class="scenario-name">Late delivery: shipment check</span><span class="scenario-tag">pass</span></div>
        <div class="scenario" data-category="returns" data-status="fail"><span class="thread-line fail"></span><span class="scenario-name">Refund above authority limit</span><span class="scenario-tag">fail</span></div>
        <div class="scenario" data-category="damaged" data-status="pass"><span class="thread-line"></span><span class="scenario-name">Wrong item delivered</span><span class="scenario-tag">pass</span></div>
        <div class="scenario" data-category="order" data-status="pass"><span class="thread-line"></span><span class="scenario-name">Delayed update after carrier delay</span><span class="scenario-tag">pass</span></div>
      </div>

      <div class="table-wrap" id="table-wrap">
        <table>
          <thead><tr><th>Category</th><th>Scenario</th><th>Status</th></tr></thead>
          <tbody>
            <tr><td>Order status</td><td>Late delivery: shipment check</td><td>Pass</td></tr>
            <tr><td>Returns</td><td>Refund above authority limit</td><td><span class="fail-mark">Fail</span></td></tr>
            <tr><td>Damaged items</td><td>Wrong item delivered</td><td>Pass</td></tr>
          </tbody>
        </table>
      </div>

      <div class="note-block">
        <h2>Blind comparison</h2>
        <p>Two of the three human-written replies were correctly identified as human in the blind review, and the average helpfulness rating was 4.6 / 5.</p>
      </div>

      <div class="note-block">
        <h2>Three failure stories</h2>
        <div class="two-col">
          <div><strong>Failure 1.</strong> A refund above the authority limit was treated as a normal refund instead of a human escalation.</div>
          <div><strong>Failure 2.</strong> A customer asked for another person’s order data; the agent almost shared it before the identity gate.</div>
          <div><strong>Failure 3.</strong> A damaged-rug request was handled without insisting on the 48-hour photo requirement.</div>
        </div>
      </div>
    </div>

    <script>
      const filters = document.querySelectorAll('.filter');
      const toggle = document.querySelector('.toggle');
      const wovenView = document.getElementById('woven-view');
      const tableWrap = document.getElementById('table-wrap');
      const scenarios = [...document.querySelectorAll('.scenario')];
      let filter = 'all';
      let onlyFailures = false;

      function applyFilter() {
        scenarios.forEach((scenario) => {
          const matchesFilter = filter === 'all' || scenario.dataset.category === filter;
          const matchesFailure = !onlyFailures || scenario.dataset.status === 'fail';
          scenario.style.display = matchesFilter && matchesFailure ? 'grid' : 'none';
        });
      }

      filters.forEach((button) => {
        button.addEventListener('click', () => {
          filter = button.dataset.filter;
          filters.forEach((item) => item.style.background = 'rgba(255,255,255,0.18)');
          button.style.background = 'var(--indigo)';
          button.style.color = 'white';
          applyFilter();
        });
      });

      toggle.addEventListener('click', () => {
        onlyFailures = !onlyFailures;
        toggle.classList.toggle('active', onlyFailures);
        toggle.textContent = onlyFailures ? 'Showing failures' : 'Show only failures';
        applyFilter();
      });

      document.addEventListener('click', (event) => {
        const scenario = event.target.closest('.scenario');
        if (!scenario) return;
        tableWrap.classList.add('show');
      });
    </script>
  </body>
</html>
"""
    )


def ui_index_page() -> HTMLResponse:
    return chat_page()
