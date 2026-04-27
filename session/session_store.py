"""
Session Store - SQLite 存儲層

負責 Session 的持久化、CRUD 操作、TTL 清理
"""

import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
import asyncio


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
        
        # 創建 sessions 表
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
    
    def create_session(self, prefix: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, ttl_hours: int = 1) -> Dict[str, Any]:
        """
        創建新 Session
        
        Args:
            prefix: Session ID 前綴（可選）
            metadata: Session 元數據（可選）
            ttl_hours: TTL（小時）
        
        Returns:
            Session 資訊字典
        """
        # 生成 Session ID（如果有 prefix，則加上前綴）
        if prefix:
            session_id = f"{prefix}_{str(uuid.uuid4())}"
        else:
            session_id = str(uuid.uuid4())
        
        now = datetime.utcnow()
        
        # 將 metadata 序列化為 JSON 字符串
        metadata_json = json.dumps(metadata) if metadata else None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
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
        """
        獲取 Session 詳情
        
        Args:
            session_id: Session ID
        
        Returns:
            Session 資訊字典，如果不存在則返回 None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM sessions WHERE session_id = ?', (session_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        session = dict(row)
        
        # 反序列化 metadata（從 JSON 字符串轉為字典）
        if session.get('metadata'):
            try:
                session['metadata'] = json.loads(session['metadata'])
            except (json.JSONDecodeError, TypeError):
                session['metadata'] = None
        
        # 獲取訊息歷史
        session['messages'] = self.get_messages(session_id)
        
        conn.close()
        return session
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        獲取所有活躍 Session 列表
        
        Returns:
            Session 列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 只返回未過期的 Session
        cursor.execute('''
            SELECT * FROM sessions 
            WHERE datetime(last_active, '+' || ttl_hours || ' hours') > datetime('now')
            ORDER BY last_active DESC
        ''')
        
        sessions = []
        for row in cursor.fetchall():
            session = dict(row)
            # 不包含完整 messages，只返回訊息數量
            session['message_count'] = self.get_message_count(session['session_id'])
            sessions.append(session)
        
        conn.close()
        return sessions
    
    def delete_session(self, session_id: str) -> bool:
        """
        刪除 Session
        
        Args:
            session_id: Session ID
        
        Returns:
            是否刪除成功
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 先刪除關聯的訊息
        cursor.execute('DELETE FROM messages WHERE session_id = ?', (session_id,))
        
        # 再刪除 Session
        cursor.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
        
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return deleted
    
    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """
        獲取 Session 的訊息歷史
        
        Args:
            session_id: Session ID
        
        Returns:
            訊息列表
        """
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
        """
        獲取訊息數量
        
        Args:
            session_id: Session ID
        
        Returns:
            訊息數量
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM messages WHERE session_id = ?', (session_id,))
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    def add_message(self, session_id: str, role: str, content: str, 
                    emotion: Optional[str] = None, lang: Optional[str] = None) -> bool:
        """
        添加訊息到 Session
        
        Args:
            session_id: Session ID
            role: 角色 ('user' 或 'assistant')
            content: 訊息內容
            emotion: 情緒標籤（可選）
            lang: 語言標籤（可選）
        
        Returns:
            是否添加成功
        """
        # 先檢查 Session 是否存在
        if not self.get_session(session_id):
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 添加訊息
        cursor.execute('''
            INSERT INTO messages (session_id, role, content, emotion, lang)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_id, role, content, emotion, lang))
        
        # 更新 Session 的最後活動時間
        cursor.execute('''
            UPDATE sessions SET last_active = CURRENT_TIMESTAMP
            WHERE session_id = ?
        ''', (session_id,))
        
        conn.commit()
        conn.close()
        return True
    
    def cleanup_expired(self) -> int:
        """
        清理過期的 Session
        
        Returns:
            清理的 Session 數量
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 找出過期的 Session
        cursor.execute('''
            SELECT session_id FROM sessions
            WHERE datetime(last_active, '+' || ttl_hours || ' hours') <= datetime('now')
        ''')
        
        expired_sessions = [row[0] for row in cursor.fetchall()]
        
        # 刪除過期 Session 及其訊息
        for session_id in expired_sessions:
            cursor.execute('DELETE FROM messages WHERE session_id = ?', (session_id,))
            cursor.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
        
        count = len(expired_sessions)
        conn.commit()
        conn.close()
        
        if count > 0:
            print(f"🧹 清理了 {count} 個過期 Session")
        
        return count


# 背景任務：定期清理過期 Session
async def cleanup_task(store: SessionStore, interval_hours: int = 1):
    """
    背景清理任務
    
    Args:
        store: SessionStore 實例
        interval_hours: 清理間隔（小時）
    """
    while True:
        await asyncio.sleep(interval_hours * 3600)
        store.cleanup_expired()


# 全局單例
_session_store_instance: Optional[SessionStore] = None


def get_session_store(db_path: str = '/data/sessions.db') -> SessionStore:
    """
    獲取 SessionStore 單例
    
    Args:
        db_path: SQLite 數據庫路徑
    
    Returns:
        SessionStore 單例實例
    """
    global _session_store_instance
    if _session_store_instance is None:
        _session_store_instance = SessionStore(db_path)
    return _session_store_instance
