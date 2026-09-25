/**
 * CaseAI — Case-Aware AI Investigation Assistant Client
 * Provides floating assistant widget, SSE streaming chat, case-context grounding,
 * special investigative actions, tokenless memory handling, and chat exports.
 */

(function () {
  let activeCaseId = "global";
  let activeCaseData = null;
  let isStreaming = false;
  let chatHistory = [];
  let isWindowOpen = false;
  let isMinimized = false;
  let isExpanded = false;

  // Initialize CaseAI DOM elements when document is ready
  document.addEventListener("DOMContentLoaded", () => {
    // Only mount if user is authenticated (has token)
    const token = localStorage.getItem("token");
    if (!token) return;

    injectCaseAIDOM();
    bindEvents();
    autoDetectCaseFromUrl();
  });

  /**
   * Automatically detect if page has a case ID (e.g., result.html?id=...)
   */
  function autoDetectCaseFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const caseId = params.get("id");
    if (caseId && caseId.length === 24) {
      setCaseContext(caseId, false);
    } else {
      updateContextUI("global", null);
    }
  }

  /**
   * Injects the CaseAI floating trigger and window into the page body
   */
  function injectCaseAIDOM() {
    if (document.getElementById("caseAiDrawer")) return;

    const wrapper = document.createElement("div");
    wrapper.id = "caseAiContainer";
    wrapper.innerHTML = `
      <!-- Floating Trigger Button -->
      <button class="caseai-floating-trigger" id="caseAiTrigger" title="Open CaseAI Investigator (Ctrl+J)">
        <span class="caseai-trigger-spark">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
            <path d="M12 2a10 10 0 0 1 10 10c0 5.523-4.477 10-10 10S2 17.523 2 12 6.477 2 12 2z"/>
            <path d="M12 8v4"/><path d="M12 16h.01"/>
          </svg>
        </span>
        <span>CaseAI</span>
        <span class="caseai-trigger-badge" id="caseAiTriggerDot"></span>
      </button>

      <!-- Chat Drawer Window -->
      <div class="caseai-window" id="caseAiDrawer" role="dialog" aria-label="CaseAI Assistant">
        <!-- Header -->
        <div class="caseai-header">
          <div class="caseai-header-left">
            <div class="caseai-avatar-icon">✦</div>
            <div>
              <div class="caseai-header-title">
                CaseAI
                <span style="font-size:0.7rem; font-weight:normal; background:rgba(0,229,255,0.15); color:var(--accent-cyan); padding:0.1rem 0.4rem; border-radius:4px;" id="caseAiProviderBadge">AI Engine</span>
              </div>
              <div class="caseai-header-sub">AI-Powered Case Investigation Assistant</div>
            </div>
          </div>
          <div class="caseai-header-actions">
            <button class="caseai-icon-btn" id="caseAiSwitchCaseBtn" title="Switch Case">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 3h5v5"/><path d="M4 20L21 3"/><path d="M21 16v5h-5"/><path d="M15 15l6 6"/><path d="M4 4l5 5"/></svg>
            </button>
            <button class="caseai-icon-btn" id="caseAiSearchToggleBtn" title="Search Conversation">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            </button>
            <button class="caseai-icon-btn" id="caseAiExpandBtn" title="Expand / Restore Window">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
            </button>
            <button class="caseai-icon-btn" id="caseAiMinimizeBtn" title="Minimize">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/></svg>
            </button>
            <button class="caseai-icon-btn" id="caseAiCloseBtn" title="Close">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
        </div>

        <!-- In-Window Search Bar (Hidden by default) -->
        <div class="caseai-search-bar" id="caseAiSearchBar">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input type="text" class="caseai-search-input" id="caseAiSearchInput" placeholder="Filter conversation messages...">
          <button class="caseai-icon-btn" id="caseAiSearchClose" style="width:20px; height:20px;">✕</button>
        </div>

        <!-- Case Context Indicator Strip -->
        <div class="caseai-context-strip">
          <div class="caseai-case-badge" id="caseAiContextBadge">
            <span>●</span>
            <span id="caseAiCaseLabel">Loading context...</span>
          </div>
          <button class="caseai-context-toggle-btn" id="caseAiContextToggleBtn">
            View Case Context ▾
          </button>
        </div>

        <!-- Collapsible Context Detail Drawer -->
        <div class="caseai-context-drawer" id="caseAiContextDrawer">
          <div class="caseai-context-grid">
            <div class="caseai-context-item">
              <label>Employer</label>
              <span id="ctxCompany">--</span>
            </div>
            <div class="caseai-context-item">
              <label>Role</label>
              <span id="ctxJob">--</span>
            </div>
            <div class="caseai-context-item">
              <label>Recruiter Email</label>
              <span id="ctxEmail">--</span>
            </div>
            <div class="caseai-context-item">
              <label>Risk Assessment</label>
              <span id="ctxRisk" style="color:var(--risk-danger);">--</span>
            </div>
          </div>
          <div style="font-size:0.75rem; color:var(--text-muted); margin-bottom:0.3rem;">
            <strong>Grounding Signals:</strong>
            <div id="ctxRedFlags" style="margin-top:0.25rem;">None loaded</div>
          </div>
        </div>

        <!-- Special AI Actions Bar -->
        <div class="caseai-actions-bar">
          <button class="caseai-action-chip" data-action="explain">
            <span>📝</span> Explain
          </button>
          <button class="caseai-action-chip" data-action="investigate">
            <span>🔍</span> Investigate
          </button>
          <button class="caseai-action-chip" data-action="checklist">
            <span>📋</span> Checklist
          </button>
          <button class="caseai-action-chip" data-action="recruiter_questions">
            <span>✉️</span> Recruiter Q's
          </button>
          <button class="caseai-action-chip" data-action="summary">
            <span>📄</span> Case Summary
          </button>
        </div>

        <!-- Messages Stream Container -->
        <div class="caseai-messages" id="caseAiMessages">
          <!-- Initial welcome and suggested questions will populate here -->
        </div>

        <!-- Footer / Input Bar -->
        <div class="caseai-footer">
          <div class="caseai-input-row">
            <textarea class="caseai-textarea" id="caseAiInput" rows="1" placeholder="Ask CaseAI about this investigation... (Enter to send)"></textarea>
            <button class="caseai-send-btn" id="caseAiSendBtn" title="Send (Enter)">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            </button>
          </div>

          <div class="caseai-footer-toolbar">
            <div style="display:flex; gap:0.6rem;">
              <button class="caseai-tool-btn" id="caseAiExportBtn" title="Export conversation">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                Export
              </button>
              <button class="caseai-tool-btn" id="caseAiClearBtn" title="Reset chat history">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                Clear
              </button>
            </div>
            <span style="font-size:0.68rem; color:var(--text-muted);" id="caseAiTokenlessIndicator">Continuous Memory Active</span>
          </div>

          <div class="caseai-disclaimer">
            CaseAI provides AI-assisted analysis based on available case information. It may make mistakes and does not independently establish whether an offer is fraudulent.
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(wrapper);
  }

  /**
   * Binds click and keyboard listeners
   */
  function bindEvents() {
    const trigger = document.getElementById("caseAiTrigger");
    const drawer = document.getElementById("caseAiDrawer");
    const closeBtn = document.getElementById("caseAiCloseBtn");
    const minimizeBtn = document.getElementById("caseAiMinimizeBtn");
    const expandBtn = document.getElementById("caseAiExpandBtn");
    const contextToggleBtn = document.getElementById("caseAiContextToggleBtn");
    const contextDrawer = document.getElementById("caseAiContextDrawer");
    const sendBtn = document.getElementById("caseAiSendBtn");
    const input = document.getElementById("caseAiInput");
    const clearBtn = document.getElementById("caseAiClearBtn");
    const exportBtn = document.getElementById("caseAiExportBtn");
    const switchCaseBtn = document.getElementById("caseAiSwitchCaseBtn");
    const searchToggleBtn = document.getElementById("caseAiSearchToggleBtn");
    const searchBar = document.getElementById("caseAiSearchBar");
    const searchInput = document.getElementById("caseAiSearchInput");
    const searchClose = document.getElementById("caseAiSearchClose");

    // Trigger toggle
    trigger.addEventListener("click", () => {
      toggleCaseAI();
    });

    closeBtn.addEventListener("click", () => {
      closeCaseAI();
    });

    minimizeBtn.addEventListener("click", () => {
      isMinimized = !isMinimized;
      drawer.classList.toggle("minimized", isMinimized);
    });

    expandBtn.addEventListener("click", () => {
      isExpanded = !isExpanded;
      drawer.classList.toggle("expanded", isExpanded);
    });

    contextToggleBtn.addEventListener("click", () => {
      const isOpen = contextDrawer.classList.toggle("open");
      contextToggleBtn.textContent = isOpen ? "Hide Case Context ▴" : "View Case Context ▾";
    });

    // Keyboard shortcut Ctrl+J / Cmd+J
    document.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "j") {
        e.preventDefault();
        toggleCaseAI();
      }
    });

    // Send on button click
    sendBtn.addEventListener("click", () => {
      handleSendMessage();
    });

    // Auto-resize and Enter to send in textarea
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
      }
    });

    input.addEventListener("input", () => {
      input.style.height = "auto";
      input.style.height = Math.min(input.scrollHeight, 120) + "px";
    });

    // Special AI Actions
    document.querySelectorAll(".caseai-action-chip").forEach((btn) => {
      btn.addEventListener("click", () => {
        const action = btn.getAttribute("data-action");
        if (action && !isStreaming) {
          executeAction(action);
        }
      });
    });

    // Clear Chat
    clearBtn.addEventListener("click", () => {
      if (confirm("Reset conversation history for this case?")) {
        clearChat();
      }
    });

    // Export Chat
    exportBtn.addEventListener("click", () => {
      exportChat();
    });

    // Switch Case Modal
    switchCaseBtn.addEventListener("click", () => {
      openCaseSwitcher();
    });

    // Search Toggle
    searchToggleBtn.addEventListener("click", () => {
      searchBar.classList.toggle("open");
      if (searchBar.classList.contains("open")) {
        searchInput.focus();
      } else {
        filterMessages("");
      }
    });

    searchClose.addEventListener("click", () => {
      searchBar.classList.remove("open");
      searchInput.value = "";
      filterMessages("");
    });

    searchInput.addEventListener("input", (e) => {
      filterMessages(e.target.value);
    });
  }

  function toggleCaseAI() {
    isWindowOpen = !isWindowOpen;
    const drawer = document.getElementById("caseAiDrawer");
    drawer.classList.toggle("open", isWindowOpen);
    if (isWindowOpen) {
      if (isMinimized) {
        isMinimized = false;
        drawer.classList.remove("minimized");
      }
      document.getElementById("caseAiInput").focus();
    }
  }

  function openCaseAI(caseId = null) {
    isWindowOpen = true;
    isMinimized = false;
    const drawer = document.getElementById("caseAiDrawer");
    drawer.classList.add("open");
    drawer.classList.remove("minimized");

    if (caseId && caseId !== activeCaseId) {
      setCaseContext(caseId, true);
    }
    setTimeout(() => {
      document.getElementById("caseAiInput").focus();
    }, 150);
  }

  function closeCaseAI() {
    isWindowOpen = false;
    document.getElementById("caseAiDrawer").classList.remove("open");
  }

  /**
   * Sets active case context, fetches context details, and loads message history
   */
  async function setCaseContext(caseId, forceReload = false) {
    activeCaseId = caseId;
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const res = await fetch(`${window.API_BASE_URL || "/api"}/cases/${caseId}/context`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        activeCaseData = data.case_context;
        updateContextUI(caseId, activeCaseData);
      } else {
        updateContextUI("global", null);
      }
    } catch (e) {
      console.warn("Failed to load case context:", e);
      updateContextUI("global", null);
    }

    await loadChatHistory(caseId);
  }

  /**
   * Updates context badge, drawer labels, and indicator dot
   */
  function updateContextUI(caseId, context) {
    const badge = document.getElementById("caseAiContextBadge");
    const label = document.getElementById("caseAiCaseLabel");
    const dot = document.getElementById("caseAiTriggerDot");

    if (caseId === "global" || !context) {
      label.textContent = "Global Safety Assistant (No Case Selected)";
      badge.style.color = "var(--text-secondary)";
      dot.style.background = "var(--accent-cyan)";
      document.getElementById("ctxCompany").textContent = "N/A";
      document.getElementById("ctxJob").textContent = "General Query";
      document.getElementById("ctxEmail").textContent = "N/A";
      document.getElementById("ctxRisk").textContent = "General Guidance";
      document.getElementById("ctxRedFlags").textContent = "Global mode: Select a case to activate forensic analysis.";
      return;
    }

    const company = context.company?.name || "Company";
    const job = context.job?.title || "Role";
    const risk = context.risk_level || "Assessed";
    const score = context.risk_score !== undefined ? context.risk_score : (100 - (context.trust_score || 50));

    label.textContent = `Case: ${company} — ${job} (${risk})`;
    badge.style.color = risk === "High Risk" ? "var(--risk-danger)" : (risk === "Suspicious" ? "var(--risk-warning)" : "var(--risk-safe)");
    dot.style.background = badge.style.color;

    document.getElementById("ctxCompany").textContent = company;
    document.getElementById("ctxJob").textContent = job;
    document.getElementById("ctxEmail").textContent = context.company?.email || "Not specified";
    document.getElementById("ctxRisk").textContent = `${risk} (${score}/100 Risk)`;
    document.getElementById("ctxRisk").style.color = badge.style.color;

    const flagsContainer = document.getElementById("ctxRedFlags");
    if (context.red_flags && context.red_flags.length > 0) {
      flagsContainer.innerHTML = context.red_flags
        .map(f => `<div style="margin-bottom:0.2rem;">• <strong>[${f.severity || "FLAG"}]</strong> ${escapeHTML(f.title)}</div>`)
        .join("");
    } else {
      flagsContainer.innerHTML = "<span style='color:var(--risk-safe);'>✓ No critical red flags recorded in this case.</span>";
    }
  }

  /**
   * Loads message history from MongoDB
   */
  async function loadChatHistory(caseId) {
    const token = localStorage.getItem("token");
    const container = document.getElementById("caseAiMessages");
    container.innerHTML = "";

    try {
      const res = await fetch(`${window.API_BASE_URL || "/api"}/cases/${caseId}/chat/history`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        chatHistory = data.messages || [];

        if (chatHistory.length === 0) {
          renderWelcomeGreeting();
        } else {
          chatHistory.forEach((msg) => {
            appendMessageBubble(msg.role, msg.content, false);
          });
        }
      } else {
        renderWelcomeGreeting();
      }
    } catch (e) {
      renderWelcomeGreeting();
    }
    scrollMessagesToBottom();
  }

  /**
   * Renders initial welcome greeting with clickable quick questions
   */
  function renderWelcomeGreeting() {
    const container = document.getElementById("caseAiMessages");
    const isCase = activeCaseId !== "global" && activeCaseData;
    const company = isCase ? activeCaseData.company?.name : "your target job offer";

    const bubbleHtml = `
      <div class="caseai-message-row assistant">
        <div class="caseai-message-avatar">✦</div>
        <div class="caseai-message-bubble">
          <p><strong>Greetings Investigator.</strong> I am <strong>CaseAI</strong>, your forensic employment fraud assistant.</p>
          ${isCase
            ? `<p>I have loaded the full case dossier for <strong>${escapeHTML(company)}</strong>, including extracted offer text, risk scores, recruiter contact vectors, and detected threat signals.</p>`
            : `<p>I am operating in <strong>Global Assistant</strong> mode. Select a case from your history or ask any recruitment security question.</p>`
          }
          <div style="margin-top:0.75rem; font-weight:600; font-size:0.8rem; color:var(--text-secondary);">Suggested Questions:</div>
          <div class="caseai-suggestions">
            <button class="caseai-suggestion-pill" data-q="Why was this job offer flagged?">
              ⚡ Why is this offer considered risky?
            </button>
            <button class="caseai-suggestion-pill" data-q="What are the biggest red flags detected in this case?">
              🚩 What are the biggest red flags in this case?
            </button>
            <button class="caseai-suggestion-pill" data-q="Does the recruiter email and contact info look legitimate?">
              🔍 Verify the recruiter email and contact info
            </button>
            <button class="caseai-suggestion-pill" data-q="What specific questions should I ask this recruiter?">
              ✉️ What strategic questions should I ask the recruiter?
            </button>
            <button class="caseai-suggestion-pill" data-q="Generate a verification checklist for this employer.">
              📋 Generate a 5-step verification checklist
            </button>
          </div>
        </div>
      </div>
    `;

    container.innerHTML = bubbleHtml;

    // Bind suggestion pill clicks
    container.querySelectorAll(".caseai-suggestion-pill").forEach((pill) => {
      pill.addEventListener("click", () => {
        const question = pill.getAttribute("data-q");
        if (question && !isStreaming) {
          sendMessage(question);
        }
      });
    });
  }

  /**
   * Sends user message and streams assistant response via SSE
   */
  async function handleSendMessage() {
    const input = document.getElementById("caseAiInput");
    const message = input.value.trim();
    if (!message || isStreaming) return;

    input.value = "";
    input.style.height = "auto";
    await sendMessage(message);
  }

  async function sendMessage(messageText) {
    if (isStreaming) return;
    const token = localStorage.getItem("token");
    if (!token) return;

    isStreaming = true;
    document.getElementById("caseAiSendBtn").disabled = true;

    // 1. Render user message bubble
    appendMessageBubble("user", messageText, true);
    scrollMessagesToBottom();

    // 2. Prepare streaming assistant bubble
    const assistantBubble = appendMessageBubble("assistant", "", true, true);
    const bubbleContent = assistantBubble.querySelector(".caseai-bubble-text");
    const cursor = assistantBubble.querySelector(".caseai-typing-cursor");

    let fullResponse = "";

    try {
      const response = await fetch(`${window.API_BASE_URL || "/api"}/cases/${activeCaseId}/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ message: messageText })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop(); // keep partial line

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data: ")) continue;
          const dataStr = trimmed.substring(6).trim();

          if (dataStr === "[DONE]") {
            break;
          }

          try {
            const parsed = JSON.parse(dataStr);
            if (parsed.chunk) {
              fullResponse += parsed.chunk;
              bubbleContent.innerHTML = formatMarkdown(fullResponse);
              scrollMessagesToBottom();
            } else if (parsed.error) {
              fullResponse += `\n[Error: ${parsed.error}]`;
              bubbleContent.innerHTML = formatMarkdown(fullResponse);
            }
          } catch (e) {
            // plain text chunk fallback
            fullResponse += dataStr;
            bubbleContent.innerHTML = formatMarkdown(fullResponse);
          }
        }
      }
    } catch (err) {
      console.error("Stream error:", err);
      fullResponse += "\n\n*Unable to complete streaming request. Please ensure local Ollama is active or API key is set.*";
      bubbleContent.innerHTML = formatMarkdown(fullResponse);
    } finally {
      if (cursor) cursor.remove();
      isStreaming = false;
      document.getElementById("caseAiSendBtn").disabled = false;
      addMessageActions(assistantBubble, fullResponse);
      scrollMessagesToBottom();
    }
  }

  /**
   * Executes a special quick action with streaming
   */
  async function executeAction(actionName) {
    if (isStreaming) return;
    const token = localStorage.getItem("token");
    if (!token) return;

    isStreaming = true;
    document.getElementById("caseAiSendBtn").disabled = true;

    const actionLabels = {
      explain: "Explain Case in Simple Terms",
      investigate: "Forensic Investigation Check",
      checklist: "Generate Verification Checklist",
      recruiter_questions: "Questions for Recruiter",
      summary: "Executive Case Summary"
    };

    appendMessageBubble("user", `✦ Action: ${actionLabels[actionName] || actionName}`, true);
    const assistantBubble = appendMessageBubble("assistant", "", true, true);
    const bubbleContent = assistantBubble.querySelector(".caseai-bubble-text");
    const cursor = assistantBubble.querySelector(".caseai-typing-cursor");

    let fullResponse = "";

    try {
      const response = await fetch(`${window.API_BASE_URL || "/api"}/cases/${activeCaseId}/chat/action`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ action: actionName })
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data: ")) continue;
          const dataStr = trimmed.substring(6).trim();

          if (dataStr === "[DONE]") break;

          try {
            const parsed = JSON.parse(dataStr);
            if (parsed.chunk) {
              fullResponse += parsed.chunk;
              bubbleContent.innerHTML = formatMarkdown(fullResponse);
              scrollMessagesToBottom();
            }
          } catch (e) {
            fullResponse += dataStr;
            bubbleContent.innerHTML = formatMarkdown(fullResponse);
          }
        }
      }
    } catch (err) {
      fullResponse += "\n\n*Action could not be executed.*";
      bubbleContent.innerHTML = formatMarkdown(fullResponse);
    } finally {
      if (cursor) cursor.remove();
      isStreaming = false;
      document.getElementById("caseAiSendBtn").disabled = false;
      addMessageActions(assistantBubble, fullResponse);
      scrollMessagesToBottom();
    }
  }

  /**
   * Appends message bubble to the messages stream
   */
  function appendMessageBubble(role, content, animate = false, hasCursor = false) {
    const container = document.getElementById("caseAiMessages");
    const row = document.createElement("div");
    row.className = `caseai-message-row ${role}`;
    if (animate) row.style.animation = "fadeIn 0.25s ease";

    const avatar = role === "user" ? "👤" : "✦";
    const formatted = formatMarkdown(content);

    row.innerHTML = `
      <div class="caseai-message-avatar">${avatar}</div>
      <div class="caseai-message-bubble">
        <div class="caseai-bubble-text">${formatted}</div>
        ${hasCursor ? `<span class="caseai-typing-cursor"></span>` : ""}
      </div>
    `;

    container.appendChild(row);

    if (role === "assistant" && content && !hasCursor) {
      addMessageActions(row, content);
    }

    return row;
  }

  function addMessageActions(messageRow, text) {
    const bubble = messageRow.querySelector(".caseai-message-bubble");
    if (!bubble || bubble.querySelector(".caseai-message-actions")) return;

    const actions = document.createElement("div");
    actions.className = "caseai-message-actions";
    actions.innerHTML = `
      <button class="caseai-copy-btn" title="Copy response to clipboard">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
        Copy
      </button>
    `;

    const copyBtn = actions.querySelector(".caseai-copy-btn");
    copyBtn.addEventListener("click", () => {
      navigator.clipboard.writeText(text).then(() => {
        copyBtn.innerHTML = `✓ Copied`;
        setTimeout(() => {
          copyBtn.innerHTML = `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy`;
        }, 1800);
      });
    });

    bubble.appendChild(actions);
  }

  /**
   * Resets chat history for current case
   */
  async function clearChat() {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const res = await fetch(`${window.API_BASE_URL || "/api"}/cases/${activeCaseId}/chat`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        renderWelcomeGreeting();
        if (window.showToast) window.showToast("Conversation history reset.", "info");
      }
    } catch (e) {
      console.error(e);
    }
  }

  /**
   * Export chat transcript
   */
  async function exportChat() {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const res = await fetch(`${window.API_BASE_URL || "/api"}/cases/${activeCaseId}/chat/export?format=txt`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        const blob = new Blob([data.content], { type: "text/plain;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = data.filename || `CaseAI_${activeCaseId.substring(0, 8)}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        if (window.showToast) window.showToast("Case transcript downloaded.", "success");
      }
    } catch (e) {
      if (window.showToast) window.showToast("Export failed.", "error");
    }
  }

  /**
   * Open modal allowing the user to select another case from their recent analyses
   */
  async function openCaseSwitcher() {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const res = await fetch(`${window.API_BASE_URL || "/api"}/cases/recent`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) return;

      const data = await res.json();
      const cases = data.cases || [];

      let modalHtml = `
        <div style="font-size:0.9rem; color:var(--text-secondary); margin-bottom:1rem;">
          Select an investigation from your history to load its complete case context into CaseAI:
        </div>
        <div style="max-height:300px; overflow-y:auto; display:flex; flex-direction:column; gap:0.5rem;">
          <div class="case-pick-item" data-id="global" style="padding:0.65rem 0.85rem; border:1px solid var(--border-subtle); border-radius:var(--radius-md); cursor:pointer; background:var(--bg-input);">
            <strong>🌐 Global Safety Assistant</strong>
            <div style="font-size:0.75rem; color:var(--text-muted);">Ask general questions about job scam tactics</div>
          </div>
          ${cases.map(c => `
            <div class="case-pick-item" data-id="${c.id}" style="padding:0.65rem 0.85rem; border:1px solid var(--border-subtle); border-radius:var(--radius-md); cursor:pointer; background:var(--bg-input);">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <strong>${escapeHTML(c.company_name)}</strong>
                <span style="font-size:0.75rem; color:${c.risk_level === 'High Risk' ? 'var(--risk-danger)' : 'var(--risk-warning)'};">${c.risk_level}</span>
              </div>
              <div style="font-size:0.75rem; color:var(--text-muted);">${escapeHTML(c.job_title)}</div>
            </div>
          `).join("")}
        </div>
      `;

      if (window.showModal) {
        window.showModal({
          title: "✦ Switch Case Investigation",
          content: modalHtml,
          confirmText: "Close",
          cancelText: null
        });

        // Bind clicks on cases
        setTimeout(() => {
          document.querySelectorAll(".case-pick-item").forEach(item => {
            item.addEventListener("click", () => {
              const selectedId = item.getAttribute("data-id");
              if (selectedId) {
                setCaseContext(selectedId, true);
                const modal = document.querySelector(".modal-backdrop");
                if (modal) modal.remove();
              }
            });
          });
        }, 50);
      }
    } catch (e) {
      console.error(e);
    }
  }

  function filterMessages(query) {
    const q = query.toLowerCase().trim();
    const rows = document.querySelectorAll(".caseai-message-row");
    rows.forEach(r => {
      if (!q) {
        r.style.display = "flex";
      } else {
        const text = r.textContent.toLowerCase();
        r.style.display = text.includes(q) ? "flex" : "none";
      }
    });
  }

  function scrollMessagesToBottom() {
    const container = document.getElementById("caseAiMessages");
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }

  function formatMarkdown(text) {
    if (!text) return "";
    let html = escapeHTML(text);

    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Code inline
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    // Headers
    html = html.replace(/^### (.*$)/gim, "<h4 style='font-size:0.95rem; margin:0.4rem 0;'>$1</h4>");
    html = html.replace(/^## (.*$)/gim, "<h3 style='font-size:1.05rem; margin:0.5rem 0;'>$1</h3>");
    // Bullet lists
    html = html.replace(/^\s*[-•]\s+(.*$)/gim, "<li>$1</li>");
    html = html.replace(/(<li>.*<\/li>)/gms, "<ul>$1</ul>");
    // Numbered lists
    html = html.replace(/^\s*\d+\.\s+(.*$)/gim, "<li>$1</li>");
    // Paragraph line breaks
    html = html.replace(/\n\n/g, "</p><p>");
    html = html.replace(/\n/g, "<br>");

    return `<p>${html}</p>`;
  }

  function escapeHTML(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Expose global API
  window.openCaseAI = openCaseAI;
  window.setCaseAIContext = setCaseContext;
})();
