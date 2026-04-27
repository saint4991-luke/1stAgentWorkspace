# 🚀 部署與故障排除指南

**版本：** v1.0  
**最後更新：** 2026-04-17  
**適用對象：** 系統管理員、技術人員

---

## 🎯 文件職責

**本文檔說明：**
- AgentShrimp 跨平台部署指南
- Docker 常見問題與解決方案

---

## 📋 目錄

1. [快速開始](#快速開始)
2. [自動配置（推薦）](#自動配置推薦)
3. [手動配置](#手動配置)
4. [常見問題](#常見問題)

---

## 快速開始

### Windows

```powershell
# 1. 執行自動配置腳本
.\setup.ps1

# 2. 編輯 .env 填入 API_KEY
notepad .env

# 3. 啟動服務
docker-compose up -d

# 4. 訪問 Web UI
http://127.0.0.1:5000
```

### Linux

```bash
# 1. 執行自動配置腳本
chmod +x setup.sh
./setup.sh

# 2. 編輯 .env 填入 API_KEY
nano .env

# 3. 啟動服務
docker-compose up -d

# 4. 訪問 Web UI
http://127.0.0.1:5000
```

---

## 自動配置（推薦）

### 腳本功能

✅ 檢查 Docker 安裝和運行狀態  
✅ 創建必要的目錄（workspace, downloads）  
✅ 設定正確的目錄權限  
✅ 創建 .env 檔案  
✅ 自動啟動 Docker 服務  
✅ 顯示服務狀態和日誌  

### 使用方式

**Windows：**
```powershell
.\setup.ps1
```

**Linux：**
```bash
chmod +x setup.sh
./setup.sh
```

---

## 手動配置

### 步驟 1：創建目錄

```bash
# Windows PowerShell
New-Item -ItemType Directory -Path ".\workspace" -Force
New-Item -ItemType Directory -Path ".\downloads" -Force

# Linux
mkdir -p workspace downloads
```

### 步驟 2：配置環境變數

```bash
# 編輯 .env 檔案
# Windows: notepad .env
# Linux: nano .env

# 填入必要的變數
LLM_PROVIDER=openai
OPENAI_BASE_URL=http://116.50.47.234:8081/v1
OPENAI_API_KEY=your-api-key
LLM_MODEL=Qwen/Qwen3.5-397B-A17B-FP8
```

### 步驟 3：啟動服務

```bash
docker-compose up -d
```

---

## 常見問題

### 問題 1：權限錯誤 (Permission denied)

**錯誤訊息：**
```
permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
```

**解決方案（Linux）：**
```bash
# 將當前用戶加入 docker 組
sudo usermod -aG docker $USER

# 重新登入或執行
newgrp docker

# 驗證
docker ps
```

**解決方案（Windows）：**
```powershell
# 以管理員身份運行 PowerShell
# 重啟 Docker Desktop
```

---

### 問題 2：Session API 啟動失敗

**檢查日誌：**
```bash
cd setup
docker compose logs session
```

**常見錯誤：**

**1. 缺少依賴包**
```
ModuleNotFoundError: No module named 'fastapi'
```
**解決：** 重建 Docker 映像
```bash
docker compose build session
docker compose up -d
```

**2. SQLite 路徑錯誤**
```
sqlite3.OperationalError: unable to open database file
```
**解決：** 確保 `/data` 目錄存在且有寫入權限
```bash
# 在 host 上創建目錄
mkdir -p ../data
chmod 755 ../data
```

**3. 端口衝突**
```
Address already in use
```
**解決：** 停止佔用端口的進程或修改端口
```bash
# 檢查端口佔用
netstat -ano | findstr :8001

# 修改 docker-compose.yml 中的端口映射
```

---

### 問題 3：Agent API 啟動失敗

**檢查日誌：**
```bash
docker compose logs agent
```

**常見錯誤：**

**1. 無法連接 Session API**
```
Connection refused: http://session:8001
```
**解決：** 確保 Session API 先啟動
```bash
# 先啟動 session 服務
docker compose up -d session

# 等待 10 秒
sleep 10

# 啟動 agent 服務
docker compose up -d agent
```

**2. LLM Provider 配置錯誤**
```
Invalid provider: xxx
```
**解決：** 檢查 .env 配置
```bash
# 確認 LLM_PROVIDER 正確
echo $LLM_PROVIDER

# 可用的 Provider: openai, ubisage
```

---

### 問題 4：Docker 容器無法啟動

**檢查 Docker 狀態：**
```bash
# Linux
systemctl status docker

# Windows
# 檢查 Docker Desktop 是否運行
```

**重建容器：**
```bash
# 停止所有服務
docker compose down

# 刪除舊容器
docker compose rm -f

# 重新啟動
docker compose up -d
```

---

### 問題 5：Web UI 無法訪問

**檢查服務狀態：**
```bash
docker compose ps
```

**檢查端口映射：**
```bash
docker compose port web 5000
```

**防火牆設定（Linux）：**
```bash
# 開放端口
sudo ufw allow 5000/tcp
```

---

## 除錯命令

### 查看日誌

```bash
# 查看所有服務日誌
docker compose logs

# 查看特定服務日誌
docker compose logs agent
docker compose logs session

# 即時查看日誌
docker compose logs -f agent
```

### 進入容器

```bash
# 進入 Agent 容器
docker exec -it shrimp-agent bash

# 進入 Session 容器
docker exec -it shrimp-session bash
```

### 重啟服務

```bash
# 重啟單一服務
docker compose restart agent

# 重啟所有服務
docker compose restart
```

### 清理資源

```bash
# 停止所有服務
docker compose down

# 刪除懸掛的映像
docker image prune -f

# 刪除所有未使用的資源
docker system prune -a
```

---

## 相關文檔

- **快速開始：** `docs/02_guides/01_QUICKSTART.md`
- **Persona 設計：** `docs/02_guides/02_PERSONA_GUIDE.md`
- **知識庫管理：** `docs/02_guides/03_KNOWLEDGE_GUIDE.md`

---

**版本歷史：**
- v1.0 (2026-04-17) - 合併原 07_DEPLOYMENT_GUIDE.md 和 09_DOCKER_TROUBLESHOOTING.md
