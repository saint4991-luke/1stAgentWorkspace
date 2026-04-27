// 蝦米 Agent Web UI - 虛擬人對話頁面 (vh-chat.js)

let currentPath = '/';
let currentSessionId = null;
let currentConfigId = null;  // 記錄當前 Session 的 configId（風格）

// 處理按鍵
function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        send();
    }
}

// 載入 Session 列表（只載入虛擬人 Session）
async function loadSessions() {
    try {
        const response = await fetch('/api/sessions');
        const data = await response.json();
        const sessions = data.sessions || [];
        
        // 過濾：只顯示有 persona_id 的 Session（虛擬人對話）
        const vhSessions = sessions.filter(s => s.metadata?.vh_char_config?.persona_id);
        
        const sessionList = document.getElementById('session-list');
        
        if (vhSessions.length === 0) {
            sessionList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">💭</div>
                    <div>還沒有虛擬人對話記錄</div>
                    <div style="font-size:12px;margin-top:10px;">選擇風格並點擊「新增」開始對話</div>
                </div>
            `;
            return;
        }
        
        sessionList.innerHTML = '';
        vhSessions.forEach(session => {
            const item = document.createElement('div');
            item.className = `session-item ${session.session_id === currentSessionId ? 'active' : ''}`;
            
            const personaId = session.metadata?.vh_char_config?.persona_id;
            
            item.onclick = (e) => {
                if (!e.target.matches('button')) selectSession(session.session_id, personaId);
            };
            
            const time = session.last_active ? new Date(session.last_active).toLocaleString('zh-TW', {
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            }) : '剛剛';
            
            const styleName = personaId ? (personaId === 'ubichan' ? '🎭 優必醬' : personaId === 'nurse' ? '👩‍⚕️ 護士姐姐' : '📝 一般') : '📝 一般';
            
            item.innerHTML = `
                <div class="session-name">${styleName} 的對話</div>
                <div class="session-meta">
                    <span>📝 ${session.message_count || 0} 則</span>
                    <span>${time}</span>
                </div>
            `;
            sessionList.appendChild(item);
        });
    } catch (error) {
        console.error('載入 Session 失敗:', error);
        document.getElementById('session-list').innerHTML = `
            <div class="empty-state">
                <div>載入失敗</div>
            </div>
        `;
    }
}

// 創建新 Session（虛擬人）
async function createNewSession() {
    const styleSelect = document.getElementById('vh-style-select');
    const configId = styleSelect.value;
    
    try {
        const response = await fetch('/api/sessions', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                prefix: configId.toUpperCase(),
                metadata: {
                    vh_char_config: {
                        persona_id: configId,
                        character_version: 'v2.0'
                    }
                }
            })
        });
        
        if (!response.ok) throw new Error('創建失敗');
        
        const session = await response.json();
        const sessionId = session.session_id;
        
        selectSession(sessionId, configId);
        loadSessions();
    } catch (error) {
        alert(`創建失敗：${error.message}`);
    }
}

// 選擇 Session
function selectSession(sessionId, configId) {
    currentSessionId = sessionId;
    currentConfigId = configId;
    
    // 清空聊天區域
    const chat = document.getElementById('chat');
    chat.innerHTML = '';
    
    // 顯示歡迎訊息
    const styleName = configId ? (configId === 'ubichan' ? '🎭 優必醬' : configId === 'nurse' ? '👩‍⚕️ 護士姐姐' : '📝 一般') : '📝 一般';
    chat.innerHTML = `
        <div class="message shrimp">
            🦐 這是與 **${styleName}** 的對話
            <br><br>
            開始聊天吧！
        </div>
    `;
    
    chat.scrollTop = chat.scrollHeight;
    document.getElementById('status-session').textContent = `💬 ${styleName}`;
    loadSessions(); // 更新 active 狀態
}

// 刪除 Session
async function deleteSession(sessionId) {
    if (!confirm('確定要刪除這個對話記錄嗎？此操作無法復原。')) return;
    
    try {
        const response = await fetch(`/api/sessions/${sessionId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) throw new Error('刪除失敗');
        
        if (sessionId === currentSessionId) {
            currentSessionId = null;
            currentConfigId = null;
            document.getElementById('chat').innerHTML = `
                <div class="message shrimp">
                    🦐 你好！這是 **虛擬人對話** 頁面
                </div>
            `;
            document.getElementById('status-session').textContent = '💬 未選擇 Session';
        }
        
        loadSessions();
    } catch (error) {
        alert(`刪除失敗：${error.message}`);
    }
}

// 載入檔案列表
async function loadFiles(path = '/') {
    try {
        const response = await fetch(`/files?path=${encodeURIComponent(path)}`);
        const files = await response.json();
        
        const fileList = document.getElementById('file-list');
        const breadcrumb = document.getElementById('breadcrumb');
        const statusPath = document.getElementById('status-path');
        
        fileList.innerHTML = '';
        breadcrumb.textContent = '📍 /workspace' + (path !== '/' ? path : '');
        statusPath.textContent = '📁 /workspace' + (path !== '/' ? path : '');
        
        if (path !== '/') {
            const parentItem = document.createElement('div');
            parentItem.className = 'file-item folder';
            parentItem.innerHTML = '<span class="file-icon">📁</span><span class="file-name">..</span>';
            parentItem.onclick = () => loadFiles(getParentPath(path));
            fileList.appendChild(parentItem);
        }
        
        const folders = files.filter(f => f.type === 'folder').sort((a, b) => a.name.localeCompare(b.name));
        const regularFiles = files.filter(f => f.type === 'file').sort((a, b) => a.name.localeCompare(b.name));
        
        [...folders, ...regularFiles].forEach(file => {
            const item = document.createElement('div');
            item.className = `file-item ${file.type === 'folder' ? 'folder' : ''}`;
            const icon = file.type === 'folder' ? '📁' : getFileIcon(file.name);
            
            item.innerHTML = `
                <span class="file-icon">${icon}</span>
                <span class="file-name">${file.name}</span>
                <div class="file-actions">
                    ${file.type === 'file' ? `<button class="btn-preview" onclick="previewFile('${file.path}')">預覽</button>` : ''}
                    ${file.type === 'file' ? `<button class="btn-download" onclick="downloadFile('${file.path}')">下載</button>` : ''}
                    <button class="btn-delete" onclick="deleteFile('${file.path}')">刪除</button>
                </div>
            `;
            
            if (file.type === 'folder') {
                item.onclick = (e) => {
                    if (!e.target.matches('button')) loadFiles(file.path);
                };
            }
            fileList.appendChild(item);
        });
        
        currentPath = path;
    } catch (error) {
        console.error('載入檔案失敗:', error);
    }
}

function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    const icons = {
        'txt': '📄', 'md': '📝', 'py': '🐍', 'js': '📜',
        'xlsx': '📊', 'xls': '📊', 'csv': '📊',
        'docx': '📘', 'doc': '📘',
        'pdf': '📕', 'pptx': '📊',
        'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️',
        'zip': '📦', 'rar': '📦'
    };
    return icons[ext] || '📄';
}

