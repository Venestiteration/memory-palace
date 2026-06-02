"""
embedding_provider.py - Embedding Provider 抽象层

定义 EmbeddingProvider 接口，供 build_vector_index.py 和 search_notes.py 使用。
未来可替换为 Ollama 等本地模型，无需修改调用方代码。

用法：
  from embedding_provider import get_embedding_provider
  provider = get_embedding_provider()  # 从环境变量自动选择
"""

import os
from abc import ABC, abstractmethod
from typing import Optional


class EmbeddingProvider(ABC):
    """Embedding Provider 抽象基类"""

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """
        生成文本的 embedding 向量。

        Args:
            text: 输入文本（一般不超过 8192 tokens）

        Returns:
            embedding 向量，float 列表
        """
        raise NotImplementedError

    @abstractmethod
    def dimension(self) -> int:
        """返回 embedding 向量的维度"""
        raise NotImplementedError


class DashScopeEmbeddingProvider(EmbeddingProvider):
    """阿里云百炼（DashScope）Embedding Provider"""

    MODEL_NAME = "text-embedding-v4"
    BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DIMENSION = 1024

    def __init__(self, api_key: Optional[str] = None):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "缺少依赖: openai。请运行: pip install openai"
            )

        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "环境变量 DASHSCOPE_API_KEY 未设置\n"
                "用法: export DASHSCOPE_API_KEY=sk-..."
            )

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.BASE_URL
        )

    def dimension(self) -> int:
        return self.DIMENSION

    def embed(self, text: str) -> list[float]:
        completion = self.client.embeddings.create(
            model=self.MODEL_NAME,
            input=text[:8192]  # 截断避免超限
        )
        result = completion.model_dump()
        return result["data"][0]["embedding"]


class MiniMaxEmbeddingProvider(EmbeddingProvider):
    """MiniMax Embedding Provider（备选，使用 MiniMax Embedding API）"""

    MODEL_NAME = "embo"
    BASE_URL = "https://api.minimax.chat/v1"
    DIMENSION = 1024

    def __init__(self, api_key: Optional[str] = None):
        try:
            import requests
        except ImportError:
            raise ImportError(
                "缺少依赖: requests。请运行: pip install requests"
            )
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "环境变量 ANTHROPIC_API_KEY 未设置\n"
                "用法: export ANTHROPIC_API_KEY=sk-cp-..."
            )

    def dimension(self) -> int:
        return self.DIMENSION

    def embed(self, text: str) -> list[float]:
        import requests

        url = f"{self.BASE_URL}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "embedding_v1",
            "texts": [text[:8192]],
            "type": "document"
        }

        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()

        if result.get("base_resp", {}).get("status_code") != 0:
            raise RuntimeError(
                f"Embedding API 错误: {result['base_resp']['status_msg']}"
            )

        vectors = result.get("vectors", [])
        if not vectors or not vectors[0]:
            raise RuntimeError("Embedding API 返回空向量")
        return vectors[0]


def get_embedding_provider() -> EmbeddingProvider:
    """
    根据环境变量自动选择 Embedding Provider。

    优先级：
      - DASHSCOPE_API_KEY → DashScopeEmbeddingProvider（优先）
      - ANTHROPIC_API_KEY → MiniMaxEmbeddingProvider（备选）

    未来扩展：
      - OLLAMA_BASE_URL 存在 → LocalOllamaProvider
    """
    if os.environ.get("DASHSCOPE_API_KEY"):
        return DashScopeEmbeddingProvider()

    if os.environ.get("ANTHROPIC_API_KEY"):
        return MiniMaxEmbeddingProvider()

    raise ValueError(
        "未找到可用的 Embedding Provider。"
        "请设置 DASHSCOPE_API_KEY 或 ANTHROPIC_API_KEY 环境变量。"
    )