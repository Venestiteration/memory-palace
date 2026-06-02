"""
search.py - 搜索路由
"""

from fastapi import APIRouter, Depends

from ..schemas import SearchRequest, SearchResponse, SearchResult
from ..security import require_read_token
from ..services.command_runner import run_python_script
import json

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search(
    q: str,
    limit: int = 5,
    type_filter: str = None,
    _token: str = Depends(require_read_token)
):
    """
    语义搜索笔记。
    """
    args = [q, "--limit", str(limit), "--json"]
    if type_filter:
        args.extend(["--type", type_filter])

    returncode, stdout, stderr = run_python_script("search_notes.py", args)

    if returncode != 0:
        return SearchResponse(
            success=False,
            query=q,
            results=[],
            total=0
        )

    try:
        data = json.loads(stdout)

        results = []
        for item in data.get("results", []):
            results.append(SearchResult(
                path=item.get("path", ""),
                title=item.get("title", ""),
                score=item.get("score", 0.0),
                snippet=item.get("snippet", ""),
                type=item.get("type", "")
            ))

        return SearchResponse(
            success=True,
            query=q,
            results=results,
            total=data.get("total", 0)
        )
    except Exception:
        return SearchResponse(
            success=False,
            query=q,
            results=[],
            total=0
        )