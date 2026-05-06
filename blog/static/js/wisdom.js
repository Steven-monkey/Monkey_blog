/* ═══════════════════════════════════════════════════
   智慧箴言 交互逻辑
   ═══════════════════════════════════════════════════ */

const LOCAL_WISDOM_LIBRARY = [
    { text: "你生来就是一团火焰，不要甘心只做烟雾。", author: "非洲谚语" },
    { text: "你无法阻挡巨浪，但你可以学会冲浪。", author: "乔·卡巴金" },
    { text: "即使是最深的黑夜，也无法吞噬一颗星星。", author: "土耳其谚语" },
    { text: "所谓勇气，就是压力之下展现的优雅。", author: "海明威" },
    { text: "当你站在悬崖边，风会教你飞翔。", author: "尼采" },
    { text: "不要把心铺在道路上，要种在田野里。", author: "鲁米" },
    { text: "我来了，我看见了，我征服了。", author: "凯撒" },
    { text: "不要为已经打翻的牛奶哭泣。", author: "西方谚语" },
    { text: "你的伤口是光进入你内心的地方。", author: "鲁米" },
    { text: "活着，就是不断创造新的回忆。", author: "村上春树" }
];

const quoteTextEl = document.getElementById("quoteText");
const quoteAuthorEl = document.getElementById("quoteAuthor");
const localBtn = document.getElementById("localQuoteBtn");
const deepseekBtn = document.getElementById("deepseekQuoteBtn");
const quoteContainerDiv = document.getElementById("quoteContainer");
const sceneImageEl = document.getElementById("sceneImage");
const liveClockEl = document.getElementById("liveClock");
const apiStatusDisplay = document.getElementById("apiStatusDisplay");
const refreshStatusBtn = document.getElementById("refreshStatusBtn");
const statusTipEl = document.getElementById("statusTip");
const downloadImageBtn = document.getElementById("downloadImageBtn");
const downloadPosterBtn = document.getElementById("downloadPosterBtn");

let currentLocalIndex = -1;
let isFetchingDeepSeek = false;
let clockInterval = null;
let activeSyncTaskId = 0;

function updateClock() {
    const now = new Date();
    const weekdays = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    const hours = String(now.getHours()).padStart(2, "0");
    const minutes = String(now.getMinutes()).padStart(2, "0");
    const seconds = String(now.getSeconds()).padStart(2, "0");
    liveClockEl.textContent = year + "." + month + "." + day + " " + weekdays[now.getDay()] + " " + hours + ":" + minutes + ":" + seconds;
}

function applyQuoteAnimation() {
    quoteContainerDiv.classList.remove("quote-animate");
    void quoteContainerDiv.offsetWidth;
    quoteContainerDiv.classList.add("quote-animate");
    setTimeout(function() { quoteContainerDiv.classList.remove("quote-animate"); }, 350);
}

function displayQuote(text, author) {
    quoteTextEl.textContent = text;
    quoteAuthorEl.innerHTML = '<span class="author-prefix">——</span> ' + (author || "未知来源");
    applyQuoteAnimation();
}

function updateSceneImage(url) {
    if (!url) return;
    sceneImageEl.src = url;
}

function preloadImage(url) {
    return new Promise(function(resolve, reject) {
        if (!url) {
            reject(new Error("图片地址为空"));
            return;
        }
        const img = new Image();
        img.onload = function() { resolve(url); };
        img.onerror = function() { reject(new Error("图片加载失败")); };
        img.src = url;
    });
}

async function loadBackgroundByQuote(text, author) {
    try {
        const params = new URLSearchParams({ text: text || "", author: author || "" });
        const res = await fetch("/api/wisdom/background?" + params.toString());
        if (!res.ok) throw new Error("HTTP " + res.status);
        const data = await res.json();
        return data && data.image_url ? data.image_url : "";
    } catch (error) {
        console.error("请求 /api/wisdom/background 失败:", error);
        return "";
    }
}

async function applyQuoteWithSyncedImage(config) {
    const taskId = ++activeSyncTaskId;
    setStatus(config.loadingMessage || "正在同步生成箴言和背景图...");
    let finalImageUrl = config.imageUrl;
    if (!finalImageUrl) {
        finalImageUrl = await loadBackgroundByQuote(config.text, config.author);
    }
    if (!finalImageUrl) {
        throw new Error("未获取到背景图地址");
    }
    await preloadImage(finalImageUrl);
    if (taskId !== activeSyncTaskId) return;
    updateSceneImage(finalImageUrl);
    displayQuote(config.text, config.author);
}

