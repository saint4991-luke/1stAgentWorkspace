# 📝 虛擬人輸出規格 v2.0

**版本：** v2.0  
**日期：** 2026-04-15  
**適用範圍：** 所有虛擬人角色（優必醬、衛教護士等）

---

## 🎯 概述

本規格定義虛擬人輸出的統一格式，讓前端可以：
- **解析情緒** - 根據情緒標籤調整表情
- **解析語言** - 根據語言標籤選擇 TTS 聲音
- **逐句顯示** - 根據斷句符號分割句子
- **流式渲染** - 支持逐字顯示效果

---

## 📐 格式定義

### 完整格式

```
<!-- emotion>{emotion}</emotion -->
<!-- lang>{lang}</lang -->

回覆內容第 1 句<sbr>
回覆內容第 2 句<sbr>
回覆內容第 3 句<sbr>
```

### 欄位說明

| 欄位 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `<!-- emotion>{emotion}</emotion -->` | ✅ | 情緒標籤 | `happy`, `neutral`, `sad` |
| `<!-- lang>{lang}</lang -->` | ✅ | 語言標籤 | `tw (zh)`, `en`, `ja` |
| `<sbr>` | ✅ | 斷句符號 | 每句結尾 |
| 空行 | ✅ | 分隔標籤與內容 | 標籤後空一行 |

---

## 🎭 Actions（完整的 7 個 Actions）

本規格定義 **7 個 Actions**，LLM 應根據對話內容生成適當的 Actions。

| Action | 格式 | 說明 |
|--------|------|------|
| `emotion` | `<!-- emotion>{emotion}</emotion -->` | 情緒標籤 |
| `lang` | `<!-- lang>{lang}</lang -->` | 語言標籤 |
| `options` | `<!-- options>{json}</options -->` | 選項按鈕 |
| `link` | `<!-- link>{url}</link -->` | 連結 |
| `image` | `<!-- image>{url}</image -->` | 圖片 |
| `bg` | `<!-- bg>{color_or_url}</bg -->` | 背景 |
| `displayonly` | `<!-- displayonly>true</displayonly -->` | 僅顯示（不播放 TTS） |

---

## 🎯 LLM Prompt 指引

LLM 應根據對話內容和場景，生成適當的 Actions 來增強虛擬人的互動效果。

### 1. emotion（情緒）

**使用時機：**
- 問候、寒暄 → `happy`
- 回答專業問題 → `neutral` 或 `thinking`
- 表達關心 → `concerned` 或 `empathetic`
- 緊急狀況 → `serious`
- 被稱讚 → `embarrassed`（優必醬）

**範例：**
```
用戶：你好！
LLM 輸出：
<!-- emotion>happy</emotion -->
<!-- lang>tw (zh)</lang -->

你好啊！很高興見到你<sbr>
```

### 2. lang（語言）

**使用時機：**
- 檢測用戶使用的語言
- 多語言切換時

**範例：**
```
用戶：Hello!
LLM 輸出：
<!-- emotion>neutral</emotion -->
<!-- lang>en</lang -->

Hello! How can I help you<sbr>
```

### 3. options（選項按鈕）

**使用時機：**
- 用戶詢問產品或服務時
- 需要引導用戶選擇時
- 提供多個解決方案時

**範例：**
```
用戶：優必達有哪些產品？
LLM 輸出：
<!-- emotion>excited</emotion -->
<!-- lang>tw (zh)</lang -->

優必達有多款產品喔<sbr>
<!-- options>{"items":["UbiGPT","UbiAnchor","UbiArt","UbiONE"]}</options -->
```

### 4. link（連結）

**使用時機：**
- 用户提供参考資料時
- 需要引導用戶到官網或文件時

**範例：**
```
用戶：官網在哪裡？
LLM 輸出：
<!-- emotion>neutral</emotion -->
<!-- lang>tw (zh)</lang -->

這是我們的官網<sbr>
<!-- link>https://www.ubitus.tv/</link -->
歡迎參觀<sbr>
```

### 5. image（圖片）

**使用時機：**
- 描述產品外觀時
- 需要視覺輔助說明時

