#!/usr/bin/env python3
"""
🦐 蝦米 Agent Stream Events - 流式事件定義

定義 SSE (Server-Sent Events) 的事件類型和數據結構。
支持多種輸出格式（UBICHAN、OpenAI Compatible 等）

規格：docs/03_specs/05_SSE_OUTPUT_SPEC.md
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import json


class StreamEventType(str, Enum):
    """流式事件類型"""
    
    # 會話控制
    START = "start"              # 開始
    DONE = "done"               # 完成
    ERROR = "error"             # 錯誤
    
    # 內容輸出
    TEXT_CHUNK = "text_chunk"    # 文字區塊
    THINKING = "thinking"        # 思考過程


class StreamEvent(BaseModel):
    """SSE 流式事件"""
    
    event: str
    message: Optional[str] = None
    created: Optional[int] = None
    id: Optional[str] = None
    timing: Optional[Dict[str, Any]] = None
    usage: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def to_sse(self) -> str:
        """
        轉換為 SSE 格式（自動在 done/error 後加 [DONE] 標記）
        
        Returns:
            str: SSE 格式字串
        """
        data = self._build_data()
        # ✅ 使用 ensure_ascii=False 支持中文，sort_keys=True 確保穩定性
        json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False, sort_keys=True)
        sse = f"event: {self.event}\ndata: {json_str}\n\n"
        
        # 在 done/error 事件後直接加 [DONE]（寫死）
        if self.event in ["done", "error"]:
            sse += "data: [DONE]\n\n"
        
        return sse
    
    def _build_data(self) -> Dict[str, Any]:
        """構建數據字典"""
        data = {"event": self.event}
        
        if self.event == "text_chunk":
            data["message"] = self.message
            data["created"] = self.created
            data["id"] = self.id
        elif self.event == "done":
            data["created"] = self.created
            data["id"] = self.id
            if self.timing:
                data["timing"] = self.timing
            if self.usage:
                data["usage"] = self.usage
        elif self.event == "error":
            data["error"] = self.error
            data["created"] = self.created
            data["id"] = self.id
        
        return data
    
    @classmethod
    def create_text_chunk(
        cls,
        message: str,
        created: int,
        event_id: str
    ) -> "StreamEvent":
        """
        創建 text_chunk 事件
        
        Args:
            message: 文字內容
            created: Unix 時間戳（秒）
            event_id: 事件 ID（格式：session_id_created）
        
        Returns:
            StreamEvent: text_chunk 事件
        """
        return cls(
            event="text_chunk",
            message=message,
            created=created,
            id=event_id
        )
    
    @classmethod
    def create_done(
        cls,
        created: int,
        event_id: str,
        timing: Optional[Dict] = None,
        usage: Optional[Dict] = None
    ) -> "StreamEvent":
        """
        創建 done 事件
        
        Args:
            created: Unix 時間戳（秒）
            event_id: 事件 ID
            timing: 計時數據（可選）
            usage: Token 用量（可選）
        
        Returns:
            StreamEvent: done 事件
        """
        return cls(
            event="done",
            created=created,
            id=event_id,
            timing=timing,
            usage=usage
        )
    
    @classmethod
    def create_error(
        cls,
        error: str,
        created: int,
        event_id: str
    ) -> "StreamEvent":
        """
        創建 error 事件
        
        Args:
            error: 錯誤訊息
            created: Unix 時間戳（秒）
            event_id: 事件 ID
        
        Returns:
            StreamEvent: error 事件
        """
        return cls(
            event="error",
            error=error,
            created=created,
            id=event_id
        )


def format_sse_event(event: StreamEvent) -> str:
    """
    格式化 SSE 事件（自動在 done/error 後加 [DONE] 標記）
    
    Args:
        event: StreamEvent 對象
    
    Returns:
        str: SSE 格式字串
    """
    return event.to_sse()


def parse_sse_event(line: str) -> Optional[StreamEvent]:
    """
    解析 SSE 事件
    
    Args:
        line: SSE 格式字串
    
    Returns:
        Optional[StreamEvent]: StreamEvent 對象，解析失敗返回 None
    """
    if not line.startswith("data: "):
        return None
    
    try:
        data = json.loads(line[6:])
        return StreamEvent(**data)
    except Exception:
        return None


# ============= 測試 =============
if __name__ == "__main__":
    print("=" * 60)
    print("🦐 蝦米 Agent Stream Events 測試")
    print("=" * 60)
    
    # 測試 1: text_chunk（UBICHAN 格式）
    print("\n📝 測試 1 - text_chunk（UBICHAN 格式）:")
    event = StreamEvent.create_text_chunk(
        message="讓我調查",
        created=1776416929,
        event_id="session_123_1776416929"
    )
    print(event.to_sse())
    
    # 測試 2: done（UBICHAN 格式，含 timing + usage）
    print("✅ 測試 2 - done（UBICHAN 格式，含 [DONE] 標記）:")
    event = StreamEvent.create_done(
        created=1776416929,
        event_id="session_123_1776416929",
        timing={
            "rag_llm_ms": 535,
            "file_read_ms": 3,
            "rag_retrieve_ms": 120,
            "llm_call_ms": 2100,
            "total_ms": 2658
        },
        usage={
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
    )
    print(event.to_sse(include_done_marker=True))
    
    # 測試 3: error（含 [DONE] 標記）
    print("❌ 測試 3 - error（含 [DONE] 標記）:")
    event = StreamEvent.create_error(
        error="測試錯誤訊息",
        created=1776416929,
        event_id="session_123_1776416929"
    )
    print(event.to_sse(include_done_marker=True))
    
    # 測試 4: done（不含 [DONE] 標記）
    print("✅ 測試 4 - done（不含 [DONE] 標記）:")
    event = StreamEvent.create_done(
        created=1776416929,
        event_id="session_123_1776416929",
        timing={"total_ms": 1000}
    )
    print(event.to_sse(include_done_marker=False))
    
    # 測試 5: format_sse_event 輔助函數
    print("🔧 測試 5 - format_sse_event 輔助函數:")
    event = StreamEvent.create_text_chunk(
        message="測試",
        created=1776416929,
        event_id="test_1776416929"
    )
    print(format_sse_event(event, include_done_marker=False))
    
    print("=" * 60)
    print("✅ StreamEvent 測試完成")
    print("=" * 60)
