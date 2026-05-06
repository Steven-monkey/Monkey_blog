/* ═══════════════════════════════════════════════════
   AI 智能搜索 交互逻辑
   ═══════════════════════════════════════════════════ */

const searchInput = document.getElementById("searchInput");
const searchBtn = document.getElementById("searchBtn");
const resultsArea = document.getElementById("resultsArea");

async function doSearch() {
    const query = searchInput.value.trim();
    if (!query) return;

    searchBtn.disabled = true;
    searchBtn.textContent = "搜索中...";
    resultsArea.innerHTML = '<div class="loading"><span class="spinner"></span>AI 正在分析你的问题...</div>';

    try {
        const res = await fetch("/api/ai/search", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ q: query }),
        });
        const data = await res.json();

        if (data.error) {
            resultsArea.innerHTML = '<div class="empty-state"><p>❌ ' + data.error + '</p></div>';
            return;
        }

        renderResults(data);
    } catch (err) {
        resultsArea.innerHTML = '<div class="empty-state"><p>❌ 请求失败: ' + err.message + '</p></div>';
    } finally {
        searchBtn.disabled = false;
        searchBtn.textContent = "搜索";
    }
}

function renderResults(data) {
    let html = "";

    if (data.keywords && data.keywords.length > 0) {
        html += '<div class="keywords">';
        html += '<span style="font-size:0.8rem;color:var(--muted);margin-right:0.3rem">关键词:</span>';
        data.keywords.forEach(function(kw) {
            html += '<span class="kw">' + escapeHtml(kw) + '</span>';
        });
        html += "</div>";
    }

    if (data.ai_summary) {
        html += '<div class="ai-summary"><strong>💡 AI 解读：</strong>' + escapeHtml(data.ai_summary) + '</div>';
    }

    if (!data.results || data.results.length === 0) {
        html += '<div class="empty-state"><div class="icon">🔍</div><p>没有找到相关内容，试试换个说法？</p></div>';
    } else {
        data.results.forEach(function(r) {
            const typeLabel = r.type === "note" ? "笔记" : "项目";
            const typeClass = r.type;
            const url = r.type === "note" ? "/notes/" + r.slug : "/projects/" + r.slug;
            const tagsHtml = r.tags && r.tags.length > 0
                ? '<div class="tags">' + r.tags.map(function(t) { return '<span class="tag">' + escapeHtml(t) + '</span>'; }).join("") + '</div>'
                : "";
            const aiExpHtml = r.ai_explanation
                ? '<div class="ai-explanation">' + escapeHtml(r.ai_explanation) + '</div>'
                : "";

            html += '<div class="result-item">'
                + '<span class="type-badge ' + typeClass + '">' + typeLabel + '</span>'
                + '<h3><a href="' + url + '">' + escapeHtml(r.title) + '</a></h3>'
                + '<p class="summary">' + escapeHtml(r.summary) + '</p>'
                + tagsHtml
                + aiExpHtml
                + '</div>';
        });
    }

    resultsArea.innerHTML = html;
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}
