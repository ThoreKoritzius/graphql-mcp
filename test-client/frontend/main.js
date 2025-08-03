const chatWindow = document.getElementById('chat-window');
const input = document.getElementById('input');
const sendBtn = document.getElementById('send');
const chatForm = document.getElementById('chat-form');
const clearBtn = document.getElementById('clear-history');
const streamToggle = document.getElementById('stream-toggle');
const streamToggleLabel = document.getElementById('stream-toggle-label');
const LS_KEY = "mcpgraphql_openai_chat";
let streamingMode = false;
let isAwaiting = false;

// Stream toggle logic
streamToggle.addEventListener('click', () => {
  streamingMode = !streamingMode;
  streamToggleLabel.textContent = streamingMode ? "On" : "Off";
});

// ----- HISTORY UTILS -----
function getHistory() {
  try {
    return JSON.parse(localStorage.getItem(LS_KEY) || "[]") || [];
  } catch (e) { return []; }
}
function setHistory(history) {
  localStorage.setItem(LS_KEY, JSON.stringify(history));
}
function clearHistory() {
  localStorage.removeItem(LS_KEY);
}

// ----- RENDERING -----
function renderMarkdown(text) {
  return marked.parse(text ?? "", {sanitize: true});
}

// Tool Call Rendering
function renderToolCalls(tool_calls) {
  if (!Array.isArray(tool_calls) || !tool_calls.length) return '';
  return tool_calls.map((t, i) => `
   <div class="tool-call">
<div class="tool-meta" style="display: flex; align-items: flex-start; gap: 1em;">
  <span class="tool-title" style="font-weight: bold;">${escapeHtml(t.tool)}</span>
  <span class="tool-input-label" style="min-width:60px;">Input:</span>
  <pre class="tool-input" style="margin:0; padding:2px 6px; min-width:100px; max-width:350px; overflow-x:auto; white-space: pre; background:#f9f9f9; border-radius:2px; border:1px solid #eee; flex:1 1 auto; display:inline-block; vertical-align:middle;">
${escapeHtml(typeof t.tool_input === "string" ? t.tool_input : JSON.stringify(t.tool_input))}
  </pre>
  <button class="obs-expand" data-i="${i}" style="margin-left:8px;">Show Observation</button>
</div>
<pre class="observation" style="display:none;">${escapeHtml(t.observation || "")}</pre>
</div>
  `).join('');
}