**範例：**
```
用戶：UbiGPT 長什麼樣子？
LLM 輸出：
<!-- emotion>happy</emotion -->
<!-- lang>tw (zh)</lang -->

這是 UbiGPT 的外觀<sbr>
<!-- image>https://example.com/ubigpt.png</image -->
很可愛吧<sbr>
```

### 6. bg（背景）

**使用時機：**
- 場景切換時
- 情緒或氛圍改變時

**範例：**
```
用戶：切換到派對模式
LLM 輸出：
<!-- emotion>excited</emotion -->
<!-- lang>tw (zh)</lang -->
<!-- bg>#FF6B6B</bg -->

派對開始<sbr>
<!-- options>{"items":["跳舞","唱歌","聊天"]}</options -->
```

### 7. displayonly（僅顯示）

**使用時機：**
- 系統訊息
- 不需要語音播報的提示

**範例：**
```
用戶：（系統事件）
LLM 輸出：
<!-- displayonly>true</displayonly -->
<!-- emotion>neutral</emotion -->
<!-- lang>tw (zh)</lang -->

（載入中...）<sbr>
```

---

## 🎭 情緒標籤（emotion）

### 支持的情緒

| 標籤 | 說明 | 適用場景 |
|------|------|----------|
| `neutral` | 中性 | 一般對話 |
| `happy` | 開心 | 問候、讚美、有趣的話題 |
| `sad` | 悲傷 | 遺憾、抱歉、悲傷的話題 |
| `angry` | 生氣 | 被冒犯、不滿（謹慎使用） |
| `surprised` | 驚訝 | 意外、驚喜 |
| `excited` | 興奮 | 歡樂、慶祝 |
| `thinking` | 思考 | 考慮、解釋複雜內容 |
| `embarrassed` | 害羞 | 被稱讚、尷尬（優必醬專用） |
| `concerned` | 關心 | 健康諮詢、擔憂（護士專用） |
| `serious` | 嚴肅 | 專業建議、緊急狀況（護士專用） |
| `encouraging` | 鼓勵 | 安慰、打氣（護士專用） |
| `empathetic` | 同理 | 理解用戶感受（護士專用） |

### 使用範例

```
<!-- emotion>happy</emotion -->
<!-- lang>tw (zh)</lang -->

哈囉！今天天氣真好<sbr>
要不要一起出去玩<sbr>
```

---

## 🌐 語言標籤（lang）

### 支持的語言

| 標籤 | 語言 |
|------|------|
| `tw (zh)` | 繁體中文 |
| `cn (zh)` | 簡體中文 |
| `en` | 英文 |
| `ja` | 日文 |
| `ko` | 韓文 |

### 使用範例

```
<!-- emotion>neutral</emotion -->
<!-- lang>en</lang -->

Hello! How can I help you today<sbr>
Feel free to ask me anything<sbr>
```

---

## 📏 斷句規則

### 基本規則

1. **每句結尾必須加 `<sbr>`**
2. **避免過長的句子**（建議 < 100 字）
3. **自然斷句** - 根據語意分割

### 正確範例

```
<!-- emotion>happy</emotion -->
<!-- lang>tw (zh)</lang -->

你好！我是優必醬<sbr>
很高興見到你<sbr>
有什麼我可以幫你的嗎<sbr>
```

### 錯誤範例

```
<!-- emotion>happy</emotion -->
<!-- lang>tw (zh)</lang -->

你好我是優必醬很高興見到你有什麼我可以幫你的嗎<sbr>
❌ 太長，應該斷句
```

---

## 🎨 完整範例

### 範例 1：問候（優必醬）

```
<!-- emotion>happy</emotion -->
<!-- lang>tw (zh)</lang -->

嗨嗨～你好啊<sbr>
人家是優必醬，優必達的虛擬代言人～♪<sbr>
很高興認識你<sbr>
有什麼可以幫你的嗎～<sbr>
```

### 範例 2：回答問題（優必醬）

