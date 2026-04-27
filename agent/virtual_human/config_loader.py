"""
CONFIG 載入器 - 預先載入所有虛擬人配置到記憶體

在 Server 啟動時載入所有 CONFIG，提供 O(1) 查詢性能。
使用 YAML 格式，支援註解且人類可讀性高。
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class ConfigLoader:
    """虛擬人 CONFIG 載入器（YAML 格式）"""
    
    def __init__(self, personas_path: str = "/workspace/personas"):
        """
        初始化 ConfigLoader
        
        Args:
            personas_path: personas 目錄路徑
        """
        self.personas_path = Path(personas_path)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load_all()
    
    def _load_all(self):
        """預先載入所有 CONFIG 到記憶體"""
        if not self.personas_path.exists():
            print(f"⚠️  personas 目錄不存在：{self.personas_path}")
            return
        
        # 掃描所有 persona 目錄（跳過 TEMPLATE）
        persona_dirs = [d for d in self.personas_path.iterdir() if d.is_dir() and d.name != 'TEMPLATE']
        if not persona_dirs:
            print(f"⚠️  personas 目錄為空：{self.personas_path}")
            return
        
        for persona_dir in persona_dirs:
            config_file = persona_dir / "config.yaml"
            if not config_file.exists():
                print(f"⚠️  缺少 config.yaml: {persona_dir}")
                continue
            
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                # 驗證必要欄位
                self._validate(config, str(config_file))
                
                # 存入快取（使用 persona_id 作為 key）
                config_id = config.get('persona_id', persona_dir.name)
                self._cache[config_id] = config
                print(f"✅ 載入 CONFIG: {config_id}")
            
            except Exception as e:
                print(f"❌ 載入 CONFIG 失敗 {config_file}: {e}")
        
        print(f"✅ 預先載入 {len(self._cache)} 個虛擬人配置")
    
    def _validate(self, config: Dict[str, Any], filename: str):
        """
        驗證 CONFIG 必要欄位（YAML v2.0 結構）
        
        新結構：
        ```yaml
        persona_id: ubichan
        display_name: 優必醬
        
        style:
          file: style.md
        
        output_format: virtual_human  # virtual_human | chat
        
        knowledge:
          enabled: true
          folders:
            - products/
            - company/
        
        metadata:
          version: "2.0"
        ```
        
        Args:
            config: CONFIG 字典
            filename: 檔案名稱（用於錯誤訊息）
        """
        # 必要欄位：persona_id, style, output_format
        required_fields = ['persona_id', 'style', 'output_format']
        missing = [field for field in required_fields if field not in config]
        
        if missing:
            raise ValueError(f"{filename}: 缺少必要欄位：{', '.join(missing)}")
        
        # 驗證 style 結構
        if 'style' in config:
            if not isinstance(config['style'], dict):
                raise ValueError(f"{filename}: style 必須是物件")
            if 'file' not in config['style']:
                raise ValueError(f"{filename}: style 缺少 file 欄位")
        
        # 驗證 output_format
        if 'output_format' in config:
            valid_formats = ['virtual_human', 'chat']
            if config['output_format'] not in valid_formats:
                raise ValueError(f"{filename}: output_format 必須是 {valid_formats} 之一")
        
        # 驗證 knowledge（可選）
        if 'knowledge' in config:
            if not isinstance(config['knowledge'], dict):
                raise ValueError(f"{filename}: knowledge 必須是物件")
            if 'enabled' not in config['knowledge']:
                raise ValueError(f"{filename}: knowledge 缺少 enabled 欄位")
            if config['knowledge'].get('enabled') and 'folders' not in config['knowledge']:
                raise ValueError(f"{filename}: knowledge.enabled=true 時需要 folders 欄位")
    
    def get(self, config_id: str) -> Optional[Dict[str, Any]]:
        """
        從快取取得 CONFIG（O(1)）
        
        Args:
            config_id: 虛擬人 ID（即 config 中的 name 欄位）
        
        Returns:
            CONFIG 字典，如果不存在則返回 None
        """
        if config_id not in self._cache:
            print(f"⚠️  未知的虛擬人 ID: {config_id}")
            return None
        
        return self._cache[config_id]
    
    def has(self, config_id: str) -> bool:
        """
        檢查 CONFIG 是否存在
        
        Args:
            config_id: 虛擬人 ID
        
        Returns:
            True 如果存在
        """
        return config_id in self._cache
    
    def get_all_ids(self) -> list:
        """
        取得所有虛擬人 ID 列表
        
        Returns:
            ID 列表
        """
        return list(self._cache.keys())
    
    def reload(self, config_id: str = None):
        """
        重新載入 CONFIG（用於開發環境）
        
        Args:
            config_id: 指定重新載入的 ID，如果為 None 則重新載入所有
        """
        if config_id:
            # 重新載入單一 CONFIG
            config_file = self.personas_path / config_id / "config.yaml"
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                self._validate(config, str(config_file))
                self._cache[config_id] = config
                print(f"🔄 重新載入 CONFIG: {config_id}")
        else:
            # 重新載入所有
            self._cache.clear()
            self._load_all()