function downloadCurrentImage() {
    const imageUrl = sceneImageEl && sceneImageEl.src ? sceneImageEl.src : "";
    if (!imageUrl) {
        setStatus("当前暂无可下载的背景图。", true);
        return;
    }
    const link = document.createElement("a");
    link.href = "/api/wisdom/download-image?url=" + encodeURIComponent(imageUrl);
    link.click();
    setStatus("正在下载当前背景图...");
}

function wrapCanvasText(ctx, text, maxWidth) {
    const chars = Array.from(text || "");
    const lines = [];
    let line = "";
    for (const ch of chars) {
        const testLine = line + ch;
        if (ctx.measureText(testLine).width > maxWidth && line) {
            lines.push(line);
            line = ch;
        } else {
            line = testLine;
        }
    }
    if (line) lines.push(line);
    return lines;
}

function loadImage(url) {
    return new Promise(function(resolve, reject) {
        const img = new Image();
        img.onload = function() { resolve(img); };
        img.onerror = reject;
        img.src = url;
    });
}

async function downloadPoster() {
    const imageUrl = sceneImageEl && sceneImageEl.src ? sceneImageEl.src : "";
    const quoteText = quoteTextEl && quoteTextEl.textContent ? quoteTextEl.textContent.trim() : "";
    const quoteAuthor = quoteAuthorEl && quoteAuthorEl.textContent ? quoteAuthorEl.textContent.replace(/^——\s*/, "").trim() : "未知来源";
    if (!imageUrl || !quoteText) {
        setStatus("当前内容不足，无法生成海报。", true);
        return;
    }
    try {
        setStatus("正在生成箴言海报...");
        const parsed = new URL(imageUrl, window.location.origin);
        const isSameOrigin = parsed.origin === window.location.origin;
        const imageSourceUrl = isSameOrigin
            ? parsed.pathname + parsed.search
            : "/api/wisdom/image-proxy?url=" + encodeURIComponent(imageUrl);
        const bg = await loadImage(imageSourceUrl);

        const canvas = document.createElement("canvas");
        canvas.width = 1080;
        canvas.height = 1920;
        const ctx = canvas.getContext("2d");

        ctx.drawImage(bg, 0, 0, canvas.width, canvas.height);

        const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
        gradient.addColorStop(0, "rgba(10, 18, 33, 0.20)");
        gradient.addColorStop(0.55, "rgba(10, 18, 33, 0.34)");
        gradient.addColorStop(1, "rgba(10, 18, 33, 0.70)");
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        const contentPadding = 96;
        const textMaxWidth = canvas.width - contentPadding * 2;
        const quoteFontSize = 56;
        const lineHeight = 84;
        ctx.fillStyle = "#f4f7ff";
        ctx.textBaseline = "top";
        ctx.font = '600 ' + quoteFontSize + 'px "Segoe UI", "Noto Sans SC", sans-serif';
        const quoteLines = wrapCanvasText(ctx, quoteText, textMaxWidth);
        const blockHeight = quoteLines.length * lineHeight + 96;
        let y = canvas.height - blockHeight - 200;

        quoteLines.forEach(function(line) {
            ctx.fillText(line, contentPadding, y);
            y += lineHeight;
        });
        ctx.font = '400 38px "Segoe UI", "Noto Sans SC", sans-serif';
        ctx.fillStyle = "rgba(240, 245, 255, 0.95)";
        ctx.fillText("—— " + quoteAuthor, contentPadding, y + 24);
        ctx.font = '400 24px "Segoe UI", "Noto Sans SC", sans-serif';
        ctx.fillStyle = "rgba(223, 232, 252, 0.9)";
        ctx.fillText("智慧箴言 · 1080x1920", contentPadding, canvas.height - 64);

        const link = document.createElement("a");
        const ts = new Date().toISOString().replace(/[-:]/g, "").slice(0, 15);
        link.download = "wisdom-poster-" + ts + ".png";
        link.href = canvas.toDataURL("image/png");
        link.click();
        setStatus("箴言海报已生成并开始下载。");
    } catch (error) {
        console.error("生成海报失败:", error);
        setStatus("海报生成失败，请稍后重试。", true);
    }
}

