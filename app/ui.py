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
    <style>
      :root {
        --bg: #f3efe8;
        --bg-strong: #e7dfd4;
        --panel: rgba(255, 255, 255, 0.76);
        --panel-strong: rgba(255, 255, 255, 0.9);
        --ink: #171b1f;
        --muted: #5f625d;
        --line: rgba(23, 27, 31, 0.12);
        --stone: #1d2429;
        --stone-soft: #2a3035;
        --sand: #ddd0ba;
        --sage: #b9c7b4;
        --gold: #c99552;
        --shadow: rgba(15, 17, 19, 0.12);
      }

      * { box-sizing: border-box; }
      html, body { height: 100%; }
      body {
        margin: 0;
        min-height: 100vh;
        background:
          radial-gradient(circle at top left, rgba(255,255,255,0.9), transparent 28%),
          linear-gradient(135deg, var(--bg) 0%, var(--bg-strong) 100%);
        color: var(--ink);
        font: 16px/1.55 "Segoe UI", Arial, sans-serif;
      }
      button, textarea { font: inherit; }

      .page {
        min-height: 100vh;
        display: grid;
        place-items: center;
        padding: 26px;
      }

      .workspace {
        width: min(1200px, 100%);
        min-height: min(900px, calc(100vh - 52px));
        display: grid;
        grid-template-columns: minmax(0, 1.7fr) minmax(300px, 0.78fr);
        border: 1px solid var(--line);
        border-radius: 28px;
        background: rgba(255,255,255,0.34);
        backdrop-filter: blur(12px);
        box-shadow: 0 32px 90px rgba(19, 20, 22, 0.12);
        overflow: hidden;
      }

      .chat-panel {
        display: flex;
        flex-direction: column;
        background: linear-gradient(180deg, rgba(255,255,255,0.7), rgba(248,245,240,0.74));
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
        font-weight: 700;
        letter-spacing: -0.04em;
      }

      .brand-mark {
        width: 42px;
        height: 42px;
        border-radius: 14px;
        display: grid;
        place-items: center;
        background: linear-gradient(135deg, var(--stone) 0%, #414a52 100%);
        color: #f8f5ee;
        font-size: 0.9rem;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.25);
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
        padding: 8px 12px;
        border-radius: 999px;
        background: rgba(39, 48, 55, 0.06);
        border: 1px solid var(--line);
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
        background: #5f8d5c;
        box-shadow: 0 0 0 4px rgba(95,141,92,0.14);
      }

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
        gap: 12px;
        padding: 18px 26px 0;
      }

      .meta-card {
        padding: 14px 16px;
        border: 1px solid var(--line);
        border-radius: 18px;
        background: rgba(255,255,255,0.4);
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

      .thread {
        flex: 1;
        position: relative;
        overflow: auto;
        padding: 26px 26px 18px 34px;
      }

      .thread::before {
        content: "";
        position: absolute;
        left: 22px;
        top: 26px;
        bottom: 18px;
        width: 2px;
        background: linear-gradient(180deg, rgba(23,27,31,0.12), rgba(23,27,31,0.18), rgba(23,27,31,0.12));
      }

      .turn {
        position: relative;
        display: grid;
        grid-template-columns: 28px minmax(0, 1fr);
        gap: 16px;
        margin: 16px 0;
        align-items: start;
      }

      .turn.customer {
        grid-template-columns: minmax(0, 1fr) 28px;
        justify-items: end;
      }

      .turn-node {
        width: 28px;
        height: 28px;
        border-radius: 50%;
        border: 1px solid rgba(23, 27, 31, 0.18);
        background: rgba(255,255,255,0.45);
        box-shadow: 0 0 0 5px rgba(255,255,255,0.4);
        display: grid;
        place-items: center;
        font-size: 0.62rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        color: var(--muted);
        cursor: pointer;
        transition: transform 0.2s ease, border-color 0.2s ease;
        z-index: 1;
      }

      .turn.customer .turn-node {
        justify-self: end;
      }

      .turn-node:hover {
        transform: scale(1.04);
        border-color: rgba(23,27,31,0.3);
      }

      .turn-node.answer {
        background: linear-gradient(135deg, var(--stone) 0%, var(--stone-soft) 100%);
        color: #f5f0ea;
        border-color: rgba(23,27,31,0.8);
      }

      .turn-node.clarify {
        background: linear-gradient(135deg, rgba(201,149,82,0.18), rgba(201,149,82,0.32));
        border-color: rgba(201,149,82,0.6);
        color: #6c4e20;
      }

      .bubble {
        max-width: min(82%, 460px);
        padding: 16px 18px;
        border-radius: 20px;
        background: rgba(255,255,255,0.38);
        border: 1px solid rgba(23,27,31,0.06);
        box-shadow: 0 10px 18px rgba(17, 20, 23, 0.04);
      }

      .turn.customer .bubble {
        background: linear-gradient(135deg, var(--stone) 0%, #2d363d 100%);
        color: #f2efe9;
        border-color: rgba(0,0,0,0.08);
      }

      .bubble-meta {
        font-size: 0.7rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 6px;
      }

      .turn.customer .bubble-meta {
        color: rgba(255,255,255,0.72);
      }

      .bubble p {
        margin: 0;
        font-size: 1.04rem;
        line-height: 1.7;
      }

      .composer {
        border-top: 1px solid var(--line);
        padding: 18px 22px 26px;
        background: rgba(255,255,255,0.2);
      }

      .composer-form {
        display: flex;
        gap: 12px;
        align-items: flex-end;
        padding: 12px 14px 12px 18px;
        border-radius: 22px;
        border: 1px solid rgba(23,27,31,0.08);
        background: rgba(255,255,255,0.48);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.44);
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
        outline: 2px solid rgba(201,149,82,0.9);
        outline-offset: 2px;
      }

      .send-button {
        min-width: 116px;
        min-height: 46px;
        border: 0;
        border-radius: 999px;
        background: linear-gradient(135deg, var(--stone) 0%, #3d4650 100%);
        color: #f9f5ee;
        font-weight: 700;
        cursor: pointer;
        box-shadow: 0 12px 22px rgba(24,27,31,0.18);
      }

      .inspector {
        background: linear-gradient(180deg, rgba(22,25,29,0.96), rgba(18,22,25,0.98));
        color: #f5f0ea;
        border-left: 1px solid rgba(255,255,255,0.08);
        display: flex;
        flex-direction: column;
      }

      .inspector-inner {
        padding: 26px 22px 20px;
        display: flex;
        flex-direction: column;
        gap: 18px;
        height: 100%;
      }

      .inspector-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        padding-bottom: 12px;
        border-bottom: 1px solid rgba(255,255,255,0.08);
      }

      .inspector-title {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }

      .kicker {
        font-size: 0.7rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: rgba(255,255,255,0.62);
      }

      .move-label {
        font-size: 1.05rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        text-transform: capitalize;
      }

      .close-button {
        border: 1px solid rgba(255,255,255,0.08);
        background: rgba(255,255,255,0.02);
        color: #f5f0ea;
        width: 36px;
        height: 36px;
        border-radius: 10px;
        cursor: pointer;
        font-size: 1.2rem;
      }

      .inspector-block {
        display: grid;
        gap: 10px;
      }

      .inspector-block h3 {
        margin: 0;
        font-size: 0.72rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: rgba(255,255,255,0.62);
      }

      .inspector-block p,
      .inspector-block li {
        margin: 0;
        color: rgba(245,240,234,0.9);
      }

      .inspector-block ul {
        margin: 0;
        padding-left: 18px;
      }

      .tag-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }

      .tag {
        display: inline-flex;
        align-items: center;
        padding: 7px 10px;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,0.08);
        background: rgba(255,255,255,0.03);
        color: rgba(245,240,234,0.94);
        font-size: 0.78rem;
      }

      .nav-row {
        display: flex;
        gap: 10px;
        padding-top: 8px;
        margin-top: auto;
      }

      .nav-button {
        flex: 1;
        min-height: 42px;
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.08);
        background: rgba(255,255,255,0.02);
        color: #f5f0ea;
        cursor: pointer;
      }

      @media (max-width: 900px) {
        .workspace {
          grid-template-columns: 1fr;
        }
        .inspector {
          border-left: 0;
          border-top: 1px solid rgba(255,255,255,0.08);
        }
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
              <button class="ghost-button" type="button">Order R-8402</button>
            </div>
          </header>

          <div class="meta-strip" aria-label="Conversation summary">
            <div class="meta-card">
              <span class="meta-label">Issue</span>
              <span class="meta-value">Shipping status</span>
            </div>
            <div class="meta-card">
              <span class="meta-label">Channel</span>
              <span class="meta-value">Chat</span>
            </div>
            <div class="meta-card">
              <span class="meta-label">Priority</span>
              <span class="meta-value">Normal</span>
            </div>
          </div>

          <main class="thread" id="conversation" aria-live="polite">
            <article class="turn agent" aria-label="Turn 1: answer">
              <button class="turn-node answer" type="button" data-index="0" aria-label="Turn 1 answer">01</button>
              <div class="bubble">
                <div class="bubble-meta">Atelier Support</div>
                <p>Hi, I’m here to help with your rug order.</p>
              </div>
            </article>

            <article class="turn customer" aria-label="Customer message">
              <div class="bubble">
                <div class="bubble-meta">Customer</div>
                <p>Where is my order?</p>
              </div>
              <button class="turn-node answer" type="button" data-index="1" aria-label="Customer message">02</button>
            </article>

            <article class="turn agent" aria-label="Turn 2: clarify">
              <button class="turn-node clarify" type="button" data-index="2" aria-label="Turn 2 clarify">03</button>
              <div class="bubble">
                <div class="bubble-meta">Atelier Support</div>
                <p>Happy to check. What is the order number?</p>
              </div>
            </article>
          </main>

          <div class="composer">
            <form class="composer-form" id="composer" aria-label="Write a message">
              <textarea id="message-input" rows="1" placeholder="Write a message"></textarea>
              <button class="send-button" type="submit">Send</button>
            </form>
          </div>
        </section>

        <aside class="inspector" id="inspector" aria-label="Decision inspector" aria-hidden="false">
          <div class="inspector-inner">
            <div class="inspector-head">
              <div class="inspector-title">
                <span class="kicker">Decision trace</span>
                <div class="move-label" id="inspector-move">answer</div>
              </div>
              <button class="close-button" id="close-inspector" type="button" aria-label="Close decision detail">×</button>
            </div>

            <div class="inspector-block">
              <div class="kicker" id="inspector-turn">Turn 1</div>
              <h3>Reason</h3>
              <p id="inspector-reason">The agent can answer directly from the known order context and reassure the customer without blocking the conversation.</p>
            </div>

            <div class="inspector-block">
              <h3>Known</h3>
              <ul id="inspector-known"><li>The customer is asking about a rug order.</li></ul>
            </div>

            <div class="inspector-block">
              <h3>Missing</h3>
              <ul id="inspector-missing"><li>Order number or verification details.</li></ul>
            </div>

            <div class="inspector-block">
              <h3>Policy refs</h3>
              <div class="tag-row" id="inspector-policies"></div>
            </div>

            <div class="inspector-block">
              <h3>Tools</h3>
              <div class="tag-row" id="inspector-tools"></div>
            </div>

            <div class="nav-row">
              <button class="nav-button" type="button" id="prev-turn">Previous</button>
              <button class="nav-button" type="button" id="next-turn">Next</button>
            </div>
          </div>
        </aside>
      </div>
    </div>

    <script>
      const decisions = [
        {
          turn: 'Turn 1',
          move: 'answer',
          reason: 'The agent can answer directly from the known order context and reassure the customer without blocking the conversation.',
          known: ['The customer is asking about a rug order.'],
          missing: ['Order number or verification details.'],
          policies: ['shipment_status', 'customer_reassurance'],
          tools: ['lookup_order']
        },
        {
          turn: 'Turn 2',
          move: 'clarify',
          reason: 'The agent needs a single missing fact to move forward and keep the conversation efficient.',
          known: ['The inquiry is about a pending order.'],
          missing: ['Order number.'],
          policies: ['identity_check'],
          tools: ['lookup_order']
        },
        {
          turn: 'Turn 3',
          move: 'answer',
          reason: 'Once the order number is known, the agent can provide a concise status update and next steps.',
          known: ['The customer has supplied the order number.'],
          missing: ['Customer verification details if needed.'],
          policies: ['shipment_status'],
          tools: ['track_shipment']
        }
      ];

      const inspector = document.getElementById('inspector');
      const mover = document.getElementById('inspector-move');
      const turnLabel = document.getElementById('inspector-turn');
      const reason = document.getElementById('inspector-reason');
      const knownList = document.getElementById('inspector-known');
      const missingList = document.getElementById('inspector-missing');
      const policyTarget = document.getElementById('inspector-policies');
      const toolsTarget = document.getElementById('inspector-tools');
      const prev = document.getElementById('prev-turn');
      const next = document.getElementById('next-turn');
      const closeBtn = document.getElementById('close-inspector');
      let activeIndex = 0;

      function renderInspector(index) {
        const decision = decisions[index];
        if (!decision) return;
        mover.textContent = decision.move;
        turnLabel.textContent = decision.turn;
        reason.textContent = decision.reason;
        knownList.innerHTML = decision.known.map(item => `<li>${item}</li>`).join('');
        missingList.innerHTML = decision.missing.map(item => `<li>${item}</li>`).join('');
        policyTarget.innerHTML = decision.policies.map(item => `<span class="tag">${item}</span>`).join('');
        toolsTarget.innerHTML = decision.tools.map(item => `<span class="tag">${item}</span>`).join('');
      }

      function openInspector(index) {
        activeIndex = index;
        renderInspector(index);
      }

      document.addEventListener('click', (event) => {
        const btn = event.target.closest('.turn-node');
        if (btn) {
          openInspector(Number(btn.dataset.index));
        }
      });

      closeBtn.addEventListener('click', () => {
        inspector.setAttribute('aria-hidden', 'true');
      });

      prev.addEventListener('click', () => {
        activeIndex = Math.max(0, activeIndex - 1);
        renderInspector(activeIndex);
      });

      next.addEventListener('click', () => {
        activeIndex = Math.min(decisions.length - 1, activeIndex + 1);
        renderInspector(activeIndex);
      });

      const form = document.getElementById('composer');
      const textarea = document.getElementById('message-input');

      textarea.addEventListener('input', () => {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
      });

      form.addEventListener('submit', (event) => {
        event.preventDefault();
        const value = textarea.value.trim();
        if (!value) return;

        const customerTurn = document.createElement('article');
        customerTurn.className = 'turn customer';
        customerTurn.innerHTML = `
          <div class="bubble">
            <div class="bubble-meta">Customer</div>
            <p>${value}</p>
          </div>
          <button class="turn-node answer" type="button" data-index="${decisions.length}" aria-label="Customer message">${String(decisions.length + 1).padStart(2, '0')}</button>
        `;
        document.getElementById('conversation').appendChild(customerTurn);

        const agentTurn = document.createElement('article');
        agentTurn.className = 'turn agent';
        agentTurn.innerHTML = `
          <button class="turn-node answer" type="button" data-index="${decisions.length + 1}" aria-label="Turn ${decisions.length + 1} answer">${String(decisions.length + 2).padStart(2, '0')}</button>
          <div class="bubble">
            <div class="bubble-meta">Atelier Support</div>
            <p>I can check that. I’ll look up the order and confirm the latest status next.</p>
          </div>
        `;
        document.getElementById('conversation').appendChild(agentTurn);

        textarea.value = '';
        textarea.style.height = 'auto';
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
