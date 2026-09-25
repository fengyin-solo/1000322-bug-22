"""接口出入参模型：列表分页、动作结果与各模块的明细结构。"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageResult(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int = 1
    size: int = 20


class DefectPageResult(PageResult[dict]):
    """缺陷登记分页结果：附带随当前列表实时重算的统计卡片。"""

    stats: dict[str, int] = Field(default_factory=dict)


class ActionResult(BaseModel):
    ok: bool
    message: str
    entry: dict[str, Any] | None = None


class EntryPayload(BaseModel):
    """登记或修改一条业务记录时提交的字段集合。"""

    values: dict[str, Any] = Field(default_factory=dict)
    remark: str | None = None



class StationEntry(BaseModel):
    """电站档案明细结构。"""

    field_0: str | None = None  # 电站编码
    field_1: str | None = None  # 电站名称
    field_2: str | None = None  # 装机容量
    field_3: str | None = None  # 并网电压等级
    field_4: str | None = None  # 所属区域
    field_5: str | None = None  # 投运日期
    field_6: str | None = None  # 运维班组
    field_7: str | None = None  # 电站状态

class ArrayEntry(BaseModel):
    """方阵明细结构。"""

    field_0: str | None = None  # 方阵编号
    field_1: str | None = None  # 方阵名称
    field_2: str | None = None  # 组件型号
    field_3: str | None = None  # 组件数量
    field_4: str | None = None  # 安装倾角
    field_5: str | None = None  # 朝向方位
    field_6: str | None = None  # 所属电站
    field_7: str | None = None  # 方阵状态

class InverterEntry(BaseModel):
    """逆变器明细结构。"""

    field_0: str | None = None  # 设备编号
    field_1: str | None = None  # 设备型号
    field_2: str | None = None  # 额定功率
    field_3: str | None = None  # 转换效率
    field_4: str | None = None  # 所属方阵
    field_5: str | None = None  # 通讯地址
    field_6: str | None = None  # 投运日期
    field_7: str | None = None  # 运行状态

class CombinerEntry(BaseModel):
    """汇流箱明细结构。"""

    field_0: str | None = None  # 汇流箱编号
    field_1: str | None = None  # 接入组串数
    field_2: str | None = None  # 直流电压
    field_3: str | None = None  # 输出电流
    field_4: str | None = None  # 防雷模块状态
    field_5: str | None = None  # 所属方阵
    field_6: str | None = None  # 安装位置
    field_7: str | None = None  # 运行状态

class StringmonEntry(BaseModel):
    """组串明细结构。"""

    field_0: str | None = None  # 组串编号
    field_1: str | None = None  # 所属方阵
    field_2: str | None = None  # 实测电流
    field_3: str | None = None  # 实测电压
    field_4: str | None = None  # 功率偏差率
    field_5: str | None = None  # 采集时间
    field_6: str | None = None  # 告警等级
    field_7: str | None = None  # 监测状态

class IrradianceEntry(BaseModel):
    """辐照测点明细结构。"""

    field_0: str | None = None  # 测点编号
    field_1: str | None = None  # 测点位置
    field_2: str | None = None  # 总辐照度
    field_3: str | None = None  # 直射辐照度
    field_4: str | None = None  # 组件温度
    field_5: str | None = None  # 环境温度
    field_6: str | None = None  # 采集时间
    field_7: str | None = None  # 测点状态

class CleaningEntry(BaseModel):
    """清洗任务明细结构。"""

    field_0: str | None = None  # 任务编号
    field_1: str | None = None  # 清洗区域
    field_2: str | None = None  # 计划日期
    field_3: str | None = None  # 实际完成日
    field_4: str | None = None  # 用水量
    field_5: str | None = None  # 作业班组
    field_6: str | None = None  # 清洗方式
    field_7: str | None = None  # 任务状态

class InspectionEntry(BaseModel):
    """巡检单明细结构。"""

    field_0: str | None = None  # 巡检单号
    field_1: str | None = None  # 巡检类型
    field_2: str | None = None  # 巡检路线
    field_3: str | None = None  # 巡检人员
    field_4: str | None = None  # 开始时间
    field_5: str | None = None  # 发现问题数
    field_6: str | None = None  # 巡检周期
    field_7: str | None = None  # 巡检状态

class DefectEntry(BaseModel):
    """设备缺陷明细结构。"""

    field_0: str | None = None  # 缺陷编号
    field_1: str | None = None  # 所属设备
    field_2: str | None = None  # 缺陷类型
    field_3: str | None = None  # 严重等级
    field_4: str | None = None  # 发现时间
    field_5: str | None = None  # 发现人
    field_6: str | None = None  # 处理期限
    field_7: str | None = None  # 缺陷状态

class RepairEntry(BaseModel):
    """消缺单明细结构。"""

    field_0: str | None = None  # 消缺单号
    field_1: str | None = None  # 关联缺陷
    field_2: str | None = None  # 处理措施
    field_3: str | None = None  # 备件消耗
    field_4: str | None = None  # 处理人员
    field_5: str | None = None  # 完成时间
    field_6: str | None = None  # 验收人员
    field_7: str | None = None  # 处理状态

class SparepartEntry(BaseModel):
    """备件领用单明细结构。"""

    field_0: str | None = None  # 领用单号
    field_1: str | None = None  # 备件名称
    field_2: str | None = None  # 备件规格
    field_3: str | None = None  # 领用数量
    field_4: str | None = None  # 领用人员
    field_5: str | None = None  # 领用日期
    field_6: str | None = None  # 所属班组
    field_7: str | None = None  # 领用状态

class GenerationEntry(BaseModel):
    """发电记录明细结构。"""

    field_0: str | None = None  # 记录编号
    field_1: str | None = None  # 电站名称
    field_2: str | None = None  # 统计日期
    field_3: str | None = None  # 理论发电量
    field_4: str | None = None  # 实际发电量
    field_5: str | None = None  # 等效利用小时
    field_6: str | None = None  # 弃光电量
    field_7: str | None = None  # 记录状态

class CurtailEntry(BaseModel):
    """限电事件明细结构。"""

    field_0: str | None = None  # 事件编号
    field_1: str | None = None  # 所属电站
    field_2: str | None = None  # 限电原因
    field_3: str | None = None  # 限电开始时间
    field_4: str | None = None  # 限电结束时间
    field_5: str | None = None  # 损失电量
    field_6: str | None = None  # 调度指令号
    field_7: str | None = None  # 限电状态

class AlarmEntry(BaseModel):
    """告警事件明细结构。"""

    field_0: str | None = None  # 告警编号
    field_1: str | None = None  # 告警类型
    field_2: str | None = None  # 告警等级
    field_3: str | None = None  # 触发设备
    field_4: str | None = None  # 触发时间
    field_5: str | None = None  # 确认人员
    field_6: str | None = None  # 处置说明
    field_7: str | None = None  # 告警状态

class PermitEntry(BaseModel):
    """作业许可单明细结构。"""

    field_0: str | None = None  # 许可编号
    field_1: str | None = None  # 作业类型
    field_2: str | None = None  # 作业地点
    field_3: str | None = None  # 工作负责人
    field_4: str | None = None  # 安全措施
    field_5: str | None = None  # 许可时间
    field_6: str | None = None  # 有效期至
    field_7: str | None = None  # 许可状态

class ContractorEntry(BaseModel):
    """承包商档案明细结构。"""

    field_0: str | None = None  # 承包商编码
    field_1: str | None = None  # 承包商名称
    field_2: str | None = None  # 资质等级
    field_3: str | None = None  # 服务范围
    field_4: str | None = None  # 联系人
    field_5: str | None = None  # 联系电话
    field_6: str | None = None  # 合同到期日
    field_7: str | None = None  # 合作状态

class TrainingEntry(BaseModel):
    """培训计划明细结构。"""

    field_0: str | None = None  # 培训编号
    field_1: str | None = None  # 培训主题
    field_2: str | None = None  # 培训对象
    field_3: str | None = None  # 培训方式
    field_4: str | None = None  # 计划课时
    field_5: str | None = None  # 考核成绩
    field_6: str | None = None  # 培训日期
    field_7: str | None = None  # 培训状态

class SettlementEntry(BaseModel):
    """结算单明细结构。"""

    field_0: str | None = None  # 结算单号
    field_1: str | None = None  # 结算对象
    field_2: str | None = None  # 结算周期
    field_3: str | None = None  # 上网电量
    field_4: str | None = None  # 电价标准
    field_5: str | None = None  # 应结金额
    field_6: str | None = None  # 已付金额
    field_7: str | None = None  # 结算状态
