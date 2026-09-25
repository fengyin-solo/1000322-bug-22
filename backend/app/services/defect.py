"""缺陷登记业务规则：定级口径、状态流转、字段校验与筛选统计都收在这里。

定级与处理期限只有这一份口径（GRADING_RULES / 处理期限上限），
列表、详情、导出、统计与定级提交校验全部走 resolve_deadline，避免各处各算。
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.store import store

MODULE = "defect"
REQUIRED_FIELDS = ["缺陷编号", "所属设备", "缺陷类型"]
OPTIONAL_FIELDS = ["严重等级", "发现时间", "发现人"]
STATUS_ORDER = ["待定级", "已定级", "处理中", "已闭环", "已挂起"]
ACTION_RULES = {"确认定级": "已定级", "提交闭环": "已闭环", "挂起缺陷": "已挂起"}
NEGATIVE_ACTIONS = []

# 终态：已闭环不允许再被任何动作改回；已挂起维持原有挂起语义
CLOSED_STATUS = "已闭环"
SUSPENDED_STATUS = "已挂起"
PENDING_GRADING_STATUS = "待定级"
GRADED_STATUS = "已定级"

# 定级口径（唯一一份）：缺陷类型 + 严重等级 -> 处理期限上限（自然日）。
# 未列出的缺陷类型按 DEFAULT_DEADLINE_DAYS 兜底，保证口径确定、不会漏管。
SEVERITY_LEVELS = ["紧急", "严重", "一般"]
GRADING_RULES: dict[str, dict[str, int]] = {
    "设备缺陷": {"紧急": 1, "严重": 3, "一般": 7},
    "安全缺陷": {"紧急": 1, "严重": 2, "一般": 5},
    "管理缺陷": {"紧急": 2, "严重": 5, "一般": 15},
}
DEFAULT_DEADLINE_DAYS: dict[str, int] = {"紧急": 1, "严重": 3, "一般": 7}

# 未定级时处理期限占位（列表与详情保持一致，不显示任何按行存的旧口径）
UNGRADED_DEADLINE = "—"


def deadline_days(defect_type: str | None, severity: str | None) -> int | None:
    """按缺陷类型与严重等级取处理期限上限；未定级（等级不在口径内）返回 None。"""
    if severity not in SEVERITY_LEVELS:
        return None
    type_rules = GRADING_RULES.get(str(defect_type or "").strip())
    return type_rules.get(severity) if type_rules else DEFAULT_DEADLINE_DAYS[severity]


def _parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if len(text) < 10:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def resolve_deadline(entry: dict[str, Any]) -> str:
    """按统一口径由「缺陷类型 + 严重等级 + 发现时间」算处理期限。

    任何入口都不允许自行另算；未定级或日期缺失时返回统一占位。
    """
    days = deadline_days(entry.get("缺陷类型"), entry.get("严重等级"))
    found_on = _parse_date(entry.get("发现时间"))
    if days is None or found_on is None:
        return UNGRADED_DEADLINE
    return (found_on + timedelta(days=days)).isoformat()


def is_overdue(entry: dict[str, Any], today: date | None = None) -> bool:
    """超期未闭环：未到闭环（挂起除外）且处理期限已过当天。"""
    if entry.get("status") in (CLOSED_STATUS, SUSPENDED_STATUS):
        return False
    deadline = _parse_date(resolve_deadline(entry))
    if deadline is None:
        return False
    return deadline < (today or date.today())


class DefectService:
    def _present(self, entry: dict[str, Any]) -> dict[str, Any]:
        """对外视图：处理期限永远按统一口径现算，不读行内旧值。"""
        view = dict(entry)
        view["处理期限"] = resolve_deadline(entry)
        view["缺陷状态"] = entry.get("status")
        return view

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
        page_rows = rows[start:start + size]
        return [self._present(row) for row in page_rows], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        entry = store.find(MODULE, entry_id)
        return self._present(entry) if entry is not None else None

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        for field in OPTIONAL_FIELDS:
            if str(values.get(field) or "").strip():
                entry[field] = values.get(field)
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return self._present(entry), []

    def grading_rules(self) -> dict[str, Any]:
        """定级口径只读视图：严重等级选项、期限上限表、兜底口径、未定级占位。"""
        return {
            "severityLevels": list(SEVERITY_LEVELS),
            "deadlineRules": {k: dict(v) for k, v in GRADING_RULES.items()},
            "defaultDeadlineDays": dict(DEFAULT_DEADLINE_DAYS),
            "ungracedPlaceholder": UNGRADED_DEADLINE,
        }

    def stats(self, *, keyword: str | None = None, status: str | None = None) -> dict[str, int]:
        """统计口径随当前列表过滤条件实时重算（统计全量匹配行，不受分页影响）。"""
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("缺陷编号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        return {
            "pendingGrading": sum(1 for row in rows if row.get("status") == PENDING_GRADING_STATUS),
            "inProgress": sum(1 for row in rows if row.get("status") == "处理中"),
            "overdue": sum(1 for row in rows if is_overdue(row)),
        }

    def run_action(self, entry_id: int, action: str, values: dict[str, Any] | None = None) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"设备缺陷 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于缺陷登记可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"

        # 闭环为终态：任何动作都不能把已闭环的缺陷改回其他状态
        if entry.get("status") == CLOSED_STATUS:
            return None, "设备缺陷已闭环，闭环结果不允许再修改"

        values = values or {}
        if action == "确认定级":
            message = self._apply_grading(entry, values)
            if message:
                return None, message
        elif action == "挂起缺陷":
            # 挂起动作照旧：未定级的缺陷还没有定级口径，不能直接挂起
            if entry.get("status") == PENDING_GRADING_STATUS:
                return None, "设备缺陷尚未定级，请先确认定级后再挂起"
            entry["status"] = SUSPENDED_STATUS
            entry["pending"] = False
        elif action == "提交闭环":
            # 提交闭环照旧：仍要求先定级，避免绕过口径直接闭环
            if entry.get("status") == PENDING_GRADING_STATUS:
                return None, "设备缺陷尚未定级，请先确认定级后再提交闭环"
            entry["status"] = CLOSED_STATUS
            entry["pending"] = False

        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return self._present(entry), f"设备缺陷已{action}"

    def _apply_grading(self, entry: dict[str, Any], values: dict[str, Any]) -> str:
        """执行定级：仅「待定级」可定级一次，等级与期限必须落在唯一口径内。"""
        if entry.get("status") != PENDING_GRADING_STATUS:
            return f"设备缺陷状态为「{entry.get('status')}」，定级口径唯一且不允许重复定级"
        severity = str(values.get("严重等级") or entry.get("严重等级") or "").strip()
        if severity not in SEVERITY_LEVELS:
            return f"严重等级「{severity or '空'}」不在定级口径内，可选：{'、'.join(SEVERITY_LEVELS)}"

        defect_type = str(values.get("缺陷类型") or entry.get("缺陷类型") or "").strip()
        submitted_type = str(values.get("缺陷类型") or "").strip()
        if submitted_type and submitted_type != str(entry.get("缺陷类型") or "").strip():
            return "定级动作不允许修改缺陷类型，缺陷类型与登记口径冲突"

        found_on = str(values.get("发现时间") or entry.get("发现时间") or "").strip()
        if not _parse_date(found_on):
            return "缺少有效的发现时间，无法按统一口径计算处理期限"

        days = deadline_days(defect_type, severity)
        if days is None:
            return f"缺陷类型「{defect_type}」与严重等级「{severity}」匹配不到处理期限口径"
        canonical_deadline = (_parse_date(found_on) + timedelta(days=days)).isoformat()

        submitted_deadline = str(values.get("处理期限") or "").strip()
        if submitted_deadline and submitted_deadline != canonical_deadline:
            return (
                f"提交的处理期限 {submitted_deadline} 与定级口径 {canonical_deadline} 冲突，"
                "请按统一口径定级"
            )

        # 校验通过：等级、类型、发现时间与期限全部以口径为准落库
        entry["严重等级"] = severity
        entry["缺陷类型"] = defect_type
        entry["发现时间"] = found_on[:10]
        entry["处理期限"] = canonical_deadline
        entry["status"] = GRADED_STATUS
        entry["pending"] = True
        return ""
