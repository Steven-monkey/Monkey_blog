/* ═══════════════════════════════════════════════════
   AI 阅读助手 + 内容推荐 交互逻辑
   依赖：模板中需先设置 CONTENT_TYPE 和 CONTENT_SLUG
   ═══════════════════════════════════════════════════ */

const chatMessages = document.getElementById("chatMessages");
const chatInput = document.getElementById("chatInput");
const chatSendBtn = document.getElementById("chatSendBtn");
let chatHistory = [];

function toggleChat() {
    document.getElementById("aiChatPanel").classList.toggle("open");
}

function addMessage(role, text) {
    const div = document.createElement("div");
    div.className = "ai-chat-msg " + role;
    div.textContent = text;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return div;
}

async function sendChat() {
    const msg = chatInput.value.trim();
    if (!msg) return;

    addMessage("user", msg);
    chatInput.value = "";
    chatSendBtn.disabled = true;

    const loadingMsg = addMessage("assistant", "思考中...");
    loadingMsg.querySelector(".loading-dots") || (loadingMsg.innerHTML = '<span class="loading-dots">思考中</span>');

    try {
        const res = await fetch("/api/ai/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                content_type: CONTENT_TYPE,
                slug: CONTENT_SLUG,
                message: msg,
                history: chatHistory,
            }),
        });

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let fullText = "";
        let assistantMsg = null;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split("\n");
            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                const data = line.slice(6).trim();
                if (data === "[DONE]") continue;
                try {
                    const parsed = JSON.parse(data);
                    if (parsed.type === "token") {
                        if (!assistantMsg) {
                            loadingMsg.remove();
                            assistantMsg = addMessage("assistant", parsed.content);
                        } else {
                            assistantMsg.textContent += parsed.content;
                        }
                        fullText += parsed.content;
                    } else if (parsed.type === "error") {
                        loadingMsg.textContent = "❌ " + parsed.content;
                    }
                } catch (e) {}
            }
        }

        chatHistory.push({ role: "user", content: msg });
        if (fullText) {
            chatHistory.push({ role: "assistant", content: fullText });
        }
        if (chatHistory.length > 12) {
            chatHistory = chatHistory.slice(-12);
        }
    } catch (err) {
        loadingMsg.textContent = "❌ 请求失败: " + err.message;
    } finally {
        chatSendBtn.disabled = false;
    }
}

// 加载推荐
async function loadRecommendations() {
    try {
        const res = await fetch("/api/ai/recommend", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ type: CONTENT_TYPE, slug: CONTENT_SLUG, limit: 3 }),
        });
        const data = await res.json();
        if (data.items && data.items.length > 0) {
            const section = document.getElementById("recommendSection");
            const list = document.getElementById("recommendList");
            section.style.display = "block";
            list.innerHTML = data.items.map(function(item) {
                const url = item.type === "note" ? "/notes/" + item.slug : "/projects/" + item.slug;
                const reason = item.ai_reason ? '<div class="ai-reason">' + item.ai_reason + '</div>' : "";
                return '<div class="recommend-card">'
                    + '<h4><a href="' + url + '">' + item.title + '</a></h4>'
                    + '<p>' + item.summary + '</p>'
                    + reason
                    + '</div>';
            }).join("");
        }
    } catch (e) {
        console.error("加载推荐失败:", e);
    }
}

loadRecommendations();