function getParentPath(path) {
    return path.substring(0, path.lastIndexOf('/')) || '/';
}

// 聊天功能（含時間戳記）
async function send() {
    const input = document.getElementById('input');
    const chat = document.getElementById('chat');
    const message = input.value.trim();
    if (!message) return;
    
    // 時間戳記功能
    const sendTime = new Date();
    const timestamp = sendTime.toLocaleTimeString('zh-TW', { hour12: false });
    
    // 顯示用戶訊息（帶時間戳）
    chat.innerHTML += `<div class="message user">${escapeHtml(message)}<br><small style="opacity:0.7;font-size:11px;margin-top:5px;display:block;">${timestamp}</small></div>`;
    input.value = '';
    chat.scrollTop = chat.scrollHeight;
    
    const loadingId = 'loading-' + Date.now();
    const startTime = Date.now();
    chat.innerHTML += `<div class="message shrimp" id="${loadingId}"><span class="loading"></span> 思考中...</div>`;
    chat.scrollTop = chat.scrollHeight;
    
    try {
        const requestBody = {
            messages: [
                {role: "user", content: message}
            ]
        };
        
        // 如果有 Session，附加 session_id 和 configId
        if (currentSessionId) {
            requestBody.session_id = currentSessionId;
            if (currentConfigId) {
                requestBody.config_id = currentConfigId;
            }
        }
        
        // ⭐ 後端固定使用 STREAM 模式（不需要發送 stream 參數）
        // requestBody.stream = true; // 已移除，後端統一使用 STREAM
        
        const response = await fetch('/api/vh/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) throw new Error('回應失敗');
        
        // 創建回應訊息元素
        const loadingEl = document.getElementById(loadingId);
        if (loadingEl) loadingEl.remove();
        
        const responseTime = new Date(Date.now()).toLocaleTimeString('zh-TW', { hour12: false });
        const responseDiv = document.createElement('div');
        responseDiv.className = 'message shrimp';
        responseDiv.innerHTML = `<small style="opacity:0.7;font-size:11px;">${responseTime}</small><div id="response-content-${loadingId}"></div>`;
        chat.appendChild(responseDiv);
        
        const contentDiv = document.getElementById(`response-content-${loadingId}`);
        let fullContent = '';
        let completeData = null;
        
        // 處理 STREAM 回應
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        while (true) {
            const {done, value} = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const jsonStr = line.slice(6);
                    // ✅ UBICHAN v2.0: 跳過 [DONE] 標記（非 JSON）
                    if (jsonStr === '[DONE]') continue;
                    
                    const eventData = JSON.parse(jsonStr);
                    const eventType = eventData.event;
                    const eventPayload = eventData;  // ✅ v2.0: 扁平化，無需 .data
                    
                    if (eventType === 'text_chunk') {
                        fullContent += eventPayload.message || '';  // ✅ v2.0: chunk → message
                        contentDiv.innerHTML = formatResponse(fullContent);
                        chat.scrollTop = chat.scrollHeight;
                    } else if (eventType === 'done') {
                        completeData = eventPayload;  // ✅ v2.0: 扁平化
                    }
                }
            }
        }
        
        // 顯示統計資訊（如果有 Done 事件）
        if (completeData) {
            let statsHtml = `<br><small style="opacity:0.7;font-size:11px;margin-top:5px;display:block;">`;
            if (completeData.timing) {  // ✅ v2.0: timings → timing
                const t = completeData.timing;
                statsHtml += `📊 <b>時間分析</b>: `;
                statsHtml += `LLM 1(檢索):${t.rag_llm_ms||0}ms | 文件讀取:${t.file_read_ms||0}ms | RAG 總計:${t.rag_retrieve_ms||0}ms | `;
                statsHtml += `LLM 2(回應):${t.llm_call_ms||0}ms | 總計:${t.total_ms||0}ms`;
            }
            statsHtml += `</small>`;
            contentDiv.innerHTML += statsHtml;
        }
        
        chat.scrollTop = chat.scrollHeight;
        
        // 更新狀態欄
        const endTime = Date.now();
        const latency = endTime - startTime;
        document.getElementById('status-timestamp').textContent = `⏱️ ${latency}ms`;
        
        // 如果是新 Session，更新 currentSessionId
        if (!currentSessionId && completeData && completeData.session_id && completeData.session_id !== 'no_session') {
            currentSessionId = completeData.session_id;
            loadSessions();
        }
        
    } catch (error) {
        const loadingEl = document.getElementById(loadingId);
        if (loadingEl) loadingEl.remove();
        addSystemMessage(`❌ 錯誤：${error.message}`);
    }
}

