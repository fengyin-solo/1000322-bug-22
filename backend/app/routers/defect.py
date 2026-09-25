"""缺陷登记接口：维护设备缺陷，覆盖确认定级、提交闭环、挂起缺陷等动作。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, DefectPageResult, EntryPayload
from app.services.defect import DefectService

router = APIRouter(prefix="/api/defect", tags=["缺陷登记"])

service = DefectService()

LIST_FIELDS = ["缺陷编号", "所属设备", "缺陷类型", "严重等级", "发现时间", "发现人", "处理期限", "缺陷状态"]
STATUSES = ["待定级", "已定级", "处理中", "已闭环", "已挂起"]


@router.get("", response_model=DefectPageResult)
def list_entries(
    keyword: str | None = Query(default=None, description="按缺陷编号检索"),
    status: str | None = Query(default=None, description="待定级、已定级、处理中、已闭环、已挂起"),
    page: int = 1,
    size: int = 20,
) -> DefectPageResult:
    """按缺陷编号与状态过滤缺陷登记列表；没有数据时返回空页，不报错。

    处理期限按后端唯一定级口径实时计算，stats 随当前过滤条件实时重算。
    """
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(keyword=keyword, status=status, page=page, size=size)
    stats = service.stats(keyword=keyword, status=status)
    return DefectPageResult(items=items, total=total, page=page, size=size, stats=stats)


@router.get("/grading-rules")
def grading_rules() -> dict[str, Any]:
    """定级口径只读接口：前端选项与期限上限以后端这一份为准，避免各处自定规则。"""
    return service.grading_rules()


@router.get("/export")
def export_entries(
    keyword: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """导出缺陷登记清单：返回当前过滤条件下的全量数据，处理期限与列表同口径。"""
    items, total = service.list_entries(keyword=keyword, status=status, page=1, size=10000)
    return {"module": "defect", "total": total, "items": items}


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条设备缺陷明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"设备缺陷 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条设备缺陷，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="设备缺陷已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条设备缺陷执行确认定级、提交闭环、挂起缺陷；不允许的动作会被拦下并说明原因。

    确认定级时校验严重等级与处理期限是否符合统一口径，口径冲突拒绝保存；
    已闭环为终态，任何动作都不能把它改回其他状态。
    """
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action, payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
