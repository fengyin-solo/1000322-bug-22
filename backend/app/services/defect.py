"""缺陷登记业务规则：定级口径、状态流转与统计口径都收在这里。

定级规则全模块唯一：按缺陷类型与严重等级查处理期限上限（天），
列表、详情、导出、统计卡全部复用同一份口径，不允许第二套算法。
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.store import store

MODULE = "defect"
REQUIRED_FIELDS = ["缺陷编号", "所属设备", "缺陷类型"]
EXTRA_FIELDS = ["严重等级", "发现时间", "发现人"]
STATUS_ORDER = ["待定级", "已定级", "处理中", "已闭环", "已挂起"]
ACTION_RULES = {"确认定级": "已定级", "提交闭环": "已闭环", "挂起缺陷": "已挂起"}
NEGATIVE_ACTIONS: list[str] = []
CLOSED_STATUS = "已闭环"
# 已闭环、已挂起都不再计入看板待处理
INACTIVE_STATUSES = {"已闭环", "已挂起"}
# 确认定级只允许从未进入处理环节的状态发起，避免处理中被打回
GRADEABLE_STATUSES = {"待定级", "已定级"}

# 唯一定级规则：缺陷类型 × 严重等级 -> 处理期限上限（天）
GRADE_DEADLINE_DAYS: dict[str, dict[str, int]] = {
    "组件缺陷": {"危急": 3, "严重": 7, "一般": 30},
    "逆变器缺陷": {"危急": 1, "严重": 3, "一般": 15},
    "汇流箱缺陷": {"危急": 1, "严重": 5, "一般": 15},
    "支架缺陷": {"危急": 7, "严重": 15, "一般": 60},
    "电缆缺陷": {"危急": 1, "严重": 7, "一般": 30},
}


def resolve_deadline_days(defect_type: str, severity: str) -> int | None:
    """按唯一定级规则查处理期限上限（天）；类型或等级不在规则内时返回 None。"""
    return GRADE_DEADLINE_DAYS.get(defect_type, {}).get(severity)


def compute_deadline(found_at: str, days: int) -> str | None:
    """发现时间 + 期限天数 = 处理期限；发现时间无法解析时返回 None。"""
    try:
        start = date.fromisoformat(found_at)
    except ValueError:
        return None
    return (start + timedelta(days=days)).isoformat()


def _parse_day(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value or "").strip())
    except ValueError:
        return None


class DefectService:
    def _present(self, row: dict[str, Any]) -> dict[str, Any]:
        """对外输出前统一口径：缺陷状态跟随内部状态，处理期限按定级规则重算。"""
        item = dict(row)
        item["缺陷状态"] = str(item.get("status") or item.get("缺陷状态") or "")
        days = resolve_deadline_days(
            str(item.get("缺陷类型") or "").strip(),
            str(item.get("严重等级") or "").strip(),
        )
        if days is not None:
            deadline = compute_deadline(str(item.get("发现时间") or "").strip(), days)
            if deadline:
                item["处理期限"] = deadline
        return item

    def _is_overdue(self, row: dict[str, Any], today: date) -> bool:
        """超期未闭环：状态不是已闭环，且按统一口径算出的处理期限早于今天。"""
        if row.get("status") == CLOSED_STATUS:
            return False
        deadline = _parse_day(self._present(row).get("处理期限"))
        return deadline is not None and deadline < today

    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("缺陷编号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return [self._present(row) for row in rows[start:start + size]], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        row = store.find(MODULE, entry_id)
        return self._present(row) if row is not None else None

    def stats(self) -> list[dict[str, Any]]:
        """统计卡口径：每次按当前列表实时重算，不做缓存。"""
        rows = store.rows(MODULE)
        today = date.today()
        return [
            {"label": "待定级缺陷", "value": sum(1 for row in rows if row.get("status") == "待定级")},
            {"label": "处理中缺陷", "value": sum(1 for row in rows if row.get("status") == "处理中")},
            {"label": "超期未闭环", "value": sum(1 for row in rows if self._is_overdue(row, today))},
        ]

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, f"缺少必填字段：{'、'.join(missing)}"
        defect_type = str(values.get("缺陷类型") or "").strip()
        severity = str(values.get("严重等级") or "").strip()
        found_at = str(values.get("发现时间") or "").strip() or date.today().isoformat()
        days = resolve_deadline_days(defect_type, severity)
        deadline = compute_deadline(found_at, days) if days is not None else None
        submitted = str(values.get("处理期限") or "").strip()
        if deadline and submitted and submitted != deadline:
            return None, f"处理期限「{submitted}」与定级规则口径「{deadline}」冲突，未保存"
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS + EXTRA_FIELDS})
        entry["发现时间"] = found_at
        if deadline:
            entry["处理期限"] = deadline
        elif submitted:
            entry["处理期限"] = submitted
        entry["status"] = STATUS_ORDER[0]
        entry["缺陷状态"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return self._present(entry), ""

    def run_action(
        self,
        entry_id: int,
        action: str,
        values: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"设备缺陷 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于缺陷登记可执行范围"
        if entry.get("status") == CLOSED_STATUS:
            return None, f"设备缺陷已闭环，不允许再执行「{action}」"
        if action == "确认定级":
            return self._confirm_grade(entry, values or {})
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["缺陷状态"] = target
        entry["pending"] = target not in INACTIVE_STATUSES
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return self._present(entry), f"设备缺陷已{action}"

    def _confirm_grade(
        self,
        entry: dict[str, Any],
        values: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, str]:
        """确认定级：按唯一规则重算处理期限，口径冲突的定级结果不允许保存。"""
        if entry.get("status") not in GRADEABLE_STATUSES:
            return None, f"设备缺陷当前为「{entry.get('status')}」，不允许重新定级"
        defect_type = str(values.get("缺陷类型") or entry.get("缺陷类型") or "").strip()
        severity = str(values.get("严重等级") or entry.get("严重等级") or "").strip()
        days = resolve_deadline_days(defect_type, severity)
        if days is None:
            return None, f"缺陷类型「{defect_type}」与严重等级「{severity}」不在定级规则内，请按统一口径修正后再确认定级"
        found_at = str(entry.get("发现时间") or "").strip() or date.today().isoformat()
        deadline = compute_deadline(found_at, days)
        submitted = str(values.get("处理期限") or "").strip()
        if submitted and deadline and submitted != deadline:
            return None, f"处理期限「{submitted}」与定级规则口径「{deadline}」冲突，未保存"
        entry["缺陷类型"] = defect_type
        entry["严重等级"] = severity
        entry["发现时间"] = found_at
        entry["处理期限"] = deadline
        entry["status"] = "已定级"
        entry["缺陷状态"] = "已定级"
        entry["pending"] = True
        entry["abnormal"] = False
        return self._present(entry), "设备缺陷已确认定级"
