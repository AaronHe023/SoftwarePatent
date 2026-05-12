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