function escapeHtml(str) {
  if (typeof str !== "string") return "";
  return str.replace(/[&<>'"]/g, ch => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }[ch]));
}

function renderHistory() {
  chatWindow.innerHTML = '';
  getHistory().forEach(msg => appendMsg(msg.role, msg.content, false));
  if (isAwaiting) showTyping();
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

// ------- APPEND/UPDATE MSGS -------
function appendMsg(role, text, save = true) {
  let row = document.createElement('div');
  row.className = "msg-row " + (role === "assistant" ? "assistant" : "user");
  let col = document.createElement('div');
  col.style.display = "flex";
  col.style.flexDirection = "column";
  col.style.alignItems = "flex-start";
  col.style.width = "100%";
  let bubble = document.createElement('div');
  bubble.className = "msg-bubble";
  let message, tool_calls;
  try {
    message = JSON.parse(text);
    if (typeof message === "object" && message.result !== undefined) {
      bubble.innerHTML = renderMarkdown(message.result ?? "");
      tool_calls = message.tool_calls;
    } else {
      bubble.innerHTML = renderMarkdown(text);
    }
  } catch {
    bubble.innerHTML = renderMarkdown(text);
  }
  if (role === "assistant" && Array.isArray(tool_calls) && tool_calls.length) {
    const toolsDiv = document.createElement("div");
    toolsDiv.className = "tool-calls-wrapper";
    toolsDiv.innerHTML = renderToolCalls(tool_calls);
    col.appendChild(toolsDiv);
  }
  col.appendChild(bubble);
  row.appendChild(col);
  chatWindow.appendChild(row);
  if (save) {
    let h = getHistory();
    h.push({role, content: text});
    setHistory(h);
  }
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

// ----- Expand/collapse for observations -----
chatWindow.addEventListener('click', function(e) {
  if (e.target.matches('.obs-expand')) {
    const toolCall = e.target.closest('.tool-call');
    const obs = toolCall.querySelector('.observation');
    if (obs.style.display === "none") {
      obs.style.display = "block";
      e.target.textContent = "Hide Observation";
    } else {
      obs.style.display = "none";
      e.target.textContent = "Show Observation";
    }
  }
});

// ----- TYPING -----
let typingNode = null;
function showTyping() {
  removeTyping();
  let row = document.createElement('div');
  row.className = "typing-row";
  let typingBubble = document.createElement('div');
  typingBubble.className = "typing";
  for (let i = 0; i < 3; ++i) {
    let dot = document.createElement('div');
    dot.className = 'dot';
    typingBubble.appendChild(dot);
  }
  row.appendChild(typingBubble);
  chatWindow.appendChild(row);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  typingNode = row;
}
function removeTyping() {
  if (typingNode && typingNode.parentNode) {
    typingNode.parentNode.removeChild(typingNode);
    typingNode = null;
  } else {
    let el = chatWindow.querySelector('.typing-row');
    if (el && el.parentNode) el.parentNode.removeChild(el);
    typingNode = null;
  }
}

// ======== SEND MESSAGE & LIVE UPDATE LOGIC ========
async function sendMsg(event) {
  if (event) event.preventDefault();
  const text = input.value.trim();
  if (!text || isAwaiting) return;
  isAwaiting = true;
  input.value = '';
  input.disabled = true;
  sendBtn.disabled = true;
  appendMsg("user", text);
  showTyping();

  let payload = {
    question: text,
    history: getHistory(),
  };

  let toolCalls = [];
  let finalResult = '';
  let receivedAny = false;
  let assistantMsgIdx = null;

  function updateAssistantMsg() {
    removeTyping();
    if (assistantMsgIdx === null) {
      appendMsg(
        "assistant",
        JSON.stringify({ result: finalResult, tool_calls: toolCalls })
      );
      assistantMsgIdx = getHistory().length - 1;
    } else {
      let msgRows = chatWindow.getElementsByClassName("msg-row assistant");
      if (!msgRows.length) return;
      let lastMsg = msgRows[msgRows.length - 1];
      let bubble = lastMsg.querySelector(".msg-bubble");
      bubble.innerHTML = renderMarkdown(finalResult ?? "");

      let existingTools = lastMsg.querySelector(".tool-calls-wrapper");
      if (toolCalls.length > 0) {
        if (existingTools) {
          existingTools.innerHTML = renderToolCalls(toolCalls);
        } else {
          let toolsDiv = document.createElement("div");
          toolsDiv.className = "tool-calls-wrapper";
          toolsDiv.innerHTML = renderToolCalls(toolCalls);
          lastMsg.insertBefore(toolsDiv, bubble);
        }
      } else {
        if (existingTools) existingTools.remove();
      }

      let h = getHistory();
      h[assistantMsgIdx] = {
        role: "assistant",
        content: JSON.stringify({ result: finalResult, tool_calls: toolCalls })
      };
      setHistory(h);
    }
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }

  try {
    if (streamingMode) {
      // --- STREAMING MODE ---
      const res = await fetch('/ask?stream=true', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.body) throw new Error('No stream supported.');
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let parts = buffer.split('\n\n');
        buffer = parts.pop();
        for (const part of parts) {
          const line = part.trim();
          if (line.startsWith('data:')) {
            try {
              const msg = JSON.parse(line.slice(5).trim());
              receivedAny = true;
              if (msg.type === "tool_call") {
                toolCalls.push({
                  tool: msg.tool,
                  tool_input: msg.tool_input,
                  observation: msg.observation
                });
                updateAssistantMsg();
              } else if (msg.type === "result") {
                finalResult = msg.result;
                updateAssistantMsg();
              }
            } catch (e) { }
          }
        }
      }
    } else {
      // --- NON-STREAMING MODE ---
      const res = await fetch('/ask?stream=false', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      finalResult = data.result || '';
      if (Array.isArray(data.tool_calls)) {
        toolCalls = data.tool_calls;
      } else {
        toolCalls = [];
      }
      updateAssistantMsg();
      receivedAny = true;
    }
    removeTyping();
    if (!receivedAny) appendMsg("assistant", "⚠️ No response");
  } catch (e) {
    removeTyping();
    appendMsg("assistant", "⚠️ Error: " + e.message);
  }
  isAwaiting = false;
  input.disabled = false;
  sendBtn.disabled = false;
  input.focus();
}

// ======= EVENT BINDINGS =======
chatForm.addEventListener('submit', sendMsg);
input.addEventListener('keydown', function (e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMsg();
  }
});

// Clear and reload on click
clearBtn.addEventListener('click', function () {
  if (confirm("Clear entire chat history?")) {
    clearHistory();
    renderHistory();
    input.focus();
  }
});

// INITIALIZE
renderHistory();
input.focus();