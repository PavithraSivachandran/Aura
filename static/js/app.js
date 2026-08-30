(() => {
  const $ = (id) => document.getElementById(id);
  const state = {
    settings: {
      onboarded: false,
      user_name: "",
      mode: "pro",
      auto_speak: false,
      location: "Jaipur",
      has_pin: false,
    },
    conversations: [],
    currentId: null,
    messages: [],
    sending: false,
    rec: null,
    recChunks: [],
    recStream: null,
    recTimer: null,
    recStart: 0,
    recTranscript: "",
    pendingMode: "pro",
    recognition: null,
    talking: false,
    talkLoop: false,
  };

  const ICONS = {
    play: `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>`,
    pause: `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 5h4v14H6zm8 0h4v14h-4z"/></svg>`,
    speaker: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 10v4h4l5 4V6L8 10H4z"/><path d="M16 9a4 4 0 010 6"/></svg>`,
    copy: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M4 16V6a2 2 0 012-2h10"/></svg>`,
  };

  const PROMPTS = {
    pro: [
      { t: "Weather in Jaipur", s: "Live conditions" },
      { t: "Who is the Prime Minister of India?", s: "Look up a fact" },
      { t: "Convert 100 USD to INR", s: "Markets" },
      { t: "Define serendipity", s: "Dictionary" },
    ],
    kids: [
      { t: "Tell me a story", s: "Bedtime magic" },
      { t: "Why is the sky blue?", s: "Curious why" },
      { t: "Animal facts", s: "Meet a creature" },
      { t: "Quiz time", s: "Play with Spark" },
    ],
  };

  async function api(path, opts = {}) {
    const res = await fetch(path, {
      headers: opts.body instanceof FormData ? {} : { "Content-Type": "application/json" },
      ...opts,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || "Request failed");
    return data;
  }

  function toast(msg) {
    const el = $("toast");
    el.textContent = msg;
    el.classList.remove("hidden");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.add("hidden"), 2800);
  }

  function applyTheme() {
    const kids = state.settings.mode === "kids";
    document.documentElement.dataset.theme = kids ? "kids" : "pro";
    document.querySelector('meta[name="theme-color"]').content = kids ? "#fff3e6" : "#080b14";
    $("brand-tag").textContent = kids ? "Kids Mode" : "Professional";
    $("user-mode-label").textContent = kids ? "Kids world" : "Professional";
    $("mode-toggle-label").textContent = kids ? "Exit Kids" : "Kids Mode";
    $("empty-art").src = kids ? "/static/img/spark-mascot.png" : "/static/img/logo.png";
    $("talk-art").src = kids ? "/static/img/spark-mascot.png" : "/static/img/logo.png";
    const name = state.settings.user_name || (kids ? "explorer" : "there");
    $("empty-hello").textContent = kids ? `Hi ${name}! What shall we explore?` : `How can I help, ${name}?`;
    $("empty-copy").textContent = kids
      ? "Ask Spark for a story, a quiz, or why the sky is blue."
      : "Ask a question, tap the mic, or send a voice note.";
    $("chat-sub").textContent = kids ? "Stories, quizzes & kind answers" : "Ask anything, or hold a voice note";
    $("fineprint").textContent = kids
      ? "Spark keeps things kind. Ask a parent before sharing personal details."
      : "Aura looks up live facts. Chats stay in your local database.";
    $("input").placeholder = kids ? "Ask Spark…" : "Message Aura…";
    const letter = (state.settings.user_name || "You").trim().charAt(0).toUpperCase();
    $("user-letter").textContent = letter || "Y";
    $("user-label").textContent = state.settings.user_name || "You";
    renderPrompts();
  }

  function renderPrompts() {
    const box = $("prompt-grid");
    box.innerHTML = "";
    PROMPTS[state.settings.mode === "kids" ? "kids" : "pro"].forEach((p) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "prompt-card";
      b.innerHTML = `${escapeHtml(p.t)}<small>${escapeHtml(p.s)}</small>`;
      b.addEventListener("click", () => sendText(p.t));
      box.appendChild(b);
    });
  }

  function groupConversations(list) {
    const groups = { Today: [], Yesterday: [], Previous: [] };
    const now = new Date();
    const startOfDay = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
    list.forEach((c) => {
      const t = new Date(c.updated_at).getTime();
      const diff = startOfDay(now) - startOfDay(new Date(c.updated_at));
      if (diff <= 0) groups.Today.push(c);
      else if (diff <= 86400000) groups.Yesterday.push(c);
      else groups.Previous.push(c);
    });
    return groups;
  }

  function renderConversations() {
    const q = ($("search").value || "").toLowerCase();
    const list = state.conversations.filter(
      (c) => c.mode === state.settings.mode && (!q || (c.title || "").toLowerCase().includes(q))
    );
    const nav = $("convo-list");
    nav.innerHTML = "";
    const grouped = groupConversations(list);
    Object.entries(grouped).forEach(([label, items]) => {
      if (!items.length) return;
      const h = document.createElement("div");
      h.className = "convo-group";
      h.textContent = label;
      nav.appendChild(h);
      items.forEach((c) => {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "convo-item" + (c.id === state.currentId ? " active" : "");
        b.innerHTML = `<span></span><span class="x" title="Delete">×</span>`;
        b.querySelector("span").textContent = c.title || "New chat";
        b.addEventListener("click", (e) => {
          if (e.target.classList.contains("x")) return;
          openConversation(c.id);
          $("sidebar").classList.remove("open");
        });
        b.querySelector(".x").addEventListener("click", async (e) => {
          e.stopPropagation();
          await api("/api/conversations/" + c.id, { method: "DELETE" });
          if (state.currentId === c.id) resetThread();
          await refreshConvos();
        });
        nav.appendChild(b);
      });
    });
  }

  function resetThread() {
    state.currentId = null;
    state.messages = [];
    $("messages").innerHTML = "";
    $("empty").classList.remove("hidden");
    $("chat-title").textContent = "New chat";
    $("suggestions").innerHTML = "";
  }

  async function refreshConvos() {
    state.conversations = await api("/api/conversations?mode=" + state.settings.mode);
    renderConversations();
  }

  async function openConversation(id) {
    const data = await api("/api/conversations/" + id);
    state.currentId = id;
    state.messages = data.messages || [];
    $("chat-title").textContent = data.conversation.title;
    $("empty").classList.toggle("hidden", state.messages.length > 0);
    $("messages").innerHTML = "";
    state.messages.forEach((m) => appendMessage(m, false));
    scrollThread();
    renderConversations();
    const last = [...state.messages].reverse().find((m) => m.role === "assistant");
    showSuggestions((last && last.meta && last.meta.suggestions) || []);
  }

  function showSuggestions(items) {
    const box = $("suggestions");
    box.innerHTML = "";
    (items || []).forEach((t) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "sug";
      b.textContent = t;
      b.addEventListener("click", () => sendText(t));
      box.appendChild(b);
    });
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderMarkdown(raw) {
    let s = escapeHtml(raw);
    s = s.replace(/```([\s\S]*?)```/g, (_, code) => `<pre><code>${code}</code></pre>`);
    s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/\*([^*]+)\*/g, "<em>$1</em>");
    s = s.replace(/_([^_]+)_/g, "<em>$1</em>");
    s = s.replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    s = s.replace(/^(?:_Source: )(https?:[^\s_]+)_?$/gm, '<a href="$1" target="_blank" rel="noopener">Source</a>');
    s = s.replace(/(^|\n)(?:- |\• )(.+)/g, "$1<li>$2</li>");
    s = s.replace(/(<li>[\s\S]+?<\/li>)/g, "<ul>$1</ul>");
    s = s.split(/\n{2,}/).map((p) => {
      if (p.startsWith("<ul>") || p.startsWith("<pre>")) return p;
      return `<p>${p.replace(/\n/g, "<br>")}</p>`;
    }).join("");
    return s;
  }

  function formatDuration(ms) {
    const s = Math.max(0, Math.round((ms || 0) / 1000));
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  }

  function waveformHtml(peaks, count = 22) {
    let arr = [];
    try {
      arr = typeof peaks === "string" ? JSON.parse(peaks) : peaks || [];
    } catch {
      arr = [];
    }
    if (!arr.length) arr = Array.from({ length: count }, (_, i) => 0.35 + (Math.sin(i) + 1) / 4);
    while (arr.length < count) arr = arr.concat(arr);
    return arr.slice(0, count).map((v) => `<i style="height:${Math.max(4, Math.min(26, v * 26))}px"></i>`).join("");
  }

  function appendMessage(msg, animate = true) {
    const wrap = document.createElement("article");
    wrap.className = "msg " + msg.role;
    const kids = state.settings.mode === "kids";
    const face = document.createElement(msg.role === "assistant" ? "img" : "div");
    face.className = "face";
    if (msg.role === "assistant") {
      face.src = kids ? "/static/img/spark-mascot.png" : "/static/img/aura-avatar.png";
      face.alt = kids ? "Spark" : "Aura";
    } else {
      face.textContent = (state.settings.user_name || "Y").charAt(0).toUpperCase();
    }

    const col = document.createElement("div");
    const bubble = document.createElement("div");
    bubble.className = "bubble";

    if (msg.msg_type === "voice" && msg.audio_file) {
      bubble.appendChild(voiceCard(msg));
      if (msg.content && msg.content !== "Voice note") {
        const cap = document.createElement("p");
        cap.style.marginTop = "8px";
        cap.style.opacity = "0.9";
        cap.style.fontSize = "13px";
        cap.textContent = msg.content;
        bubble.appendChild(cap);
      }
    } else {
      bubble.innerHTML = renderMarkdown(msg.content || "");
    }

    const meta = document.createElement("div");
    meta.className = "meta-row";
    const time = document.createElement("span");
    try {
      time.textContent = new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      time.textContent = "";
    }
    meta.appendChild(time);
    if (msg.role === "assistant") {
      const sp = document.createElement("button");
      sp.type = "button";
      sp.title = "Play voice";
      sp.innerHTML = ICONS.speaker;
      sp.addEventListener("click", () => speak(msg.content || ""));
      meta.appendChild(sp);
      const cp = document.createElement("button");
      cp.type = "button";
      cp.title = "Copy";
      cp.innerHTML = ICONS.copy;
      cp.addEventListener("click", async () => {
        await navigator.clipboard.writeText(msg.content || "");
        toast("Copied");
      });
      meta.appendChild(cp);
    }
    col.appendChild(bubble);
    col.appendChild(meta);
    if (msg.role === "user") {
      wrap.appendChild(col);
      wrap.appendChild(face);
    } else {
      wrap.appendChild(face);
      wrap.appendChild(col);
    }
    $("messages").appendChild(wrap);
    $("empty").classList.add("hidden");
    if (animate) scrollThread();
  }

  function voiceCard(msg) {
    const card = document.createElement("div");
    card.className = "voice-card";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "play";
    btn.innerHTML = ICONS.play;
    const audio = new Audio("/api/media/" + msg.audio_file);
    const bars = document.createElement("div");
    bars.className = "bars";
    bars.innerHTML = waveformHtml(msg.meta && msg.meta.peaks);
    const dur = document.createElement("span");
    dur.textContent = formatDuration(msg.duration_ms);
    audio.addEventListener("timeupdate", () => {
      dur.textContent = formatDuration(audio.currentTime * 1000) + " / " + formatDuration(msg.duration_ms);
    });
    audio.addEventListener("ended", () => {
      btn.innerHTML = ICONS.play;
      dur.textContent = formatDuration(msg.duration_ms);
    });
    btn.addEventListener("click", () => {
      if (audio.paused) {
        document.querySelectorAll("audio").forEach((a) => a.pause());
        audio.play();
        btn.innerHTML = ICONS.pause;
      } else {
        audio.pause();
        btn.innerHTML = ICONS.play;
      }
    });
    card.appendChild(btn);
    card.appendChild(bars);
    card.appendChild(dur);
    card.appendChild(audio);
    audio.style.display = "none";
    return card;
  }

  function scrollThread() {
    const t = $("thread");
    t.scrollTo({ top: t.scrollHeight, behavior: "smooth" });
  }

  function thinkingEl() {
    const wrap = document.createElement("article");
    wrap.className = "msg assistant";
    wrap.id = "thinking";
    const img = document.createElement("img");
    img.className = "face";
    img.src = state.settings.mode === "kids" ? "/static/img/spark-mascot.png" : "/static/img/aura-avatar.png";
    const bubble = document.createElement("div");
    bubble.className = "bubble thinking";
    bubble.innerHTML = "<span></span><span></span><span></span>";
    wrap.appendChild(img);
    wrap.appendChild(bubble);
    $("messages").appendChild(wrap);
    $("empty").classList.add("hidden");
    scrollThread();
  }

  function speak(text) {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text.replace(/[*_`#]/g, " "));
    u.rate = state.settings.mode === "kids" ? 0.92 : 1;
    u.pitch = state.settings.mode === "kids" ? 1.12 : 1;
    const voices = speechSynthesis.getVoices();
    const prefer = state.settings.mode === "kids"
      ? voices.find((v) => /female|samantha|google uk.*female/i.test(v.name))
      : voices.find((v) => /google|samantha|daniel|rishi/i.test(v.name) && /en/i.test(v.lang));
    if (prefer) u.voice = prefer;
    u.lang = "en-IN";
    speechSynthesis.speak(u);
    return new Promise((resolve) => {
      u.onend = resolve;
      u.onerror = resolve;
    });
  }

  async function sendText(text, source = "text") {
    const content = (text || "").trim();
    if (!content || state.sending) return;
    state.sending = true;
    $("input").value = "";
    autosize();
    $("suggestions").innerHTML = "";
    const optimistic = {
      role: "user",
      content,
      msg_type: source === "voice" ? "voice" : "text",
      created_at: new Date().toISOString(),
      meta: {},
    };
    appendMessage(optimistic);
    thinkingEl();
    try {
      const data = await api("/api/chat", {
        method: "POST",
        body: JSON.stringify({
          content,
          mode: state.settings.mode,
          conversation_id: state.currentId,
          client_meta: { source },
        }),
      });
      $("thinking")?.remove();
      state.currentId = data.conversation.id;
      $("chat-title").textContent = data.conversation.title;
      appendMessage(data.assistant_message);
      showSuggestions((data.assistant_message.meta || {}).suggestions || []);
      if (state.settings.auto_speak || source === "voice" || state.talkLoop) {
        await speak(data.assistant_message.content);
      }
      await refreshConvos();
      return data.assistant_message.content;
    } catch (err) {
      $("thinking")?.remove();
      toast(err.message || "Could not reply");
    } finally {
      state.sending = false;
    }
  }

  function getRecognition() {
    const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Ctor) return null;
    const rec = new Ctor();
    rec.lang = "en-IN";
    rec.interimResults = true;
    rec.continuous = true;
    return rec;
  }

  function toggleSTT() {
    if (state.recognition) {
      state.recognition.stop();
      state.recognition = null;
      $("stt-btn").classList.remove("listening");
      return;
    }
    const rec = getRecognition();
    if (!rec) {
      toast("Speech recognition needs Chrome or Edge over HTTPS");
      return;
    }
    let finalText = $("input").value;
    rec.onresult = (e) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) finalText = (finalText + " " + t).trim();
        else interim += t;
      }
      $("input").value = (finalText + " " + interim).trim();
      autosize();
    };
    rec.onend = () => {
      $("stt-btn").classList.remove("listening");
      state.recognition = null;
    };
    rec.onerror = () => {
      $("stt-btn").classList.remove("listening");
      state.recognition = null;
    };
    state.recognition = rec;
    rec.start();
    $("stt-btn").classList.add("listening");
  }

  async function startNote() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      state.recStream = stream;
      state.recChunks = [];
      state.recTranscript = "";
      const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const rec = new MediaRecorder(stream);
      state.rec = rec;
      rec.ondataavailable = (e) => {
        if (e.data.size) state.recChunks.push(e.data);
      };
      rec.start();
      state.recStart = Date.now();
      $("composer").classList.add("hidden");
      $("recorder").classList.remove("hidden");
      paintWave();
      state.recTimer = setInterval(() => {
        $("rec-time").textContent = formatDuration(Date.now() - state.recStart);
      }, 250);
      const sr = getRecognition();
      if (sr) {
        sr.continuous = true;
        sr.onresult = (e) => {
          let out = "";
          for (let i = 0; i < e.results.length; i++) out += e.results[i][0].transcript + " ";
          state.recTranscript = out.trim();
          $("rec-live").textContent = state.recTranscript;
        };
        try {
          sr.start();
          state.recognition = sr;
        } catch {
          /* already started */
        }
      }
    } catch {
      toast("Microphone permission is needed for voice notes");
    }
  }

  function paintWave() {
    const wave = $("wave");
    wave.innerHTML = "";
    for (let i = 0; i < 18; i++) {
      const b = document.createElement("b");
      b.style.height = 8 + Math.random() * 18 + "px";
      b.style.animationDelay = i * 0.05 + "s";
      wave.appendChild(b);
    }
  }

  function stopNote(send) {
    return new Promise((resolve) => {
      const rec = state.rec;
      if (!rec) return resolve(null);
      rec.onstop = () => resolve(new Blob(state.recChunks, { type: rec.mimeType || "audio/webm" }));
      if (rec.state !== "inactive") rec.stop();
      else resolve(null);
    }).then(async (blob) => {
      clearInterval(state.recTimer);
      state.recStream?.getTracks().forEach((t) => t.stop());
      try {
        state.recognition?.stop();
      } catch {}
      state.recognition = null;
      $("recorder").classList.add("hidden");
      $("composer").classList.remove("hidden");
      $("rec-live").textContent = "";
      state.rec = null;
      if (!send || !blob || blob.size < 200) return;
      await sendVoice(blob, state.recTranscript, Date.now() - state.recStart);
    });
  }

  async function sendVoice(blob, transcript, durationMs) {
    if (state.sending) return;
    state.sending = true;
    $("suggestions").innerHTML = "";
    const localUrl = URL.createObjectURL(blob);
    appendMessage({
      role: "user",
      content: transcript || "Voice note",
      msg_type: "voice",
      audio_file: null,
      duration_ms: durationMs,
      created_at: new Date().toISOString(),
      meta: {},
      _local: localUrl,
    });
    // Replace placeholder visually by injecting audio via last voice card if needed
    thinkingEl();
    try {
      const fd = new FormData();
      fd.append("audio", blob, "note.webm");
      fd.append("transcript", transcript || "");
      fd.append("mode", state.settings.mode);
      fd.append("duration_ms", String(durationMs));
      if (state.currentId) fd.append("conversation_id", String(state.currentId));
      const data = await api("/api/chat/voice", { method: "POST", body: fd });
      $("thinking")?.remove();
      // reload conversation for proper audio urls
      state.currentId = data.conversation.id;
      await openConversation(state.currentId);
      const reply = data.assistant_message;
      showSuggestions((reply.meta || {}).suggestions || []);
      if (state.settings.auto_speak) await speak(reply.content);
    } catch (err) {
      $("thinking")?.remove();
      toast(err.message || "Voice note failed");
    } finally {
      state.sending = false;
    }
  }

  function autosize() {
    const el = $("input");
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  }

  async function switchMode(next) {
    if (next === state.settings.mode) return;
    if (state.settings.mode === "kids" && next === "pro" && state.settings.has_pin) {
      openPin(() => actuallySetMode("pro"));
      return;
    }
    await actuallySetMode(next);
  }

  async function actuallySetMode(mode) {
    await api("/api/settings", { method: "PUT", body: JSON.stringify({ mode }) });
    state.settings.mode = mode;
    applyTheme();
    resetThread();
    await refreshConvos();
  }

  function openPin(onOk) {
    $("pin-modal").classList.remove("hidden");
    $("pin-error").classList.add("hidden");
    $("pin-input").value = "";
    $("pin-input").focus();
    $("pin-ok").onclick = async () => {
      try {
        await api("/api/pin/verify", { method: "POST", body: JSON.stringify({ pin: $("pin-input").value }) });
        $("pin-modal").classList.add("hidden");
        onOk();
      } catch {
        $("pin-error").classList.remove("hidden");
      }
    };
  }

  async function openTalk() {
    $("talk").classList.remove("hidden");
    $("talk-status").textContent = "Tap to speak";
    $("talk-script").textContent = "";
    $("talk-orb").classList.remove("listening", "speaking");
  }

  function closeTalk() {
    state.talkLoop = false;
    try {
      state.recognition?.stop();
    } catch {}
    speechSynthesis.cancel();
    $("talk").classList.add("hidden");
  }

  async function talkListen() {
    const rec = getRecognition();
    if (!rec) {
      toast("Talk mode needs Chrome or Edge");
      return;
    }
    state.talkLoop = true;
    rec.continuous = false;
    rec.interimResults = true;
    $("talk-status").textContent = "Listening…";
    $("talk-orb").classList.add("listening");
    $("talk-orb").classList.remove("speaking");
    let finalText = "";
    rec.onresult = (e) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) finalText += e.results[i][0].transcript;
        else interim += e.results[i][0].transcript;
      }
      $("talk-script").textContent = finalText || interim;
    };
    rec.onerror = () => {
      $("talk-orb").classList.remove("listening");
      $("talk-status").textContent = "Try again";
    };
    rec.onend = async () => {
      $("talk-orb").classList.remove("listening");
      const said = ($("talk-script").textContent || "").trim();
      if (!said || !state.talkLoop) {
        $("talk-status").textContent = "Tap to speak";
        return;
      }
      $("talk-status").textContent = "Thinking…";
      const reply = await sendText(said, "voice");
      if (!state.talkLoop) return;
      $("talk-status").textContent = "Speaking…";
      $("talk-orb").classList.add("speaking");
      $("talk-script").textContent = reply || "";
      await speak(reply || "");
      $("talk-orb").classList.remove("speaking");
      if (state.talkLoop) talkListen();
    };
    state.recognition = rec;
    rec.start();
  }

  function showSettings() {
    $("settings").classList.remove("hidden");
    $("set-name").value = state.settings.user_name || "";
    $("set-city").value = state.settings.location || "Jaipur";
    $("set-speak").checked = !!state.settings.auto_speak;
    $("set-pin").value = "";
  }

  async function boot() {
    const data = await api("/api/bootstrap");
    state.settings = data.settings;
    state.conversations = data.conversations || [];
    applyTheme();
    if (!state.settings.onboarded) {
      $("onboard").classList.remove("hidden");
      $("shell").classList.add("hidden");
    } else {
      $("onboard").classList.add("hidden");
      $("shell").classList.remove("hidden");
      renderConversations();
    }
  }

  function goStep(n) {
    document.querySelectorAll(".step").forEach((s) => s.classList.toggle("active", Number(s.dataset.step) === n));
  }

  $("ob-start").addEventListener("click", () => goStep(1));
  $("ob-name-next").addEventListener("click", () => {
    if (!$("ob-name").value.trim()) {
      $("ob-name").focus();
      return;
    }
    goStep(2);
  });
  document.querySelectorAll(".mode-card").forEach((card) => {
    card.addEventListener("click", () => {
      document.querySelectorAll(".mode-card").forEach((c) => c.classList.remove("selected"));
      card.classList.add("selected");
      state.pendingMode = card.dataset.mode;
    });
  });
  $("ob-mode-next").addEventListener("click", async () => {
    if (state.pendingMode === "kids") {
      goStep(3);
      return;
    }
    await finishOnboard("");
  });
  $("ob-skip-pin").addEventListener("click", () => finishOnboard(""));
  $("ob-save-pin").addEventListener("click", () => finishOnboard($("ob-pin").value.trim()));

  async function finishOnboard(pin) {
    const payload = {
      user_name: $("ob-name").value.trim(),
      mode: state.pendingMode,
      location: "Jaipur",
      pin,
    };
    const data = await api("/api/onboard", { method: "POST", body: JSON.stringify(payload) });
    state.settings = data.settings;
    applyTheme();
    $("onboard").classList.add("hidden");
    $("shell").classList.remove("hidden");
    await refreshConvos();
  }

  $("composer").addEventListener("submit", (e) => {
    e.preventDefault();
    sendText($("input").value);
  });
  $("input").addEventListener("input", autosize);
  $("input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendText($("input").value);
    }
  });
  $("stt-btn").addEventListener("click", toggleSTT);
  $("note-btn").addEventListener("click", startNote);
  $("rec-cancel").addEventListener("click", () => stopNote(false));
  $("rec-send").addEventListener("click", () => stopNote(true));
  $("new-chat").addEventListener("click", () => {
    resetThread();
    renderConversations();
    $("sidebar").classList.remove("open");
    $("input").focus();
  });
  $("search").addEventListener("input", renderConversations);
  $("open-sidebar").addEventListener("click", () => $("sidebar").classList.add("open"));
  $("close-sidebar").addEventListener("click", () => $("sidebar").classList.remove("open"));
  $("mode-toggle").addEventListener("click", () => {
    switchMode(state.settings.mode === "kids" ? "pro" : "kids");
  });
  $("talk-btn").addEventListener("click", openTalk);
  $("talk-close").addEventListener("click", closeTalk);
  $("talk-hold").addEventListener("click", talkListen);
  $("settings-btn").addEventListener("click", showSettings);
  $("open-settings").addEventListener("click", showSettings);
  $("settings-close").addEventListener("click", () => $("settings").classList.add("hidden"));
  $("pin-cancel").addEventListener("click", () => $("pin-modal").classList.add("hidden"));
  $("save-settings").addEventListener("click", async () => {
    const data = await api("/api/settings", {
      method: "PUT",
      body: JSON.stringify({
        user_name: $("set-name").value.trim(),
        location: $("set-city").value.trim() || "Jaipur",
        auto_speak: $("set-speak").checked,
      }),
    });
    state.settings = { ...state.settings, ...data.settings };
    applyTheme();
    $("settings").classList.add("hidden");
    toast("Saved");
  });
  $("save-pin").addEventListener("click", async () => {
    const pin = $("set-pin").value.trim();
    if (!/^\d{4}$/.test(pin)) {
      toast("Use 4 digits");
      return;
    }
    await api("/api/pin", { method: "POST", body: JSON.stringify({ pin }) });
    state.settings.has_pin = true;
    toast("PIN saved");
  });
  $("reset-all").addEventListener("click", async () => {
    if (!confirm("Erase all chats, voice notes, and settings?")) return;
    await api("/api/reset", { method: "POST", body: "{}" });
    location.reload();
  });

  window.speechSynthesis?.getVoices();
  boot().catch((err) => toast(err.message || "Could not start Aura"));
})();
