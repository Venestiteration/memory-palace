"""
llm_provider.py - LLM Provider 抽象层

定义 LLMProvider 接口，供 ask_vault.py、atomize_note.py、generate_daily_brief.py 等使用。
未来可替换为 Anthropic、OpenAI、本地模型（Ollama），无需修改调用方代码。

用法：
  from llm_provider import get_llm_provider
  provider = get_llm_provider()
  response = provider.chat(system_prompt, user_message)
"""

import os
import re
from abc import ABC, abstractmethod
from typing import Optional


class LLMProvider(ABC):
    """LLM Provider 抽象基类"""

    @abstractmethod
    def chat(self, system_prompt: str, user_message: str, **kwargs) -> str:
        """
        发送对话请求到 LLM。

        Args:
            system_prompt: 系统提示词
            user_message: 用户消息
            **kwargs: 提供商特定参数（如 temperature, max_tokens）

        Returns:
            LLM 生成的文本回复
        """
        raise NotImplementedError

    @abstractmethod
    def name(self) -> str:
        """返回提供商名称"""
        raise NotImplementedError


class MiniMaxLLMProvider(LLMProvider):
    """MiniMax LLM Provider"""

    MODEL_NAME = "MiniMax-M2.7"
    BASE_URL = "https://api.minimax.chat/v1"
    DEFAULT_MAX_TOKENS = 2048
    DEFAULT_TEMPERATURE = 0.3

    def __init__(self, api_key: Optional[str] = None):
        try:
            import requests
        except ImportError:
            raise ImportError("缺少依赖: requests。请运行: pip install requests")

        self.api_key = api_key or os.environ.get("MINIMAX_API_KEY")
        if not self.api_key:
            raise ValueError(
                "环境变量 MINIMAX_API_KEY 未设置\n"
                "用法: export MINIMAX_API_KEY=sk-cp-..."
            )

    def name(self) -> str:
        return f"MiniMax ({self.MODEL_NAME})"

    def chat(self, system_prompt: str, user_message: str, **kwargs) -> str:
        import requests

        max_tokens = kwargs.get("max_tokens", self.DEFAULT_MAX_TOKENS)
        temperature = kwargs.get("temperature", self.DEFAULT_TEMPERATURE)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        response = requests.post(
            f"{self.BASE_URL}/chat/completions",
            headers=headers,
            json=data,
            timeout=120
        )
        response.raise_for_status()
        result = response.json()

        raw_text = result["choices"][0]["message"]["content"].strip()

        # 移除 thinking block（如有）
        raw_text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL)

        return raw_text


class AnthropicLLMProvider(LLMProvider):
    """Anthropic LLM Provider（备选）"""

    MODEL_NAME = "claude-sonnet-4-20250514"
    BASE_URL = "https://api.anthropic.com/v1"
    DEFAULT_MAX_TOKENS = 2048
    DEFAULT_TEMPERATURE = 0.3

    def __init__(self, api_key: Optional[str] = None):
        try:
            import requests
        except ImportError:
            raise ImportError("缺少依赖: requests。请运行: pip install requests")

        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "环境变量 ANTHROPIC_API_KEY 未设置\n"
                "用法: export ANTHROPIC_API_KEY=sk-ant-..."
            )

    def name(self) -> str:
        return f"Anthropic ({self.MODEL_NAME})"

    def chat(self, system_prompt: str, user_message: str, **kwargs) -> str:
        import requests

        max_tokens = kwargs.get("max_tokens", self.DEFAULT_MAX_TOKENS)
        temperature = kwargs.get("temperature", self.DEFAULT_TEMPERATURE)

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.MODEL_NAME,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_message}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        response = requests.post(
            f"{self.BASE_URL}/messages",
            headers=headers,
            json=data,
            timeout=120
        )
        response.raise_for_status()
        result = response.json()

        return result["content"][0]["text"].strip()


def get_llm_provider() -> LLMProvider:
    """
    根据环境变量自动选择 LLM Provider。

    优先级：
      - MINIMAX_API_KEY → MiniMaxLLMProvider（优先）
      - ANTHROPIC_API_KEY → AnthropicLLMProvider（备选）

    未来扩展：
      - OPENAI_API_KEY → OpenAILLMProvider
      - OLLAMA_BASE_URL → LocalOllamaProvider
    """
    if os.environ.get("MINIMAX_API_KEY"):
        return MiniMaxLLMProvider()

    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicLLMProvider()

    raise ValueError(
        "未找到可用的 LLM Provider。"
        "请设置 MINIMAX_API_KEY 或 ANTHROPIC_API_KEY 环境变量。"
    )