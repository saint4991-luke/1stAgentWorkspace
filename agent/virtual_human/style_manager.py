"""
風格 Prompt 管理器 - 載入並快取風格文件

載入 Markdown 格式的風格定義文件，提供快取機制。
"""

from pathlib import Path
from typing import Dict, Optional, List


class StyleManager:
    """風格 Prompt 管理器"""
    
    def __init__(self, style_base: str = "/styles"):
        """
        初始化 StyleManager
        
        Args:
            style_base: 風格文件基礎路徑
        """
        self.style_base = Path(style_base)
        self._cache: Dict[str, str] = {}
        print(f"✅ StyleManager 初始化完成 (base: {style_base})")
    
    def load_style(self, style_path: str) -> Optional[str]:
        """
        載入風格 Prompt（從快取或文件）
        
        Args:
            style_path: 風格文件路徑（如 "/styles/ubichan/system_prompt.md"）
        
        Returns:
            風格內容，如果失敗則返回 None
        """
        # 檢查快取
        if style_path in self._cache:
            print(f"📖 [快取] 載入風格：{style_path}")
            return self._cache[style_path]
        
        # 從文件載入
        style_file = Path(style_path)
        if not style_file.exists():
            print(f"❌ 風格文件不存在：{style_file}")
            return None
        
        try:
            with open(style_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 存入快取
            self._cache[style_path] = content
            print(f"📖 載入風格：{style_path} ({len(content)} 字)")
            
            return content
        
        except Exception as e:
            print(f"❌ 載入風格失敗 {style_path}: {e}")
            return None
    
    def get_available_styles(self) -> List[str]:
        """
        取得所有可用的風格 ID
        
        Returns:
            風格 ID 列表
        """
        if not self.style_base.exists():
            return []
        
        styles = []
        for style_dir in self.style_base.iterdir():
            if style_dir.is_dir():
                style_file = style_dir / "system_prompt.md"
                if style_file.exists():
                    styles.append(style_dir.name)
        
        return styles
    
    def reload(self, style_path: str = None):
        """
        重新載入風格文件（用於開發環境）
        
        Args:
            style_path: 指定重新載入的路徑，如果為 None 則清空快取
        """
        if style_path:
            # 重新載入單一風格
            if style_path in self._cache:
                del self._cache[style_path]
                print(f"🔄 清除風格快取：{style_path}")
        else:
            # 清空所有快取
            self._cache.clear()
            print("🔄 清除所有風格快取")
    
    def get_stats(self) -> Dict:
        """
        取得統計資訊
        
        Returns:
            統計字典
        """
        return {
            'cached_styles': len(self._cache),
            'available_styles': len(self.get_available_styles())
        }
