"""
ask.py - Ask Vault 路由
"""

from fastapi import APIRouter, Depends

from ..schemas import AskRequest, AskResponse
from ..security import require_read_token
from ..services.vault_service import ask as vault_ask

router = APIRouter(prefix="/ask", tags=["ask"])


@router.post("", response_model=AskResponse)
async def ask_vault(
    body: AskRequest,
    _token: str = Depends(require_read_token)
):
    """
    Ask Vault 问答。

    通过向量搜索获取相关笔记，调用 LLM 生成回答。
    """
    result = vault_ask(
        question=body.question,
        limit=body.limit,
        save_category=body.save_category
    )

    if not result.get("success", False):
        return AskResponse(
            success=False,
            query=body.question,
            answer="",
            references=[],
            notes_count=0,
            error=result.get("error", "Unknown error")
        )

    return AskResponse(
        success=True,
        query=result.get("query", body.question),
        answer=result.get("answer", ""),
        references=result.get("references", []),
        notes_count=result.get("notes_count", 0),
        saved=result.get("saved")
    )