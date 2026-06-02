"""
schemas.py - Pydantic 模型定义
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "ok"
    timestamp: str
    version: str = "1.0.0"


class CaptureTextRequest(BaseModel):
    """文本捕获请求"""
    content: str = Field(..., min_length=1, max_length=10000)
    source: Optional[str] = "manual"
    title: Optional[str] = None
    tags: list[str] = []


class CaptureTextResponse(BaseModel):
    """文本捕获响应"""
    success: bool
    file: Optional[str] = None
    error: Optional[str] = None


class InboxItem(BaseModel):
    """Inbox 条目"""
    file: str
    created: str
    source: str
    type: str
    title: str
    suggested_action: str
    content_length: int


class InboxResponse(BaseModel):
    """Inbox 列表响应"""
    success: bool
    items: list[InboxItem]
    total: int


class AtomizeRequest(BaseModel):
    """原子化请求"""
    file: str = Field(..., description="文件路径")
    write: bool = Field(False, description="是否写入原子笔记")


class AtomizeResponse(BaseModel):
    """原子化响应"""
    success: bool
    source: str
    candidates_count: int
    written: Optional[list[dict]] = None
    error: Optional[str] = None


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., min_length=1)
    limit: int = Field(5, ge=1, le=50)
    type_filter: Optional[str] = None


class SearchResult(BaseModel):
    """搜索结果项"""
    path: str
    title: str
    score: float
    snippet: Optional[str] = None
    type: Optional[str] = None


class SearchResponse(BaseModel):
    """搜索响应"""
    success: bool
    query: str
    results: list[SearchResult]
    total: int


class AskRequest(BaseModel):
    """问答请求"""
    question: str = Field(..., min_length=1)
    limit: int = Field(5, ge=1, le=20)
    save_category: Optional[str] = None


class AskResponse(BaseModel):
    """问答响应"""
    success: bool
    query: str
    answer: str
    references: list[dict]
    notes_count: int
    saved: Optional[str] = None


class BriefResponse(BaseModel):
    """简报响应"""
    success: bool
    date: Optional[str] = None
    week: Optional[str] = None
    content: Optional[str] = None
    dry_run: bool = False
    error: Optional[str] = None


class GenerateBriefRequest(BaseModel):
    """生成简报请求"""
    date: Optional[str] = None
    week: Optional[str] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: Optional[str] = None


class CaptureWebClipRequest(BaseModel):
    """网页剪藏请求"""
    url: str = Field(..., min_length=1)
    title: Optional[str] = None
    content: Optional[str] = ""
    author: Optional[str] = None
    tags: list[str] = []


class CaptureVoiceRequest(BaseModel):
    """语音转录请求"""
    transcript: str = Field(..., min_length=1)
    title: Optional[str] = None
    tags: list[str] = []