# 🚀 快速開始指南

**版本：** v1.2  
**最後更新：** 2026-04-16  
**預計時間：** 5 分鐘

---

## 🎯 文件職責

**本文檔說明：**
- AgentShrimp 的快速安裝與啟動指南
- 5 分鐘內完成第一次對話測試的步驟說明

---

## 🎯 目標

在 5 分鐘內啟動 AgentShrimp 服務並完成第一次對話測試。

---

## 📋 前置條件

### 必要條件

- ✅ Docker + Docker Compose 已安裝
- ✅ Git 已安裝
- ✅ API Key（Qwen / OpenAI）

### 檢查命令

```bash
# 檢查 Docker
docker --version
docker compose version

# 檢查 Git
git --version
```

---

## 步驟 1：克隆專案

```bash
# 克隆專案
git clone https://github.com/srjiang/agtshrimp.git
cd agtshrimp

# 切換到正確分支
git checkout agent-ubichan
```

---

## 步驟 2：配置環境

### 2.1 複製環境配置文件

```bash
cd setup
cp .env.example .env
```

### 2.2 編輯 .env 文件

```bash
# Linux / macOS
nano .env

# Windows
notepad .env
```

**必要配置：**
```bash
# OpenAI Provider（Qwen）
OPENAI_BASE_URL=http://116.50.47.234:8081/v1
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=Qwen/Qwen3.5-397B-A17B-FP8

# KNOWLEDGE 配置（選用）
KNOWLEDGE_PASSPHRASE=5688
```

**⚠️ 重要：** 將 `your-api-key-here` 替換為你的實際 API Key。

---

## 步驟 3：啟動服務

```bash
cd setup

# 構建並啟動
docker compose up -d --build

# 查看日誌（可選）
docker compose logs -f agent
```

**預期輸出：**
```
✔ Container setup-agent-1  Started
✔ Container setup-web-1     Started
```

---

## 步驟 4：驗證服務

### 4.1 檢查健康狀態

```bash
curl http://localhost:8000/health
```

**預期回應：**
```json
{"status":"healthy"}
```

### 4.2 訪問 Web UI

打開瀏覽器訪問：
- **Web UI:** http://localhost:5000
- **API:** http://localhost:8000

---

## 步驟 5：第一次對話測試

### 方法 A：使用 Web UI（推薦）

1. 打開 http://localhost:5000
2. 點擊「創建新對話」
3. 輸入訊息：「你好！」
4. 確認助手回應正常

### 方法 B：使用 CURL

```bash
# 創建 Session
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "prefix": "TEST",
    "metadata": {"test": true}
  }'

# 回應：
# {"session_id": "TEST_abc123", ...}
```

```bash
# 發送訊息
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "TEST_abc123",
    "messages": [{"role": "user", "content": "你好！"}]
  }'
```

---

## 🔧 常見問題

### 問題 1：Docker 啟動失敗

**錯誤：** `permission denied`

**解決：**
```bash
# Linux：將用戶加入 docker 組
sudo usermod -aG docker $USER
newgrp docker

# 重啟 Docker
sudo systemctl restart docker
```

### 問題 2：API Key 錯誤

**錯誤：** `401 Unauthorized`

**解決：**
1. 檢查 `.env` 中的 `OPENAI_API_KEY`
2. 確認 API Key 有效
3. 重啟服務：`docker compose restart`

### 問題 3：端口衝突

**錯誤：** `Address already in use`

**解決：**
```bash
# 檢查端口佔用
lsof -i :8000
lsof -i :5000

# 停止衝突服務或修改 docker-compose.yml 端口
```

---

## 📚 下一步

完成快速開始後，你可以：

1. **學習 Persona 配置** → `02_PERSONA_GUIDE.md`
2. **學習知識庫管理** → `03_KNOWLEDGE_GUIDE.md`
3. **查看故障排除** → `04_DEPLOYMENT_TROUBLESHOOTING.md`

---

## 🎉 完成！

你已成功啟動 AgentShrimp 服務！

**有用連結：**
- 專案 Repo: https://github.com/srjiang/agtshrimp
- 文檔地圖：`docs/README.md`
- 技術規格：`docs/03_specs/`

---

**版本歷史：**
- v1.0 (2026-04-16) - 初始版本
