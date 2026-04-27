"""
Session 管理器 - In-Memory + TTL 自動清理

維護活躍 Session，綁定 config_id，自動清理過期 Session。
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Session:
    """Session 數據結構"""
    session_id: str
    config_id: str  # 綁定的虛擬人 ID
    messages: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_active: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SessionManager:
    """Session 管理器"""
    
    def __init__(self, ttl_hours: int = 1):
        """
        初始化 SessionManager
        
        Args:
            ttl_hours: Session 過期時間（小時）
        """
        self.sessions: Dict[str, Session] = {}
        self.ttl = timedelta(hours=ttl_hours)
        print(f"✅ SessionManager 初始化完成 (TTL: {ttl_hours} 小時)")
    
    def create(self, config_id: str, metadata: Dict[str, Any] = None) -> str:
        """
        創建新 Session（綁定 config_id）
        
        Args:
            config_id: 虛擬人 ID
            metadata: 元數據（可選）
        
        Returns:
            session_id
        """
        session_id = str(uuid.uuid4())
        
        self.sessions[session_id] = Session(
            session_id=session_id,
            config_id=config_id,  # 綁定！
            messages=[],
            created_at=datetime.utcnow(),
            last_active=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        print(f"📝 創建新 Session: {session_id} (config: {config_id})")
        return session_id
    
    def get(self, session_id: str) -> Optional[Session]:
        """
        取得 Session（檢查過期）
        
        Args:
            session_id: Session ID
        
        Returns:
            Session 對象，如果不存在或過期則返回 None
        """
        if session_id not in self.sessions:
            print(f"⚠️  Session 不存在：{session_id}")
            return None
        
        session = self.sessions[session_id]
        
        # 檢查是否過期
        if datetime.utcnow() - session.last_active > self.ttl:
            print(f"⏰ Session 過期：{session_id}")
            self.delete(session_id)
            return None
        
        # 更新最後活躍時間
        session.last_active = datetime.utcnow()
        
        return session
    
    def add_message(self, session_id: str, role: str, content: str, 
                    metadata: Dict[str, Any] = None) -> bool:
        """
        添加訊息到 Session
        
        Args:
            session_id: Session ID
            role: 'user' 或 'assistant'
            content: 訊息內容
            metadata: 額外元數據（emotion, lang 等）
        
        Returns:
            是否成功
        """
        session = self.get(session_id)
        if not session:
            return False
        
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.utcnow()
        }
        
        if metadata:
            message.update(metadata)
        
        session.messages.append(message)
        
        # 更新最後活躍時間
        session.last_active = datetime.utcnow()
        
        return True
    
    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """
        取得對話歷史
        
        Args:
            session_id: Session ID
        
        Returns:
            訊息列表
        """
        session = self.get(session_id)
        if not session:
            return []
        
        return session.messages
    
    def delete(self, session_id: str) -> bool:
        """
        刪除 Session
        
        Args:
            session_id: Session ID
        
        Returns:
            是否成功
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            print(f"🗑️  刪除 Session: {session_id}")
            return True
        return False
    
    def cleanup_expired(self) -> int:
        """
        清理過期的 Session
        
        Returns:
            清理的數量
        """
        now = datetime.utcnow()
        expired = [
            sid for sid, session in self.sessions.items()
            if now - session.last_active > self.ttl
        ]
        
        for sid in expired:
            del self.sessions[sid]
        
        if expired:
            print(f"🧹 清理了 {len(expired)} 個過期 Session")
        
        return len(expired)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        取得 Session 統計資訊
        
        Returns:
            統計字典
        """
        now = datetime.utcnow()
        
        active_count = 0
        idle_count = 0
        
        for session in self.sessions.values():
            age = now - session.last_active
            if age < timedelta(minutes=5):
                active_count += 1
            else:
                idle_count += 1
        
        return {
            'total_sessions': len(self.sessions),
            'active_sessions': active_count,
            'idle_sessions': idle_count,
            'ttl_hours': self.ttl.total_seconds() / 3600
        }
