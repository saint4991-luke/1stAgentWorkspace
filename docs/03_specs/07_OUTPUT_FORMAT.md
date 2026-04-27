# 📝 輸出格式規格書

**版本：** v2.0  
**日期：** 2026-04-08  
**Branch:** `agent-ubichan`

---

## 🎯 文件職責

**本文檔說明：**
- 虛擬人輸出格式規格（情緒標籤、語言標籤、斷句符號）
- 前端渲染與 TTS 整合技術規格

---

## 📋 概述

輸出格式是**虛擬人輸出的統一格式**，讓前端可以：
- **解析情緒** - 根據情緒標籤調整表情
- **解析語言** - 根據語言標籤選擇 TTS 聲音
- **逐句顯示** - 根據斷句符號分割句子
- **流式渲染** - 支持逐字顯示效果

---

## 📐 格式定義

### 完整格式

```
<!-- emotion -->情緒標籤<!-- /emotion -->
<!-- lang -->語言標籤<!-- /lang -->

回覆內容第 1 句。<sbr>
回覆內容第 2 句。<sbr>
回覆內容第 3 句。<sbr>
```

### 欄位說明

| 欄位 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `<!-- emotion -->...<!-- /emotion -->` | ✅ | 情緒標籤 | `happy`, `neutral`, `sad` |
| `<!-- lang -->...<!-- /lang -->` | ✅ | 語言標籤 | `tw (zh)`, `en`, `ja` |
| `<sbr>` | ✅ | 斷句符號 | 每句結尾 |
| 空行 | ✅ | 分隔標籤與內容 | 標籤後空一行 |

---

## 🎭 Actions（動作類型）

本規格定義 **7 個 Actions**，用於控制虛擬人的表情、語言、互動等行為。

### 完整的 Actions 清單

| Action | 格式 | 說明 | 範例 |
|--------|------|------|------|
| `emotion` | `<!-- emotion>{emotion}</emotion -->` | 情緒標籤 | `<!-- emotion>happy</emotion -->` |
| `lang` | `<!-- lang>{lang}</lang -->` | 語言標籤 | `<!-- lang>tw (zh)</lang -->` |
| `options` | `<!-- options>{json}</options -->` | 選項按鈕 | `<!-- options>{"items":["選項 1","選項 2"]}</options -->` |
| `link` | `<!-- link>{url}</link -->` | 連結 | `<!-- link>https://example.com</link -->` |
| `image` | `<!-- image>{url}</image -->` | 圖片 | `<!-- image>https://example.com/img.png</image -->` |
| `bg` | `<!-- bg>{color_or_url}</bg -->` | 背景 | `<!-- bg>#FF0000</bg -->` |
| `displayonly` | `<!-- displayonly>true</displayonly -->` | 僅顯示（不播放 TTS） | `<!-- displayonly>true</displayonly -->` |

### 使用範例

```
<!-- emotion>happy</emotion -->
<!-- lang>tw (zh)</lang -->

你好！今天天氣真好<sbr>
<!-- options>{"items":["出門玩","在家休息"]}</options -->
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

## 🔗 連結（link）

當需要提供参考資料或外部資源時使用。

**格式：**
```
<!-- link>{URL}</link -->
```

**範例：**
```
<!-- link>https://www.ubitus.tv/</link -->

這是優必達官網<sbr>
歡迎參觀<sbr>
```

---

## 🖼️ 圖片（image）

當需要展示圖片時使用。

**格式：**
```
<!-- image>{圖片 URL}</image -->
```

**範例：**
```
<!-- image>https://example.com/product.png</image -->

這是我們的產品<sbr>
請參考圖片<sbr>
```

---

## 🔘 選項按鈕（options）

當需要提供互動選項時使用。

**格式：**
```
<!-- options>{"items":["選項 1","選項 2","選項 3"]}</options -->
```

**範例：**
```
<!-- options>{"items":["了解產品","技術支援","聯絡我們"]}</options -->

請問您需要什麼協助<sbr>
```

---

## 🎨 背景（bg）

當需要切換背景時使用。

**格式：**
```
<!-- bg>{顏色代碼或背景 URL}</bg -->
```

**範例：**
```
<!-- bg>#FF6B6B</bg -->

現在切換到紅色背景<sbr>
```

---

## 🔇 僅顯示（displayonly）

當只需要顯示文字但不播放 TTS 時使用。

**格式：**
```
<!-- displayonly>true</displayonly -->
```

**範例：**
```
<!-- displayonly>true</displayonly -->