```
<!-- emotion>excited</emotion -->
<!-- lang>tw (zh)</lang -->

欸嘿～讓人家來介紹優必達的產品喔<sbr>
有 UbiGPT（AI 對話助手）<sbr>
UbiAnchor（雲端遊戲）<sbr>
UbiArt（AI 藝術）<sbr>
還有 Ubi-chan（就是人家啦～♪）<sbr>
以及 UbiONE（整合解決方案）<sbr>
想了解哪個呢～<sbr>
```

### 範例 3：健康諮詢（護士）

```
<!-- emotion>concerned</emotion -->
<!-- lang>tw (zh)</lang -->

哎呀，感冒了嗎<sbr>
先提醒您，如果發燒超過 38.5 度、呼吸困難或症狀持續 3 天以上，請盡快就醫喔<sbr>
一般感冒可以這樣照顧自己<sbr>
1. 多休息，保證充足睡眠<sbr>
2. 多喝溫開水，保持水分<sbr>
3. 飲食清淡，避免油膩食物<sbr>
4. 注意保暖，避免吹風<sbr>
要多保重身體喔～<sbr>
```

### 範例 4：緊急狀況（護士）

```
<!-- emotion>serious</emotion -->
<!-- lang>tw (zh)</lang -->

⚠️ 請立即就醫<sbr>
胸口疼痛可能是嚴重症狀<sbr>
請立刻前往急診或撥打急救電話<sbr>
在等待救護車時<sbr>
- 保持安靜，不要走動<sbr>
- 採取舒適的坐姿<sbr>
- 放鬆衣物，保持呼吸順暢<sbr>
請務必盡快就醫檢查<sbr>
```

### 範例 5：多語言切換

```
<!-- emotion>happy</emotion -->
<!-- lang>ja</lang -->

こんにちは！優必醬です<sbr>
お会いできて嬉しいです<sbr>
何かお手伝いしましょうか<sbr>
```

---

## 🔧 前端解析

### 解析流程

```javascript
function parseVirtualHumanOutput(response) {
    // 1. 解析情緒標籤
    const emotionMatch = response.match(/<!-- emotion>(.+?)<\/emotion -->/);
    const emotion = emotionMatch ? emotionMatch[1] : 'neutral';
    
    // 2. 解析語言標籤
    const langMatch = response.match(/<!-- lang>(.+?)<\/lang -->/);
    const lang = langMatch ? langMatch[1] : 'tw (zh)';
    
    // 3. 移除標籤
    let content = response
        .replace(/<!-- emotion>.+?<\/emotion -->/, '')
        .replace(/<!-- lang>.+?<\/lang -->/, '')
        .trim();
    
    // 4. 根據 <sbr> 分割句子
    const sentences = content.split('<sbr>').filter(s => s.trim());
    
    return { emotion, lang, sentences };
}
```

### 渲染流程

```javascript
// 1. 設置表情
avatar.setEmotion(emotion);

// 2. 設置 TTS 聲音
tts.setVoice(lang);

// 3. 逐句顯示
sentences.forEach((sentence, index) => {
    setTimeout(() => {
        // 顯示文字
        displayText(sentence);
        
        // 播放 TTS
        tts.speak(sentence);
    }, index * 2000); // 每句間隔 2 秒
});
```

---

## ⚠️ 注意事項

### 1. 標籤格式

- ✅ 使用 HTML 註解格式（`<!-- ... -->`）
- ✅ 開始和結束標籤必須配對
- ✅ 標籤必須在開頭（前兩行）

### 2. 斷句符號

- ✅ 使用 `<sbr>`（不是 `<br>` 或 `\n`）
- ✅ 每句結尾都必須有 `<sbr>`
- ✅ 最後一句也要有 `<sbr>`

### 3. 情緒和語言

- ✅ 必須選擇支持的情緒和語言
- ✅ 避免使用未定義的標籤
- ✅ 預設值：`neutral` + `tw (zh)`

---

## 📊 版本歷史

| 版本 | 日期 | 變更說明 |
|------|------|----------|
| v2.0 | 2026-04-15 | 統一斷句符號為 `<sbr>`，新增更多情緒標籤 |
| v1.0 | - | 原始版（使用 `<br>` 斷句） |

---

**維護者：** 蝦米 Agent 團隊  
**最後更新：** 2026-04-15
