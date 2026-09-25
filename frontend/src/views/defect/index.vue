<template>
  <section class="page" data-module="defect">
    <header class="page-head">
      <div>
        <h2>缺陷登记管理</h2>
        <p class="page-desc">维护设备缺陷，围绕缺陷编号、所属设备、缺陷类型、严重等级做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记设备缺陷</button>
        <button class="btn" type="button" @click="exportRows">导出缺陷登记清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="filters[field]" :placeholder="`按${field}检索`" />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
          <td class="row-actions">
            <button
              v-for="action in actions"
              :key="action"
              class="link"
              type="button"
              :disabled="isActionDisabled(action, row)"
              :title="actionDisabledReason(action, row)"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无缺陷登记数据，可先登记设备缺陷</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条缺陷登记记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>
type GradingRules = {
  severityLevels: string[]
  deadlineRules: Record<string, Record<string, number>>
  defaultDeadlineDays: Record<string, number>
}

const ENDPOINT = '/api/defect'
const columns = ["缺陷编号", "所属设备", "缺陷类型", "严重等级", "发现时间", "发现人", "处理期限", "缺陷状态"]
const actions = ["确认定级", "提交闭环", "挂起缺陷"]
const statuses = ["待定级", "已定级", "处理中", "已闭环", "已挂起"]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = columns.slice(0, 3)
const gradingRules = ref<GradingRules | null>(null)

// 统计卡片：值由后端按当前列表过滤条件实时返回，前端不另算一套
const stats = ref([
  { label: "待定级缺陷", value: 0 },
  { label: "处理中缺陷", value: 0 },
  { label: "超期未闭环", value: 0 },
])

function applyStats(payload: { stats?: Record<string, number> }) {
  const next = payload.stats ?? {}
  stats.value = [
    { label: "待定级缺陷", value: next.pendingGrading ?? 0 },
    { label: "处理中缺陷", value: next.inProgress ?? 0 },
    { label: "超期未闭环", value: next.overdue ?? 0 },
  ]
}

function resetFilters() {
  filters.value = {}
  void reload()
}

function exportRows() {
  const query = new URLSearchParams(filters.value as Record<string, string>).toString()
  window.open(`${ENDPOINT}/export?${query}`, '_blank')
}

function openCreate() {
  errorMessage.value = '设备缺陷登记入口尚未接入审批流'
}

function isActionDisabled(action: string, row: Row): boolean {
  // 已闭环为终态，任何动作都不允许把它改回；定级只对待定级缺陷开放
  if (row.status === '已闭环') {
    return true
  }
  if (action === '确认定级') {
    return row.status !== '待定级'
  }
  if (action === '提交闭环' || action === '挂起缺陷') {
    return row.status === '待定级'
  }
  return false
}

function actionDisabledReason(action: string, row: Row): string {
  if (row.status === '已闭环') {
    return '缺陷已闭环，闭环结果不允许再修改'
  }
  if (action === '确认定级' && row.status !== '待定级') {
    return '该缺陷已定级，定级口径唯一且不允许重复定级'
  }
  if ((action === '提交闭环' || action === '挂起缺陷') && row.status === '待定级') {
    return '请先确认定级后再执行该动作'
  }
  return ''
}

function chooseSeverity(row: Row): string | null {
  const levels = gradingRules.value?.severityLevels ?? []
  // 选项来自后端 /api/defect/grading-rules，前端不内置第二套定级口径
  const answer = window.prompt(
    `请为缺陷 ${row['缺陷编号']} 选择严重等级（${levels.join('、')}），处理期限将按统一口径自动计算：`,
    levels[0] ?? '',
  )
  const severity = (answer ?? '').trim()
  if (!severity) {
    return null
  }
  if (!levels.includes(severity)) {
    errorMessage.value = `严重等级「${severity}」不在定级口径内，可选：${levels.join('、')}`
    return null
  }
  return severity
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  if (isActionDisabled(action, row)) {
    errorMessage.value = actionDisabledReason(action, row)
    return
  }
  const body: Record<string, string> = { action }
  if (action === '确认定级') {
    const severity = chooseSeverity(row)
    if (severity === null) {
      return
    }
    body['严重等级'] = severity
  }
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify(body),
    })
    const payload = await response.json().catch(() => null)
    if (!response.ok || payload?.ok === false) {
      throw new Error(payload?.message ?? '缺陷登记动作未生效，请稍后重试')
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '缺陷登记操作失败'
  }
}

async function loadGradingRules() {
  try {
    const response = await request(`${ENDPOINT}/grading-rules`)
    if (response.ok) {
      gradingRules.value = await response.json()
    }
  } catch {
    // 口径读取失败时定级按钮会提示等级选项缺失，不阻塞列表使用
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams(filters.value as Record<string, string>).toString()
  try {
    const response = await request(`${ENDPOINT}?${query}`)
    if (!response.ok) {
      throw new Error('设备缺陷列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
    applyStats(payload)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '缺陷登记列表读取失败'
  }
}

onMounted(() => {
  void loadGradingRules()
  void reload()
})
</script>
