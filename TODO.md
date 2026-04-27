# AgentShrimp TODO

**這是一個做事的筆記本** — 只記錄待辦事項，已完成項目會定期清除  
**最後更新：** 2026-04-15  
**狀態：** 進行中

---

## 🔴 高優先級（應該實作）

### #0. LLM1 性能波動問題

**問題：** LLM1 回應時間波動極大（535ms ~ 4401ms）

**測試數據：**
| 請求 | LLM1 時間 | RAG 總計 | 回應長度 |
|------|----------|---------|---------|
| 「你是誰」 | 535ms | 0ms | 短句 ✅ |
| 「你會什麼」 | 3045ms | 0ms | ~50 字 ❌ |
| 「介紹一下自己」 | 4401ms | 2ms | ~100 字 ❌ |

**觀察：**
- RAG 不是瓶頸（0-2ms）✅
- LLM1 時間與回應長度**強相關**
- Prompt 限制「不超過 20 字」**未被嚴格遵守**

**建議解決方案：**
1. **更強的 Prompt 限制** - 強調「超過 20 字會導致系統錯誤」
2. **後處理截斷** - 如果超長，強制截斷
3. **使用更小的 LLM 模型** - 安撫話語不需要大模型

**檔案：**
- `agent/agent-api-streaming.py` (LLM1 Prompt)
- `agent/virtual_human/api.py` (LLM1 Prompt)

---

### #0-1. 快速回應長度配置化

**需求：** 快速回應的長度要可以 config

**建議實作：**
```python
# 配置文件或環境變數
QUICK_RESPONSE_MAX_LENGTH = 20  # 預設 20 字

# 在 Prompt 中使用
prompt = f"""回應：[一句話，**嚴格不超過 {QUICK_RESPONSE_MAX_LENGTH} 字**]"""

# 後處理截斷
if len(comforting_words) > QUICK_RESPONSE_MAX_LENGTH:
    comforting_words = comforting_words[:QUICK_RESPONSE_MAX_LENGTH] + "..."
```

**配置位置：**
- 環境變數：`QUICK_RESPONSE_MAX_LENGTH=20`
- 配置文件：`config.py` 或 `settings.json`
- 或根據不同 persona 設定不同長度（虛擬人可能允許稍長）

---

### #1. 中性 Fallback 語句優化

**問題：** 目前只有一句「我收到了，讓我處理一下。」

**建議：**
```python
FALLBACK_RESPONSES = [
    "我收到了，讓我處理一下。",
    "好的，我知道了。",
    "明白了，正在處理。",
    "收到，讓我來看看。",
]
comforting_words = random.choice(FALLBACK_RESPONSES)
```

**原因：** 避免每次都一樣，增加自然感

**檔案：**
- `agent/agent-api-streaming.py`
- `agent/virtual_human/api.py`

---

## 🟡 中優先級（可以實作）

### #3. 移除棄用的 API 端點

**問題：** 以下 API 端點偏離原始設計，應移除：

1. `POST /vh/sessions/{session_id}/switch` - 切換虛擬人
2. `GET /vh/sessions/{session_id}/stats` - Session 統計
3. `GET /vh/sessions/stats` - 所有 Sessions 統計

**替代方案：**
- 切換虛擬人 → 直接創建新的 Session（`POST /vh/sessions`）
- Session 統計 → 無需替代（非核心功能）

**涉及檔案：**
- `agent/virtual_human/api.py` (第 801-900 行)
- `docs/02_specs/01_AGENT_API_SPEC.md`（已加註⚠️）

---

### #4-1. LLM1 風格導入（/chat 端點）

**問題：** 目前 `/chat` 端點的 LLM1 永遠是「知識庫檢索助手」風格，安撫語都是「我幫你查查」

**現狀：**
- `/chat`：中立助手（無風格）
- `/vh/chat`：已導入虛擬人風格（可愛、親切語氣）

**決策：** 暫時保持中立助手風格，詳細風格問題之後處理

**TODO：** 未來考慮為 `/chat` 添加風格選項

**建議架構：**
```python
# 風格配置
persona_style = request.persona_style or "neutral"  # neutral, professional, friendly

if persona_style == "professional":
    comforting_examples = ["我來為您查詢相關資訊", "讓我為您整理資料"]
elif persona_style == "friendly":
    comforting_examples = ["我幫你看看～", "來找找看喔"]
else:  # neutral
    comforting_examples = ["我幫你查查", "讓我看看相關資料"]
```

**相關檔案：**
- `agent/agent-api-streaming.py` (LLM1 Prompt)
- `agent/virtual_human/api.py` (已實作)

---

### #5. 重試機制（針對暫時性錯誤）

**問題：** LLM1 呼叫失敗時沒有重試

