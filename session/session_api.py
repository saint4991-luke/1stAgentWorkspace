"""
🦐 Session API 模組 - 可嵌入 Agent API 或其他服務

提供 Session CRUD、SQLite 持久化、TTL 清理功能
可作為獨立 FastAPI 應用或 BluePrint 模組使用
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sqlite3
import uuid
import json
from datetime import datetime, timedelta
from pathlib import Path
import asyncio

# ============= 數據模型 =============
class CreateSessionRequest(BaseModel):
    """創建 Session 請求"""
    prefix: Optional[str] = None  # 可選的 Session ID 前綴（用於生成 ID，不存儲）
    metadata: Optional[Dict[str, Any]] = None  # 可選的 metadata（JSON 物件，上層模組自行決定內容）
    ttl_hours: int = 1


class SessionResponse(BaseModel):
    """Session 回應"""
    session_id: str
    metadata: Optional[Dict[str, Any]] = None  # metadata（如果有）
    created_at: str
    last_active: str
    ttl_hours: int
    message_count: Optional[int] = 0
    messages: Optional[List[Dict[str, Any]]] = None


class AddMessageRequest(BaseModel):
    """添加訊息請求"""
    role: str
    content: str
    emotion: Optional[str] = None
    lang: Optional[str] = None


# ============= SQLite 存儲層 =============
class SessionStore:
    """Session SQLite 存儲"""
    
    def __init__(self, db_path: str = '/data/sessions.db'):
        """
        初始化 Session Store
        
        Args:
            db_path: SQLite 數據庫路徑
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        print(f"✅ SessionStore 初始化完成 ({db_path})")
    
    def _init_db(self):
        """初始化數據庫 Schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 創建 sessions 表（移除 prefix，添加 metadata）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ttl_hours INTEGER DEFAULT 1
            )
        ''')
        
        # 創建 messages 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                emotion TEXT,
                lang TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        ''')
        
        # 創建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(last_active)')
        
        conn.commit()
        conn.close()
        print("📊 數據庫 Schema 初始化完成")
    
    def create_session(self, prefix: Optional[str] = None, 
                       metadata: Optional[Dict] = None,
                       ttl_hours: int = 1) -> Dict[str, Any]:
        """創建新 Session（Session ID 格式：{PREFIX}_{uuid}）
        
        Args:
            prefix: 可選的自定義 prefix（用於生成 ID，不存儲）
            metadata: 可選的 metadata 字典（上層模組自行決定內容，存儲為 JSON）
            ttl_hours: TTL 小時數
        
        Returns:
            Session 字典
        
        Examples:
            >>> create_session(prefix="UBICHAN", metadata={"vh_char_config": {...}})
            {'session_id': 'UBICHAN_A1B2C3D4E5F6', ...}
            
            >>> create_session()
            {'session_id': 'GENERAL_B2C3D4E5F6G7', ...}
        """
        # 生成 UUID（短版，12 碼）
        uuid_short = uuid.uuid4().hex[:12].upper()
        
        # 決定使用哪個 prefix
        if prefix:
            # 使用傳入的 prefix（轉大寫）
            prefix_upper = prefix.upper()
        else:
            # 預設為 GENERAL
            prefix_upper = 'GENERAL'
        
        session_id = f"{prefix_upper}_{uuid_short}"
        now = datetime.utcnow()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 將 metadata 轉為 JSON 字串
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute('''
            INSERT INTO sessions (session_id, metadata, created_at, last_active, ttl_hours)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_id, metadata_json, now.isoformat(), now.isoformat(), ttl_hours))
        
        conn.commit()
        conn.close()
        
        return {
            'session_id': session_id,
            'metadata': metadata,
            'created_at': now.isoformat(),
            'last_active': now.isoformat(),
            'ttl_hours': ttl_hours
        }
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """獲取 Session 詳情"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM sessions WHERE session_id = ?', (session_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        session = dict(row)
        
        # 解析 metadata（JSON 字串 → 字典）
        if session.get('metadata'):
            try:
                session['metadata'] = json.loads(session['metadata'])
            except:
                session['metadata'] = None
        else:
            session['metadata'] = None
        
        session['messages'] = self.get_messages(session_id)
        
        conn.close()
        return session
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """獲取所有活躍 Session 列表"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM sessions 
            WHERE datetime(last_active, '+' || ttl_hours || ' hours') > datetime('now')
            ORDER BY last_active DESC
        ''')
        
        sessions = []
        for row in cursor.fetchall():
            session = dict(row)
            session['message_count'] = self.get_message_count(session['session_id'])
            sessions.append(session)
        
        conn.close()
        return sessions
    
    def delete_session(self, session_id: str) -> bool:
        """刪除 Session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM messages WHERE session_id = ?', (session_id,))
        cursor.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
        
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return deleted
    
    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """獲取 Session 的訊息歷史"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, role, content, emotion, lang, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY created_at ASC
        ''', (session_id,))
        
        messages = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return messages
    
    def get_message_count(self, session_id: str) -> int:
        """獲取訊息數量"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM messages WHERE session_id = ?', (session_id,))
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    def add_message(self, session_id: str, role: str, content: str, 
                    emotion: Optional[str] = None, lang: Optional[str] = None) -> bool:
        """添加訊息到 Session"""
        if not self.get_session(session_id):
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO messages (session_id, role, content, emotion, lang)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_id, role, content, emotion, lang))
        
        cursor.execute('''
            UPDATE sessions SET last_active = CURRENT_TIMESTAMP
            WHERE session_id = ?
        ''', (session_id,))
        
        conn.commit()
        conn.close()
        return True
    
    def cleanup_expired(self) -> int:
        """清理過期的 Session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT session_id FROM sessions
            WHERE datetime(last_active, '+' || ttl_hours || ' hours') <= datetime('now')
        ''')
        
        expired_sessions = [row[0] for row in cursor.fetchall()]
        
        for session_id in expired_sessions:
            cursor.execute('DELETE FROM messages WHERE session_id = ?', (session_id,))
            cursor.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
        
        count = len(expired_sessions)
        conn.commit()
        conn.close()
        
        if count > 0:
            print(f"🧹 清理了 {count} 個過期 Session")
        
        return count


# ============= FastAPI Router =============
def create_session_router(store: SessionStore) -> APIRouter:
    """
    創建 Session API Router
    
    可嵌入到任何 FastAPI 應用中
    """
    router = APIRouter(prefix="/sessions", tags=["Session"])
    
    @router.post("/", response_model=SessionResponse)
    async def create_session(request: CreateSessionRequest):
        """創建新 Session
        
        - **prefix**: 可選，Session ID 前綴（用於生成 ID，不存儲）
        - **metadata**: 可選，metadata 物件（上層模組自行決定內容）
        - **ttl_hours**: Session 存活時間（小時）
        
        Session ID 格式：{PREFIX}_{uuid}
        
        範例：
        - `{"prefix": "UBICHAN", "metadata": {"vh_char_config": {...}}}` → `UBICHAN_A1B2C3D4E5F6`
        - `{"prefix": "NURSE"}` → `NURSE_B2C3D4E5F6G7`
        - `{}` → `GENERAL_C3D4E5F6G7H8`
        """
        session = store.create_session(
            prefix=request.prefix,
            metadata=request.metadata,
            ttl_hours=request.ttl_hours
        )
        return SessionResponse(**session)
    
    @router.get("/")
    async def list_sessions():
        """獲取所有活躍 Session 列表"""
        sessions = store.list_sessions()
        return {"sessions": sessions}
    
    @router.get("/{session_id}", response_model=SessionResponse)
    async def get_session(session_id: str):
        """獲取 Session 詳情"""
        session = store.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return SessionResponse(**session)
    
    @router.delete("/{session_id}")
    async def delete_session(session_id: str):
        """刪除 Session"""
        success = store.delete_session(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"success": True, "message": "Session deleted"}
    
    @router.get("/{session_id}/messages")
    async def get_messages(session_id: str):
        """獲取 Session 的訊息歷史"""
        if not store.get_session(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        messages = store.get_messages(session_id)
        return {"messages": messages}
    
    @router.post("/{session_id}/messages")
    async def add_message(session_id: str, request: AddMessageRequest):
        """添加訊息到 Session"""
        success = store.add_message(
            session_id=session_id,
            role=request.role,
            content=request.content,
            emotion=request.emotion,
            lang=request.lang
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"success": True}
    
    return router


# ============= 背景清理任務 =============
async def cleanup_task(store: SessionStore, interval_hours: int = 1):
    """背景清理過期 Session"""
    while True:
        await asyncio.sleep(interval_hours * 3600)
        store.cleanup_expired()


# ============= 全局實例（可選） =============
# 如果作為獨立模組使用，可創建全局 store
_session_store: Optional[SessionStore] = None

def get_session_store(db_path: str = '/data/sessions.db') -> SessionStore:
    """獲取或創建 SessionStore 實例"""
    global _session_store
    if _session_store is None:
        _session_store = SessionStore(db_path)
    return _session_store