function setStatus(message, isError) {
    statusTipEl.textContent = message || "";
    statusTipEl.classList.toggle("error", Boolean(isError));
}

function getRandomLocalWisdom() {
    let newIndex = Math.floor(Math.random() * LOCAL_WISDOM_LIBRARY.length);
    if (LOCAL_WISDOM_LIBRARY.length > 1 && newIndex === currentLocalIndex) {
        newIndex = (newIndex + 1) % LOCAL_WISDOM_LIBRARY.length;
    }
    currentLocalIndex = newIndex;
    return LOCAL_WISDOM_LIBRARY[currentLocalIndex];
}

function handleLocalQuote() {
    const wisdom = getRandomLocalWisdom();
    applyQuoteWithSyncedImage({
        text: wisdom.text,
        author: wisdom.author,
        loadingMessage: "正在同步生成本地箴言和背景图..."
    })
        .then(function() { setStatus("已同步更新本地箴言与背景图。"); })
        .catch(function(error) {
            displayQuote(wisdom.text, wisdom.author);
            setStatus("背景图同步失败：" + (error.message || "未知错误"), true);
        });
}

async function refreshApiStatus() {
    try {
        const res = await fetch("/api/llm/status");
        if (!res.ok) throw new Error("HTTP " + res.status);
        const data = await res.json();
        if (data.configured) {
            const quoteModel = data.quote_model || data.model || "chat-model";
            const imageModel = data.image_model || "default";
            const imageProvider = data.image_provider || "openai-compatible";
            const imageKeyTag = data.image_configured ? "已配置Key" : "未配置Key";
            apiStatusDisplay.textContent = "🔮 箴言模型：" + quoteModel + " ｜ 🎨 生图：" + imageProvider + "/" + imageModel + "（" + imageKeyTag + "）";
            apiStatusDisplay.style.color = "#2a6b47";
        } else {
            apiStatusDisplay.textContent = "⚠️ AI 引擎：后端未完成配置";
            apiStatusDisplay.style.color = "#a5613a";
        }
    } catch (error) {
        apiStatusDisplay.textContent = "❌ 无法获取后端配置状态";
        apiStatusDisplay.style.color = "#b64949";
        console.error("读取状态失败:", error);
    }
}

async function handleDeepSeekQuote() {
    if (isFetchingDeepSeek) return;
    isFetchingDeepSeek = true;
    const originalText = deepseekBtn.innerHTML;
    deepseekBtn.innerHTML = '🌐 沉思中 <span class="wisdom-loader"></span>';
    deepseekBtn.disabled = true;
    setStatus("正在向后端请求 AI 灵感内容...");
    try {
        const res = await fetch("/api/llm/wisdom");
        if (!res.ok) throw new Error("HTTP " + res.status);
        const data = await res.json();
        if (!data || !data.text) throw new Error("返回内容缺少 text 字段");
        const finalAuthor = data.author || "AI 灵感引擎";
        await applyQuoteWithSyncedImage({
            text: data.text,
            author: finalAuthor,
            imageUrl: data.image_url || "",
            loadingMessage: "正在同步生成 AI 箴言与背景图..."
        });
        if (data.source === "fallback") {
            setStatus(data.note || "AI 服务暂不可用，已回退到本地内容。", true);
        } else {
            setStatus("已同步生成 AI 箴言与背景图。");
        }
    } catch (error) {
        setStatus("调用失败：" + (error.message || "未知错误"), true);
        console.error("请求 /api/llm/wisdom 失败:", error);
    } finally {
        isFetchingDeepSeek = false;
        deepseekBtn.innerHTML = originalText;
        deepseekBtn.disabled = false;
    }
}

function init() {
    updateClock();
    clockInterval = setInterval(updateClock, 1000);
    handleLocalQuote();
    refreshApiStatus();
    localBtn.addEventListener("click", handleLocalQuote);
    deepseekBtn.addEventListener("click", handleDeepSeekQuote);
    downloadImageBtn.addEventListener("click", downloadCurrentImage);
    downloadPosterBtn.addEventListener("click", downloadPoster);
    refreshStatusBtn.addEventListener("click", refreshApiStatus);
    window.addEventListener("beforeunload", function() { clearInterval(clockInterval); });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
} else {
    init();
}
