#!/usr/bin/env python3
"""
🦐 蝦米 Agent v3.2.1 - LLM Provider 工廠

根據配置創建對應的 LLM Provider 實例
"""

import os
from typing import Dict, Optional
from llm_providers import LLMProvider, OpenAIProvider, UbisageProvider, AVAILABLE_PROVIDERS


def create_provider(
    provider_type: Optional[str] = None,
    config: Optional[Dict] = None
) -> LLMProvider:
    """
    工廠方法：根據類型創建 LLM Provider
    
    Args:
        provider_type: Provider 類型 ("openai", "ubisage")
                      如果為 None，從環境變數 LLM_PROVIDER 讀取
        config: Provider 配置字典
               如果為 None，從環境變數讀取
    
    Returns:
        LLMProvider 實例
    
    Raises:
        ValueError: 如果 Provider 類型無效或配置不完整
    
    Example:
        # 使用環境變數
        provider = create_provider()
        
        # 手動指定
        provider = create_provider(
            provider_type="openai",
            config={
                "model": "Qwen/Qwen3.5-397B-A17B-FP8",
                "api_key": "xxx",
                "base_url": "http://116.50.47.234:8081/v1"
            }
        )
    """
    
    # 1. 確定 Provider 類型
    if provider_type is None:
        provider_type = os.getenv("LLM_PROVIDER", "openai").lower()
    
    # 2. 確定配置
    if config is None:
        config = _load_config_from_env(provider_type)
    
    # 3. 創建 Provider 實例
    if provider_type == "openai":
        return _create_openai_provider(config)
    elif provider_type == "ubisage":
        return _create_ubisage_provider(config)
    else:
        # 嘗試從註冊表獲取
        if provider_type in AVAILABLE_PROVIDERS:
            provider_class = AVAILABLE_PROVIDERS[provider_type]
            return provider_class(**config)
        else:
            available = ", ".join(AVAILABLE_PROVIDERS.keys())
            raise ValueError(
                f"未知的 Provider 類型：{provider_type}\n"
                f"可用的 Provider: {available}"
            )


def _load_config_from_env(provider_type: str) -> Dict:
    """從環境變數載入配置"""
    
    config = {
        "model": os.getenv("OPENAI_MODEL", ""),
    }
    
    if provider_type == "openai":
        config.update({
            "api_key": os.getenv("OPENAI_API_KEY", ""),
            "base_url": os.getenv("OPENAI_BASE_URL", ""),
            "max_tokens": int(os.getenv("MAX_TOKENS", "4096")),
            "timeout": float(os.getenv("REQUEST_TIMEOUT", "30.0")),
        })
    
    elif provider_type == "ubisage":
        config.update({
            "api_key": os.getenv("UBISAGE_API_KEY", ""),
            "grant_url": os.getenv("UBISAGE_GRANT_URL", "https://sage-stg.ubitus.ai/ubillm/api/v1/resource/grant"),
        })
    
    return config


def _create_openai_provider(config: Dict) -> OpenAIProvider:
    """創建 OpenAI Provider"""
    
    # 驗證必要配置
    required = ["model", "api_key", "base_url"]
    missing = [key for key in required if not config.get(key)]
    
    if missing:
        raise ValueError(
            f"OpenAI Provider 缺少必要配置：{', '.join(missing)}\n"
            f"請設置環境變數：LLM_MODEL, OPENAI_API_KEY, OPENAI_BASE_URL"
        )
    
    return OpenAIProvider(**config)


def _create_ubisage_provider(config: Dict) -> UbisageProvider:
    """創建 Ubisage Provider"""
    
    # 驗證必要配置
    required = ["model", "api_key"]
    missing = [key for key in required if not config.get(key)]
    
    if missing:
        raise ValueError(
            f"Ubisage Provider 缺少必要配置：{', '.join(missing)}\n"
            f"請設置環境變數：LLM_MODEL, UBISAGE_API_KEY"
        )
    
    return UbisageProvider(**config)


def get_default_provider_type() -> str:
    """獲取預設的 Provider 類型"""
    return os.getenv("LLM_PROVIDER", "openai").lower()


def is_provider_available(provider_type: str) -> bool:
    """檢查 Provider 是否可用"""
    return provider_type in AVAILABLE_PROVIDERS


def list_available_providers() -> list:
    """列出所有可用的 Provider 類型"""
    return list(AVAILABLE_PROVIDERS.keys())