function formatResponse(text) {
    if (!text) return '';
    return escapeHtml(text).replace(/\\n/g, '<br>');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function addSystemMessage(text) {
    const chat = document.getElementById('chat');
    chat.innerHTML += `<div class="message system">${text}</div>`;
    chat.scrollTop = chat.scrollHeight;
}

// 檔案預覽
async function previewFile(path) {
    try {
        const response = await fetch(`/files/preview?path=${encodeURIComponent(path)}`);
        const data = await response.json();
        
        if (data.error) throw new Error(data.error);
        
        document.getElementById('preview-title').textContent = '📄 ' + path.split('/').pop();
        document.getElementById('preview-body').textContent = data.content;
        document.getElementById('preview').style.display = 'block';
    } catch (error) {
        alert(`預覽失敗：${error.message}`);
    }
}

function closePreview() {
    document.getElementById('preview').style.display = 'none';
}

document.getElementById('preview').addEventListener('click', function(e) {
    if (e.target === this) closePreview();
});

// 下載檔案
function downloadFile(path) {
    window.location.href = `/files/download?path=${encodeURIComponent(path)}`;
}

// 刪除檔案
async function deleteFile(path) {
    if (!confirm(`確定要刪除 "${path.split('/').pop()}" 嗎？`)) return;
    
    try {
        const response = await fetch(`/files/delete?path=${encodeURIComponent(path)}`, {method: 'DELETE'});
        if (!response.ok) throw new Error('刪除失敗');
        
        addSystemMessage(`✅ 已刪除：${path.split('/').pop()}`);
        loadFiles(currentPath);
    } catch (error) {
        alert(`刪除失敗：${error.message}`);
    }
}

// 上傳檔案
async function uploadFile(input) {
    const file = input.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('path', currentPath);
    
    addSystemMessage(`⬆️ 上傳中：${file.name}`);
    
    try {
        const response = await fetch('/files/upload', {method: 'POST', body: formData});
        if (!response.ok) throw new Error('上傳失敗');
        
        addSystemMessage(`✅ 上傳成功：${file.name}`);
        loadFiles(currentPath);
    } catch (error) {
        addSystemMessage(`❌ 上傳失敗：${error.message}`);
    }
    
    input.value = '';
}

// 檢查連線
async function checkHealth() {
    try {
        const response = await fetch('/api/health');
        if (response.ok) {
            const data = await response.json();
            document.getElementById('status-connection').textContent = '🟢 已連線';
            if (data.session_support) {
                console.log('✅ Session 功能已啟用');
            } else {
                console.log('⚠️ Session 功能不可用');
            }
        } else {
            throw new Error('健康檢查失敗');
        }
    } catch (error) {
        document.getElementById('status-connection').textContent = '🔴 離線';
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    loadSessions();
    loadFiles();
    checkHealth();
    setInterval(checkHealth, 30000);
    setInterval(loadSessions, 30000);
});

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closePreview();
    }
});