（這段文字只會顯示，不會播放語音）<sbr>
```

---

## 📏 斷句規則

### 基本規則

1. **每句結尾必須加 `<sbr>`**
2. **避免過長的句子**（建議 < 100 字）
3. **自然斷句** - 根據語意分割

### 正確範例

```
你好！我是優必醬。<sbr>
有什麼可以幫你？<sbr>
```

### 錯誤範例

```
你好！我是優必醬。有什麼可以幫你？  # 缺少 <sbr>
```

---

## 📝 完整範例

### 範例 1：問候

```
<!-- emotion -->happy<!-- /emotion -->
<!-- lang -->tw (zh)<!-- /lang -->

哈囉！我是優必醬！<sbr>
很高見到你！<sbr>
今天有什麼可以幫你？<sbr>
```

### 範例 2：多語言

```
<!-- emotion -->neutral<!-- /emotion -->
<!-- lang -->en<!-- /lang -->

Hello! Welcome to Ubitus!<sbr>
How can I assist you today?<sbr>
Feel free to ask me anything.<sbr>
```

### 範例 3：思考

```
<!-- emotion -->think<!-- /emotion -->
<!-- lang -->tw (zh)<!-- /lang -->

讓我想想這個問題...<sbr>
根據我的了解，這個產品有三個主要特點。<sbr>
第一，它非常高效。<sbr>
第二，它很容易使用。<sbr>
第三，它的價格很合理。<sbr>
```

---

## 🔧 前端解析（偽代碼）

本節提供**通用的解析邏輯**，不限定特定程式語言。

### 解析流程

```
FUNCTION parseVirtualHumanResponse(response):
    // 1. 解析所有 Action 標籤
    actions = {}
    FOR EACH action IN ["emotion", "lang", "options", "link", "image", "bg", "displayonly"]:
        pattern = "<!-- " + action + ">(.*?)<!-- /" + action + "-->"
        match = regex_match(response, pattern)
        IF match FOUND:
            actions[action] = match.content
    
    // 2. 移除所有 Action 標籤，取得純內容
    content = response
    FOR EACH action IN ["emotion", "lang", "options", "link", "image", "bg", "displayonly"]:
        pattern = "<!-- " + action + ">.*?<!-- /" + action + "-->"
        content = regex_replace(content, pattern, "")
    content = trim(content)
    
    // 3. 根據 <sbr> 分割句子
    sentences = split(content, "<sbr>")
    sentences = filter_empty(sentences)
    
    // 4. 返回結果
    RETURN {
        actions: actions,      // 所有 Action 標籤的值
        sentences: sentences   // 分割後的句子列表
    }
```

### 渲染流程

```
FUNCTION renderVirtualHumanResponse(parsed):
    // 1. 處理 Actions
    IF parsed.actions["emotion"] EXISTS:
        avatar.setEmotion(parsed.actions["emotion"])
    
    IF parsed.actions["lang"] EXISTS:
        tts.setVoice(parsed.actions["lang"])
    
    IF parsed.actions["options"] EXISTS:
        ui.showButtons(parse_json(parsed.actions["options"]))
    
    IF parsed.actions["link"] EXISTS:
        ui.showLink(parsed.actions["link"])
    
    IF parsed.actions["image"] EXISTS:
        ui.showImage(parsed.actions["image"])
    
    IF parsed.actions["bg"] EXISTS:
        ui.setBackground(parsed.actions["bg"])
    
    IF parsed.actions["displayonly"] == "true":
        tts.disable()  // 不播放語音
    
    // 2. 逐句顯示
    FOR EACH sentence IN parsed.sentences:
        ui.displayText(sentence)
        IF tts.isEnabled():
            tts.speak(sentence)
        WAIT for_sentence_display_complete()
```

### 使用範例

```
輸入：
<!-- emotion>happy<!-- /emotion -->
<!-- lang>tw (zh)<!-- /lang -->
<!-- options>{"items":["選項 1","選項 2"]}<!-- /options -->

你好！我是優必醬。<sbr>
有什麼可以幫你？<sbr>

輸出：
{
    actions: {
        emotion: "happy",
        lang: "tw (zh)",
        options: "{\"items\":[\"選項 1\",\"選項 2\"]}"
    },
    sentences: ["你好！我是優必醬。", "有什麼可以幫你？"]
}

渲染行為：
1. 設置表情為 happy
2. 設置 TTS 語言為 tw (zh)
3. 顯示兩個選項按鈕
4. 逐句顯示文字並播放語音
```

---

## ⚠️ 注意事項

1. **情緒標籤必須在開頭**
2. **語言標籤必須在情緒標籤之後**
3. **標籤後必須空一行**
4. **每句結尾必須加 `<sbr>`**

---

**文檔結束**
