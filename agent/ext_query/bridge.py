"""
bridge.py - Session + ext_query 橋接服務

整合：
- session/ 模組（Session 管理）
- ext_query/ 模組（電話號碼查詢）

API 端點：
- POST /query - 統一查詢入口（SSE 串流）
- GET /session/{session_id} - 獲取 Session 詳情
- GET /health - 健康檢查
"""

import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# 添加父目錄到 Python 路徑，以便導入 session 模組
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from typing import Optional, Dict, Any
import json
import time

# 環境變數配置
SESSION_DB_PATH = os.getenv("SESSION_DB_PATH", "/data/sessions.db")
USER_ID_HEADER = os.getenv("USER_ID_HEADER", "X-User-ID")
BRIDGE_HOST = os.getenv("BRIDGE_HOST", "0.0.0.0")
BRIDGE_PORT = int(os.getenv("BRIDGE_PORT", "3006"))

# 導入 session 模組
try:
    from session.session_store import SessionStore, get_session_store
    SESSION_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 警告：無法導入 session 模組：{e}")
    SESSION_AVAILABLE = False

# 導入 ext_query 模組（同目錄）
try:
    from retrieval_agent import RetrievalAgent
    from final_agent import FinalAgent
    EXT_QUERY_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 警告：無法導入 ext_query 模組：{e}")
    EXT_QUERY_AVAILABLE = False

# 全局變數
store: Optional[SessionStore] = None
retrieval_agent: Optional[RetrievalAgent] = None
final_agent: Optional[FinalAgent] = None


