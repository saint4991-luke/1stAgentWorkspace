#!/usr/bin/env python3
"""
🦐 蝦米 Agent Block Chunker - 文字分段器

用於將長文字智能分段，優先在段落/換行/句子處斷開。
"""

from typing import List


class BlockChunker:
    """文字分段器"""
    
    def __init__(
        self,
        min_chars: int = 800,
        max_chars: int = 1200,
        break_preference: str = "paragraph"
    ):
        """
        初始化分段器
        
        Args:
            min_chars: 最小字元數 (觸發分段閾值)
            max_chars: 最大字元數 (強制分段閾值)
            break_preference: 斷點優先級 ("paragraph" | "newline" | "sentence")
        """
        self.buffer = ""
        self.min_chars = min_chars
        self.max_chars = max_chars
        self.break_preference = break_preference
    
    def append(self, text: str):
        """添加文字到緩衝區"""
        if text:
            self.buffer += text
    
    def reset(self):
        """重置緩衝區"""
        self.buffer = ""
    
    @property
    def buffered_text(self) -> str:
        """獲取當前緩衝內容"""
        return self.buffer
    
    def has_buffered(self) -> bool:
        """檢查是否有緩衝內容"""
        return len(self.buffer) > 0
    
    def drain(self) -> List[str]:
        """
        輸出分段
        
        Returns:
            List[str]: 分段列表
        """
        chunks = []
        
        while len(self.buffer) >= self.min_chars:
            # 嘗試找到安全斷點
            break_index = self._find_safe_break()
            
            if break_index > 0:
                # 找到安全斷點
                chunk = self.buffer[:break_index].strip()
                if chunk:
                    chunks.append(chunk)
                self.buffer = self.buffer[break_index:].lstrip()
            elif len(self.buffer) > self.max_chars:
                # 超過最大值，強制切斷
                chunk = self.buffer[:self.max_chars].strip()
                chunks.append(chunk)
                self.buffer = self.buffer[self.max_chars:].lstrip()
            else:
                # 還未達到最小值，等待更多內容
                break
        
        return chunks
    
    def flush(self) -> List[str]:
        """
        強制輸出所有緩衝
        
        Returns:
            List[str]: 分段列表
        """
        chunks = []
        if self.buffer.strip():
            chunks.append(self.buffer.strip())
        self.buffer = ""
        return chunks
    
    def should_send(self, chunk: str) -> bool:
        """
        檢查是否應該發送 chunk
        
        Args:
            chunk: 新收到的文字塊
        
        Returns:
            bool: 是否應該發送
        """
        self.append(chunk)
        return len(self.buffer) >= self.min_chars
    
    def get_chunk(self, chunk: str) -> str:
        """
        獲取要發送的文字塊
        
        Args:
            chunk: 新收到的文字塊
        
        Returns:
            str: 要發送的文字塊
        """
        chunks = self.drain()
        if chunks:
            return chunks[0]
        return ""
    
    def has_remaining(self) -> bool:
        """檢查是否有剩餘內容"""
        return len(self.buffer.strip()) > 0
    
    def get_remaining(self) -> str:
        """獲取剩餘內容"""
        remaining = self.buffer.strip()
        self.buffer = ""
        return remaining
    
    def _find_safe_break(self) -> int:
        """
        尋找安全斷點
        
        Returns:
            int: 斷點索引，-1 表示沒有安全斷點
        """
        # 1. 優先段落斷點 (雙換行)
        if self.break_preference == "paragraph":
            idx = self.buffer.find("\n\n", self.min_chars)
            if idx != -1 and idx <= self.max_chars:
                return idx + 2  # 包含換行符
        
        # 2. 其次換行斷點
        if self.break_preference in ["paragraph", "newline"]:
            idx = self.buffer.find("\n", self.min_chars)
            if idx != -1 and idx <= self.max_chars:
                return idx + 1
        
        # 3. 最後句子斷點
        if self.break_preference != "newline":
            for punct in ["。", "！", "？", ".", "!", "?", ";", "；"]:
                idx = self.buffer.find(punct, self.min_chars)
                if idx != -1 and idx <= self.max_chars:
                    return idx + 1
        
        return -1  # 沒有安全斷點


# ============= 測試 =============
if __name__ == "__main__":
    # 測試基本功能
    chunker = BlockChunker(min_chars=50, max_chars=100)
    
    # 測試 1：短文字
    chunker.append("這是短文字。")
    chunks = chunker.drain()
    print(f"測試 1 - 短文字：{len(chunks)} 段 (應為 0)")
    
    # 測試 2：長文字
    long_text = "這是第一段落。\n\n" * 20
    chunker.append(long_text)
    chunks = chunker.drain()
    print(f"測試 2 - 長文字：{len(chunks)} 段 (應為 >0)")
    for i, chunk in enumerate(chunks):
        print(f"  [{i}] {len(chunk)}字元")
    
    # 測試 3：刷新
    final = chunker.flush()
    print(f"測試 3 - 刷新：{len(final)}段")
    
    print("\n✅ BlockChunker 測試完成")
