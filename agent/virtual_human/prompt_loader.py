"""
Prompt 載入器 - 輸出提示詞模板管理

負責載入和管理輸出提示詞模板（prompts/*.md）。
支援快取機制，避免重複讀取文件。
"""

from pathlib import Path
from typing import Dict, Optional


class PromptLoader:
    """輸出提示詞載入器"""
    
    def __init__(self, prompts_path: str = "/workspace/prompts"):
        """
        初始化 PromptLoader
        
        Args:
            prompts_path: prompts 目錄路徑
        """
        self.prompts_path = Path(prompts_path)
        self._cache: Dict[str, str] = {}
    
    def load_prompt(self, output_format: str) -> str:
        """
        載入輸出提示詞模板
        
        Args:
            output_format: 輸出格式（virtual_human | chat）
        
        Returns:
            提示詞模板內容
        """
        # 檢查快取
        if output_format in self._cache:
            return self._cache[output_format]
        
        # 根據 output_format 選擇提示詞文件
        if output_format == 'virtual_human':
            prompt_file = self.prompts_path / "virtual-human-output.md"
        elif output_format == 'chat':
            # chat 模式不需要特殊提示詞
            return "一般文字回應，無需情緒標籤"
        else:
            print(f"⚠️  未知的 output_format: {output_format}，使用預設")
            return "一般文字回應，無需情緒標籤"
        
        # 檢查文件是否存在
        if not prompt_file.exists():
            print(f"⚠️  提示詞文件不存在：{prompt_file}")
            return "一般文字回應，無需情緒標籤"
        
        # 讀取文件
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 存入快取
            self._cache[output_format] = content
            print(f"✅ 載入提示詞模板：{output_format} ({len(content)} 字)")
            return content
        
        except Exception as e:
            print(f"⚠️  讀取提示詞文件失敗：{e}")
            return "一般文字回應，無需情緒標籤"
    
    def load_prompt_for_llm1(self, output_format: str) -> str:
        """
        為 LLM1 載入提示詞模板（完整版，但 LLM1 只關注 language + 斷句）
        
        根據規範文件，LLM1 使用完整版提示詞模板，但實際上只會用到
        language 和斷句符號部分，不會用到 emotion。
        
        Args:
            output_format: 輸出格式
        
        Returns:
            提示詞模板內容（完整版）
        """
        # LLM1 使用完整版提示詞模板（一致性 > token 節省）
        return self.load_prompt(output_format)
    
    def load_prompt_for_llm2(self, output_format: str) -> str:
        """
        為 LLM2 載入提示詞模板（完整版，含 emotion）
        
        Args:
            output_format: 輸出格式
        
        Returns:
            提示詞模板內容（完整版）
        """
        # LLM2 使用完整版提示詞模板
        return self.load_prompt(output_format)
    
    def clear_cache(self):
        """清空快取（用於開發環境重新載入）"""
        self._cache.clear()
        print("🔄 已清空提示詞快取")
    
    def get_prompt_path(self, output_format: str) -> Optional[Path]:
        """
        取得提示詞文件路徑
        
        Args:
            output_format: 輸出格式
        
        Returns:
            文件路徑，如果不存在則返回 None
        """
        if output_format == 'virtual_human':
            return self.prompts_path / "virtual-human-output.md"
        return None