def initialize_modules():
    """初始化所有模組"""
    global store, retrieval_agent, final_agent
    
    # 初始化 Session Store
    if SESSION_AVAILABLE:
        try:
            store = get_session_store(db_path=SESSION_DB_PATH)
            print(f"✅ SessionStore 初始化完成 ({SESSION_DB_PATH})")
        except Exception as e:
            print(f"❌ SessionStore 初始化失敗：{e}")
            store = None
    
    # 初始化 Retrieval Agent
    if EXT_QUERY_AVAILABLE:
        try:
            retrieval_agent = RetrievalAgent()
            print("✅ RetrievalAgent 初始化完成")
        except Exception as e:
            print(f"❌ RetrievalAgent 初始化失敗：{e}")
            retrieval_agent = None
        
        try:
            final_agent = FinalAgent()
            print("✅ FinalAgent 初始化完成")
        except Exception as e:
            print(f"❌ FinalAgent 初始化失敗：{e}")
            final_agent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan 事件處理器（替代 @app.on_event("startup")）
    
    FastAPI 推薦的方式：https://fastapi.tiangolo.com/advanced/events/
    """
    # 啟動時執行
    print("🦐 ExtQuery Bridge 啟動中...")
    initialize_modules()
    yield
    # 關閉時執行（清理資源）
    print("👋 ExtQuery Bridge 關閉中...")


# 初始化 FastAPI 應用
app = FastAPI(
    title="ExtQuery Bridge",
    description="Session + ext_query 整合服務 - 電話號碼查詢系統",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """
    健康檢查
    
    返回各模組的就緒狀態。
    """
    return {
        "status": "ok",
        "modules": {
            "session": "ready" if SESSION_AVAILABLE and store else "not available",
            "ext_query": "ready" if EXT_QUERY_AVAILABLE and retrieval_agent and final_agent else "not available"
        }
    }


@app.post("/query")
async def query_endpoint(request: Request):
    """
    統一查詢入口
    
    流程：
    1. 用戶識別 → 2. Session 管理 → 3. ext_query 判斷 → 4. 記錄對話 → 5. 返回結果
    
    請求：
    - Header: X-User-ID (必填)
    - Cookie: session_id (可選)
    - Body: {"query": "用戶問題"}
    
    回應：SSE 串流
    - event: status - 狀態訊息（例如：正在搜尋）
    - event: text_chunk - 回答內容片段
    - event: done - 完成
    - event: error - 錯誤
    """
    # 檢查模組就緒狀態
    if not SESSION_AVAILABLE or not store:
        raise HTTPException(status_code=503, detail="Session module not available")
    
    if not EXT_QUERY_AVAILABLE or not retrieval_agent or not final_agent:
        raise HTTPException(status_code=503, detail="ext_query module not available")
    
    # 1. 用戶識別
    user_id = request.headers.get(USER_ID_HEADER)
    if not user_id:
        raise HTTPException(
            status_code=400,
            detail=f"Missing {USER_ID_HEADER} header"
        )
    
    # 2. Session 管理（檢查是否為連續對話）
    session_id = request.cookies.get("session_id")
    session = None
    
    if session_id:
        session = store.get_session(session_id)
        if not session:
            session_id = None  # Session 過期，重新創建
    
    # 創建新 Session
    if not session_id:
        session_data = store.create_session(
            prefix="EXT",
            metadata={"user_id": user_id},
            ttl_hours=24
        )
        session_id = session_data['session_id']
        print(f"🆕 創建新 Session: {session_id} (user: {user_id})")
    else:
        print(f"🔄 使用現有 Session: {session_id} (user: {user_id})")
    
    # 3. 獲取用戶問題
    try:
        data = await request.json()
        user_query = data.get("query", "")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    if not user_query:
        raise HTTPException(status_code=400, detail="Missing 'query' in request body")
    
    # 4. 記錄用戶問題
    store.add_message(session_id, role="user", content=user_query)
    print(f"💬 [Session: {session_id}] User: {user_query}")
    
    # 5. ext_query 判斷流程
    async def event_generator():
        full_answer = ""
        start_time = time.time()
        
        # 獲取時間戳（請求開始時）- 用於所有事件
        created = int(time.time())
        
        # 生成事件 ID: {session_id}_{created}
        event_id = f"{session_id}_{created}"
        
        try:
            # Step A: 判斷是否需要查詢
            print(f"🔍 [Session: {session_id}] 判斷意圖...")
            keywords, display = await retrieval_agent.extract_keywords_from_query(user_query)
            
            if keywords:
                # 需要查詢 → 呼叫資料庫
                print(f"🔍 [Session: {session_id}] 需要查詢：{keywords}")
                if display:
                    yield {
                        "event": "text_chunk",
                        "data": json.dumps({"event": "text_chunk", "message": display}, ensure_ascii=False)
                    }
                
                # Step B: 搜尋資料庫
                results = await retrieval_agent.search_by_keywords(keywords)
                print(f"📊 [Session: {session_id}] 找到 {len(results)} 筆結果")
                
                # Step C: Final Agent 生成回答
                async for chunk in final_agent.generate_answer_stream(user_query, results):
                    if chunk == "[DONE]":
                        break
                    full_answer += chunk
                    
                    # SSE 格式：text_chunk（扁平結構）
                    yield {
                        "event": "text_chunk",
                        "data": json.dumps({
                            "event": "text_chunk",
                            "message": chunk,
                            "created": created,
                            "id": event_id
                        }, ensure_ascii=False, separators=(',', ':'))
                    }
            else:
                # 不需要查詢 → 直接對話
                print(f"💬 [Session: {session_id}] 不需要查詢，直接對話")
                
                # 使用 Final Agent 生成一般對話回答
                answer = "請問您想查詢什麼電話號碼或聯絡人嗎？"
                full_answer = answer
                
                # SSE 格式：text_chunk
                yield {
                    "event": "text_chunk",
                    "data": json.dumps({
                        "event": "text_chunk",
                        "message": answer,
                        "created": created,
                        "id": event_id
                    }, ensure_ascii=False, separators=(',', ':'))
                }
            
            # Step D: 記錄系統回答
            if full_answer:
                store.add_message(session_id, role="assistant", content=full_answer)
                print(f"💬 [Session: {session_id}] Assistant: {full_answer[:50]}...")
            
            # 計算計時數據
            end_time = time.time()
            timing = {
                "total_ms": int((end_time - start_time) * 1000)
            }
            
            # Step E: 完成（SSE 格式：done）
            yield {
                "event": "done",
                "data": json.dumps({
                    "event": "done",
                    "created": created,
                    "id": event_id,
                    "timing": timing
                }, ensure_ascii=False, separators=(',', ':'))
            }
            
            # Step F: [DONE] 標記（規範要求）
            yield {
                "event": "done",
                "data": "[DONE]"
            }
            
        except Exception as e:
            print(f"❌ [Session: {session_id}] 錯誤：{e}")
            error_message = str(e)
            
            # SSE 格式：error
            yield {
                "event": "error",
                "data": json.dumps({
                    "event": "error",
                    "error": error_message,
                    "created": created,
                    "id": event_id
                }, ensure_ascii=False, separators=(',', ':'))
            }
            
            # Step F: [DONE] 標記（錯誤情況）
            yield {
                "event": "error",
                "data": "[DONE]"
            }
            
            # 記錄錯誤到 Session
            store.add_message(session_id, role="assistant", content=f"錯誤：{error_message}")
    
    # 6. SSE 串流返回
    response = EventSourceResponse(
        event_generator(),
        media_type="text/event-stream"
    )
    
    # 設置 Session ID Cookie
    response.set_cookie(
        key="session_id",
        value=session_id,
        max_age=86400,  # 24 小時
        httponly=True,
        samesite="lax"
    )
    
    return response


@app.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """
    獲取 Session 詳情（用於除錯）
    
    返回完整的 Session 資訊，包含對話歷史。
    """
    if not SESSION_AVAILABLE or not store:
        raise HTTPException(status_code=503, detail="Session module not available")
    
    session = store.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session


@app.get("/sessions")
async def list_sessions():
    """
    獲取所有活躍 Session 列表
    
    返回未過期的 Session 摘要資訊。
    """
    if not SESSION_AVAILABLE or not store:
        raise HTTPException(status_code=503, detail="Session module not available")
    
    sessions = store.list_sessions()
    
    return {
        "count": len(sessions),
        "sessions": sessions
    }


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    刪除 Session
    
    刪除指定的 Session 及其所有對話歷史。
    """
    if not SESSION_AVAILABLE or not store:
        raise HTTPException(status_code=503, detail="Session module not available")
    
    success = store.delete_session(session_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "success": True,
        "message": f"Session {session_id} deleted"
    }


@app.get("/")
async def root():
    """
    根路徑 - API 資訊
    """
    return {
        "name": "ExtQuery Bridge",
        "version": "1.0.0",
        "description": "Session + ext_query 整合服務",
        "endpoints": {
            "POST /query": "統一查詢入口（SSE 串流）",
            "GET /session/{session_id}": "獲取 Session 詳情",
            "GET /sessions": "獲取所有活躍 Session",
            "DELETE /session/{session_id}": "刪除 Session",
            "GET /health": "健康檢查"
        }
    }


# 主程式入口
if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🦐 ExtQuery Bridge 啟動中...")
    print("=" * 60)
    print(f"📍 Host: {BRIDGE_HOST}")
    print(f"🔌 Port: {BRIDGE_PORT}")
    print(f"💾 Session DB: {SESSION_DB_PATH}")
    print(f"🔑 User ID Header: {USER_ID_HEADER}")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host=BRIDGE_HOST,
        port=BRIDGE_PORT,
        log_level="info"
    )
