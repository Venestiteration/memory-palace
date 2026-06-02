"""
inbox.py - Inbox 路由
"""

from fastapi import APIRouter, Depends

from ..schemas import InboxResponse, InboxItem
from ..security import require_read_token
from ..services.command_runner import run_python_script

router = APIRouter(prefix="/inbox", tags=["inbox"])


@router.get("", response_model=InboxResponse)
async def get_inbox(
    limit: int = 0,
    _token: str = Depends(require_read_token)
):
    """
    获取 Inbox 列表。
    """
    args = ["--json"]
    if limit > 0:
        args.extend(["--limit", str(limit)])

    returncode, stdout, stderr = run_python_script("process_inbox.py", args)

    if returncode != 0:
        return InboxResponse(
            success=False,
            items=[],
            total=0
        )

    import json
    try:
        items_data = json.loads(stdout)
        items = [InboxItem(**item) for item in items_data]
        return InboxResponse(
            success=True,
            items=items,
            total=len(items)
        )
    except Exception:
        return InboxResponse(
            success=False,
            items=[],
            total=0
        )