**建議：**
```python
async def call_llm1_with_retry(prompt, max_retries=2):
    for attempt in range(max_retries):
        try:
            result = await llm_client.chat.completions.create(...)
            if result and result.choices:
                return result.choices[0].message.content
        except (asyncio.TimeoutError, ConnectionError):
            if attempt < max_retries - 1:
                await asyncio.sleep(0.5 * (2 ** attempt))
    return None
```

**適用場景：**
- 網路抖動
- API 瞬斷
- Rate limit (429)

---

### #6. 降級策略（針對格式解析失敗）

**問題：** LLM 返回格式錯誤時直接放棄

**建議：**
```python
# 第 1 層：正常解析
if not comforting_words:
    # 第 2 層：簡化 Prompt 重試
    simple_prompt = f"用戶輸入：{user_message}\n請用一句話友善回應："
    simple_result = await llm_client.chat.completions.create(...)
    comforting_words = simple_result.choices[0].message.content
```

**適用場景：**
- LLM 不理解格式要求
- Prompt 太複雜

---

### #7. Prompt 強化

**問題：** 目前 Prompt 可能不夠嚴格

**建議：** 使用 XML 標籤分隔 + 負面範例

```python
llm1_prompt = f"""<|system|>
你是一個知識庫檢索助手。你的任務是：
1. 閱讀用戶輸入
2. 判斷是否需要查詢知識庫
3. 生成一句友善的安撫話語
4. 列出相關文件（如果有）

<|format_rules|>
**你必須嚴格按照以下格式回應，否則系統會錯誤：**

回應：[你的安撫話語]
相關文件：["file1.txt", "file2.txt"]

**格式規則（違反任何一條都會導致錯誤）：**
1. 第一行必須以「回應：」開頭
2. 第二行必須以「相關文件：」開頭
3. 只能有這兩行，不能有其他內容
4. 相關文件必須是 JSON 陣列格式
5. 如果沒有相關文件，必須返回：相關文件：[]

<|examples|>
**正確範例：**
用戶輸入：「優必達有哪些產品？」
回應：我幫你查查優必達的產品資訊！
相關文件：["products.txt"]

用戶輸入：「今天心情不好」
回應：我收到了，讓我聽你說說看。
相關文件：[]

**錯誤範例（不要這樣做）：**
❌ 回應：我幫你查查
   相關文件：["products.txt"]
   還需要其他幫助嗎？  ← 不要添加額外內容

<|user_input|>
用戶輸入：{user_message}

<|response|>
（現在請按照格式規則回應）
"""
```

**檔案：**
- `agent/agent-api-streaming.py` (第 633 行)
- `agent/virtual_human/api.py` (第 136 行)

---

## 🟢 低優先級（未來考慮）

### #8. Token Usage 追蹤

**建議：** 記錄 LLM1 的 Token 使用量

```python
if hasattr(llm_result, 'usage'):
    print(f"📊 LLM1 Token Usage: {llm_result.usage}")
```

---

### #9. 性能監控

**建議：** 添加 Prometheus/Grafana 監控

**指標：**
- `llm1_call_count` - LLM1 呼叫次數
- `llm1_error_count` - LLM1 錯誤次數
- `llm1_latency_ms` - LLM1 延遲（毫秒）
- `llm1_fallback_rate` - Fallback 使用率

---

### #10. 單元測試

**建議：** 為 LLM1 呼叫邏輯添加單元測試

**測試場景：**
- 正常回應（有格式）
- 空回應
- None 回應
- 格式錯誤回應
- 網路錯誤
- API 錯誤

**檔案：** `tests/test_llm1_service.py`

---

## 📊 決策樹

```
LLM1 呼叫
   │
   ▼
┌─────────────────┐
│ 系統層面失敗？   │ ──YES──→ 中性 fallback（硬編碼可接受）
│ (網路/API/服務) │
└─────────────────┘
   │ NO
   ▼
┌─────────────────┐
│ 內容層面失敗？   │ ──YES──→ 智能降級（提取/重試）
│ (格式/空內容)   │
└─────────────────┘
   │ NO
   ▼
┌─────────────────┐
│ 程式碼錯誤？     │ ──YES──→ 修復 Bug（不應該發生）
│ (None/變數)     │
└─────────────────┘
   │ NO
   ▼
✅ 成功返回安撫話語
```

---

## 📝 測試清單

### 基本功能測試

- [ ] `/chat` 端點正常回應
- [ ] `/vh/chat` 端點正常回應
- [ ] 快速回應在 < 1 秒內發送
- [ ] 中性 fallback 正確顯示

### 錯誤場景測試

- [ ] LLM 返回 None
- [ ] LLM 返回空字串
- [ ] LLM 返回格式錯誤
- [ ] 網路超時
- [ ] API 錯誤 (500, 429)

### 用戶場景測試

- [ ] 查詢類問題（「優必達有哪些產品？」）
- [ ] 聊天類問題（「今天心情不好」）
- [ ] 指令類問題（「幫我寫一封郵件」）

---

**文檔結束**
