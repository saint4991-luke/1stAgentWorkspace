"""
bridge.py - Session + ext_query 橋接服務

整合：
- session/ 模組（Session 管理）
- ext_query/ 模組（電話號碼查詢）

API 端點（根據 AIJPDNC-QueryRESTAPIforDNC-110526-1134-192.pdf 規範）:
- GET /session - 創建 Session（初始化會話環境）
- POST /chat - 聊天查詢（SSE 串流）
- GET /session/{session_id} - 獲取 Session 詳情（除錯用）
- GET /sessions - 獲取所有活躍 Session
- DELETE /session/{session_id} - 刪除 Session
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


@app.get("/session")
async def create_session():
    """
    創建 Session（初始化會話環境）
    
    根據規範 AIJPDNC-QueryRESTAPIforDNC-110526-1134-192.pdf Section 1.1
    
    HTTP Method: GET
    Response Content-Type: application/json
    
    Response Headers:
    - Set-Cookie: session_id=EXT_...; HttpOnly; SameSite=Lax; Path=/
    
    Response Body:
    {
        "event": "done",
        "message": {
            "session_id": "EXT_4e5c693f-7a30-4452-a902-792e64cb6a6e",
            "metadata": {},
            "created_at": "2026-05-08T03:19:12.224206",
            "last_active": "2026-05-08T03:19:12.224206",
            "ttl_hours": 24
        },
        "created": 1778210352,
        "id": "EXT_4e5c693f-7a30-4452-a902-792e64cb6a6e_1778210352",
        "timing": {
            "total_ms": 2
        }
    }
    """
    if not SESSION_AVAILABLE or not store:
        raise HTTPException(status_code=503, detail="Session module not available")
    
    # 創建新 Session
    session_data = store.create_session(
        prefix="EXT",
        metadata={},
        ttl_hours=24
    )
    
    session_id = session_data['session_id']
    created = int(time.time())
    
    print(f"🆕 創建新 Session: {session_id}")
    
    # 構建響應（符合規範格式）
    response_data = {
        "event": "done",
        "message": {
            "session_id": session_id,
            "metadata": session_data.get('metadata', {}),
            "created_at": session_data['created_at'],
            "last_active": session_data['last_active'],
            "ttl_hours": session_data['ttl_hours']
        },
        "created": created,
        "id": f"{session_id}_{created}",
        "timing": {
            "total_ms": 1  # 創建操作非常快
        }
    }
    
    # 創建 JSONResponse 並設置 cookie
    response = JSONResponse(content=response_data)
    
    # 設置 Session ID Cookie（符合規範）
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="lax",
        path="/"
    )
    
    return response


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


@app.post("/chat")
async def chat_endpoint(request: Request):
    """
    聊天查詢（SSE 串流）
    
    根據規範 AIJPDNC-QueryRESTAPIforDNC-110526-1134-192.pdf Section 1.2
    
    HTTP Method: POST
    Content-Type: application/json
    Accept: text/event-stream
    Cookie: session_id=<YOUR_SESSION_ID>
    
    Request Body:
    {
        "input": "${input}"
    }
    
    Response Headers:
    - Content-Type: text/event-stream; charset=utf-8
    - Cache-Control: no-cache
    - Connection: keep-alive
    
    Response Body (Stream):
    event: text_chunk
    data: {"event":"text_chunk","message":"","created":1778211058,"id":"EXT_0acbce59-4502-4eb8-8661-26cb1a6b222e_1778211058"}
    ...
    event: done
    data: {"event":"done","created":1778211058,"id":"EXT_0acbce59-4502-4eb8-8661-26cb1a6b222e_1778211058","timing":{...}}
    data: [DONE]
    
    Session Expired:
    HTTP Status: 401 Unauthorized
    Body: {"detail": "Session expired or invalid. Please re-initialize session."}
    """
    # 檢查模組就緒狀態
    if not SESSION_AVAILABLE or not store:
        raise HTTPException(status_code=503, detail="Session module not available")
    
    if not EXT_QUERY_AVAILABLE or not retrieval_agent or not final_agent:
        raise HTTPException(status_code=503, detail="ext_query module not available")
    
    # 1. Session 管理（檢查 cookie 中的 session_id）
    session_id = request.cookies.get("session_id")
    
    # 如果沒有 session_id 或 session 不存在，返回 401（符合規範）
    if not session_id:
        raise HTTPException(
            status_code=401,
            detail="Session expired or invalid. Please re-initialize session."
        )
    
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=401,
            detail="Session expired or invalid. Please re-initialize session."
        )
    
    print(f"🔄 使用現有 Session: {session_id}")
    
    # 3. 獲取用戶問題
    try:
        data = await request.json()
        user_query = data.get("input", "")
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
            # 獲取對話歷史（用於判斷是否需要檢索）
            messages = store.get_messages(session_id)
            conversation_history = {"user": [], "assistant": []}
            for msg in messages:
                if msg["role"] == "user":
                    conversation_history["user"].append(msg["content"])
                elif msg["role"] == "assistant":
                    conversation_history["assistant"].append(msg["content"])
            
            # Step A: 判斷是否需要查詢（傳入對話歷史）
            print(f"🔍 [Session: {session_id}] 判斷意圖...")
            keywords, display, is_ignore, search_result = await retrieval_agent.extract_keywords_from_query(
                user_query, 
                conversation_history=conversation_history
            )
            
            if is_ignore:
                # ignore_retrieve：LLM 已經從對話歷史提取了答案
                print(f"💬 [Session: {session_id}] ignore_retrieve，使用 LLM 提取的答案")
                
                # 先傳送 display（如果有）
                if display:
                    full_answer += display
                    yield f"event: text_chunk\ndata: {json.dumps({'event': 'text_chunk', 'message': display, 'created': created, 'id': event_id}, ensure_ascii=False, separators=(',', ':'))}\n\n"
                
                # 再傳送 search_result（如果有）
                if search_result:
                    search_display = f"<!-- json>{json.dumps(search_result, ensure_ascii=False)}</json -->"
                    full_answer += search_display
                    yield f"event: text_chunk\ndata: {json.dumps({'event': 'text_chunk', 'message': search_display, 'created': created, 'id': event_id}, ensure_ascii=False, separators=(',', ':'))}\n\n"
                
                # 如果都沒有
                if not display and not search_result:
                    full_answer = "申し訳ございませんが、回答を抽出できませんでした。"
                    
            elif keywords:
                # 需要查詢 → 呼叫資料庫
                print(f"🔍 [Session: {session_id}] 需要查詢：{keywords}")
                
                # 先回 display（等待中訊息）
                if display:
                    yield f"event: text_chunk\ndata: {json.dumps({'event': 'text_chunk', 'message': display, 'created': created, 'id': event_id}, ensure_ascii=False, separators=(',', ':'))}\n\n"
                
                # Step B: 搜尋資料庫
                results = await retrieval_agent.search_by_keywords(keywords)
                print(f"📊 [Session: {session_id}] 找到 {len(results)} 筆結果")
                
                # Step C: Final Agent 生成回答
                async for chunk in final_agent.generate_answer_stream(user_query, results):
                    if chunk == "[DONE]":
                        break
                    full_answer += chunk
                    
                    # SSE 格式：text_chunk（扁平結構）
                    yield f"event: text_chunk\ndata: {json.dumps({'event': 'text_chunk', 'message': chunk, 'created': created, 'id': event_id}, ensure_ascii=False, separators=(',', ':'))}\n\n"
            
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
            yield f"event: done\ndata: {json.dumps({'event': 'done', 'created': created, 'id': event_id, 'timing': timing}, ensure_ascii=False, separators=(',', ':'))}\n\n"
            
            # Step F: [DONE] 標記（規範要求）
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            print(f"❌ [Session: {session_id}] 錯誤：{e}")
            error_message = str(e)
            
            # SSE 格式：error
            yield f"event: error\ndata: {json.dumps({'event': 'error', 'error': error_message, 'created': created, 'id': event_id}, ensure_ascii=False, separators=(',', ':'))}\n\n"
            
            # Step F: [DONE] 標記（錯誤情況）
            yield "data: [DONE]\n\n"
            
            # 記錄錯誤到 Session
            store.add_message(session_id, role="assistant", content=f"錯誤：{error_message}")
    
    # 6. SSE 串流返回（需要自定義 Response 以支持 cookie）
    from starlette.responses import StreamingResponse
    from starlette import status
    
    # 創建 StreamingResponse 並設置 cookie
    response = StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        status_code=status.HTTP_200_OK
    )
    
    # 設置 Session ID Cookie
    response.set_cookie(
        key="session_id",
        value=session_id,
        max_age=86400,  # 24 小時
        httponly=True,
        samesite="lax",
        path="/"
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
        "description": "Session + ext_query 整合服務（符合 AIJPDNC-QueryRESTAPIforDNC 規範）",
        "endpoints": {
            "GET /session": "創建 Session（初始化會話環境）",
            "POST /chat": "聊天查詢（SSE 串流）",
            "GET /session/{session_id}": "獲取 Session 詳情（除錯用）",
            "GET /sessions": "獲取所有活躍 Session",
            "DELETE /session/{session_id}": "刪除 Session",
            "GET /health": "健康檢查"
        },
        "specification": "docs/03_specs/AIJPDNC-QueryRESTAPIforDNC-110526-1134-192.pdf"
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
    print(f"📜 規範：AIJPDNC-QueryRESTAPIforDNC-110526-1134-192.pdf")
    print("=" * 60)
    print("API 端點:")
    print("  GET  /session - 創建 Session")
    print("  POST /chat    - 聊天查詢（SSE 串流）")
    print("  GET  /health  - 健康檢查")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host=BRIDGE_HOST,
        port=BRIDGE_PORT,
        log_level="info"
    )
