const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000/api'

export function getToken() {
  return localStorage.getItem('software_patent_token') || ''
}

export function setToken(token) {
  if (token) localStorage.setItem('software_patent_token', token)
  else localStorage.removeItem('software_patent_token')
}

export async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  if (!(options.body instanceof FormData)) headers['Content-Type'] = headers['Content-Type'] || 'application/json'
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json') ? await response.json() : await response.text()
  if (!response.ok) {
    const detail = typeof payload === 'object' ? payload.detail : payload
    throw new Error(detail || '请求失败')
  }
  return payload
}

export async function download(path, filename) {
  const token = getToken()
  const response = await fetch(`${API_BASE}${path}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  if (!response.ok) throw new Error('导出失败')
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

/**
 * 分页获取题目列表（对应增强版后端 GET /questions 分页响应）。
 * 返回 { items, total, page, page_size, total_pages }
 */
export async function fetchQuestionsPage(filters = {}, page = 1, pageSize = 20) {
  const query = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => value && query.set(key, value))
  query.set('page', page)
  query.set('page_size', pageSize)
  return api(`/questions?${query}`)
}

/**
 * 触发题目列表导出下载（JSON 或 CSV）。
 * 将当前筛选条件传入后端，后端按条件导出。
 */
export async function exportQuestions(filters = {}, format = 'json') {
  const query = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => value && query.set(key, value))
  query.set('format', format)
  const filename = `questions-export-${Date.now()}.${format}`
  return download(`/questions/export?${query}`, filename)
}

/**
 * 获取当前用户的题目分类统计（无需加载全量题目）。
 * 返回 { total, by_modal_type, by_difficulty, by_logic_system, by_review_status }
 */
export async function fetchQuestionStats() {
  return api('/questions/stats')
}

/**
 * 批量确认题目：将草稿状态改为已确认。
 * @param {number[]} ids - 题目 ID 数组
 */
export async function batchConfirmQuestions(ids) {
  return api('/questions/batch-confirm', {
    method: 'POST',
    body: JSON.stringify({ question_ids: ids }),
  })
}

/**
 * 获取管理员活动日志（最近 N 条系统事件）。
 * @param {number} limit - 返回条数上限，默认 20
 */
export async function fetchActivityLog(limit = 20) {
  return api(`/admin/activity-log?limit=${limit}`)
}
