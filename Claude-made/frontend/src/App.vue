<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { api, batchConfirmQuestions, download, exportQuestions, fetchActivityLog, fetchQuestionStats, fetchQuestionsPage, getToken, setToken } from './api'
import logicNetwork from './assets/logic-network.svg'
import emptyState from './assets/empty-lab.svg'
import reportGraphic from './assets/report-matrix.svg'

const user = ref(null)
const page = ref('hub')
const theme = ref(localStorage.getItem('software_patent_theme') || 'light')
const message = ref('')
const error = ref('')
const toast = ref(null)
const busy = ref({})
const fieldErrors = ref({})
const authMode = ref('login')
const authForm = ref({ username: '', email: '', password: '' })
const passwordForm = ref({ old_password: '', new_password: '' })

// 分页状态
const questionsPage = ref(1)
const questionsTotalPages = ref(1)
const questionsTotal = ref(0)

// 题目统计（全局，不依赖分页）
const questionStats = ref(null)

// 批量操作
const selectedQuestionIds = ref(new Set())

// 题目预览弹窗
const previewQuestion = ref(null)

// 复制高亮
const newItemId = ref(null)

// 活动日志（管理员）
const activityLog = ref([])

const modalTypes = ['认知模态', '道义模态', '时态模态', '真值模态']
const logicSystems = ['K', 'T', 'S4', 'S5']
const difficulties = [
  { value: 'single_step', label: '单步推理' },
  { value: 'multi_step', label: '多步推理' },
  { value: 'nested', label: '算子嵌套' }
]
const questionTypes = [
  { value: 'true_false', label: 'True/False' },
  { value: 'multiple_choice', label: '多选题ABCD' }
]
const strategies = [
  { value: 'zero_shot', label: 'Zero-shot' },
  { value: 'cot', label: 'CoT' },
  { value: 'few_shot', label: 'Few-shot' }
]

const moduleMeta = {
  hub: { code: 'HOME', title: '系统首页', subtitle: '按题目生成、题目确认、数据集构建、模型评测和报告导出完成核心流程', accent: '系统总览' },
  generate: { code: 'GEN', title: '题目生成', subtitle: '按模态类型、逻辑系统、难度和题目格式生成推理题目草稿', accent: '题目生成' },
  questions: { code: 'QBK', title: '题库管理', subtitle: '维护题干、前提、答案、解析和确认状态，形成可复用题库', accent: '题库管理' },
  datasets: { code: 'DST', title: '数据集管理', subtitle: '将已确认题目组织为标准评测数据集，并支持 JSON 导出', accent: '数据集管理' },
  evaluate: { code: 'EVA', title: '模型评测', subtitle: '配置模型和提示策略，对数据集执行批量推理评测', accent: '模型评测' },
  reports: { code: 'REP', title: '统计报告', subtitle: '查看总体准确率、分类统计、模型策略对比和单题输出', accent: '统计报告' },
  templates: { code: 'TPL', title: '提示模板', subtitle: '管理 Zero-shot、CoT、Few-shot 等评测提示模板', accent: '提示模板' },
  adminHub: { code: 'ADM', title: '系统管理后台', subtitle: '管理员查看系统概览、用户、内容审核和评测任务监管', accent: '系统管理' },
  adminUsers: { code: 'USR', title: '用户管理', subtitle: '查看用户清单、角色身份和账号创建情况', accent: '用户管理' },
  adminContent: { code: 'CNT', title: '内容审核', subtitle: '集中查看题目、数据集和待确认内容', accent: '内容审核' },
  adminTasks: { code: 'OPS', title: '评测任务监管', subtitle: '追踪评测任务状态、失败数量与运行进度', accent: '任务监管' }
}

const pageCatalog = [
  { key: 'hub', label: '系统首页', code: 'HOME' },
  { key: 'generate', label: '题目生成', code: 'GEN' },
  { key: 'questions', label: '题库管理', code: 'QBK' },
  { key: 'datasets', label: '数据集管理', code: 'DST' },
  { key: 'evaluate', label: '模型评测', code: 'EVA' },
  { key: 'reports', label: '统计报告', code: 'REP' },
  { key: 'templates', label: '提示模板', code: 'TPL' }
]

const adminCatalog = [
  { key: 'adminHub', label: '系统概览', code: 'ADM' },
  { key: 'adminUsers', label: '用户管理', code: 'USR' },
  { key: 'adminContent', label: '内容审核', code: 'CNT' },
  { key: 'adminTasks', label: '任务监管', code: 'OPS' }
]

const questions = ref([])
const datasets = ref([])
const templates = ref([])
const tasks = ref([])
const adminUsers = ref([])
const adminOverview = ref(null)
const systemHealth = ref('checking')
const selectedDataset = ref(null)
const selectedTask = ref(null)
const importForm = ref({ format: 'json', content: '' })
const filters = ref({ modal_type: '', logic_system: '', difficulty: '', question_type: '', review_status: '', source: '' })
const generationForm = ref({
  modal_type: '认知模态',
  logic_system: 'K',
  difficulty: 'single_step',
  modal_depth: 1,
  question_type: 'true_false',
  count: 3,
  base_url: '',
  api_key: '',
  model_name: ''
})

function blankQuestion() {
  return {
    title: '',
    premisesText: '',
    question_text: '',
    optionsText: '',
    answer: '',
    question_type: 'true_false',
    modal_type: '认知模态',
    logic_system: 'K',
    modal_depth: 1,
    difficulty: 'single_step',
    source: 'manual',
    explanation: '',
    review_status: 'draft'
  }
}

const questionForm = ref(blankQuestion())
const editingQuestionId = ref(null)
const datasetForm = ref({ name: '', description: '' })
const templateForm = ref({ name: '', strategy_type: 'zero_shot', template_content: '' })
const evalForm = ref({
  dataset_id: '',
  task_name: '',
  models: [{ model_name: 'demo-model', base_url: '', api_key: '' }],
  strategies: [{ strategy_type: 'zero_shot', prompt_template_id: 1 }]
})

const isAdminMode = computed(() => user.value?.role === 'admin')
const navItems = computed(() => isAdminMode.value ? adminCatalog : pageCatalog)

// 全局题目计数（优先使用 stats 接口，降级用当前页数组长度）
const totalQuestionsCount = computed(() =>
  questionStats.value?.total ?? questions.value.length
)
const confirmedCountGlobal = computed(() =>
  questionStats.value?.by_review_status?.confirmed ?? confirmedQuestions.value.length
)
const draftCountGlobal = computed(() =>
  questionStats.value?.by_review_status?.draft ?? draftQuestions.value.length
)

function applyTheme() {
  document.documentElement.dataset.theme = theme.value
  localStorage.setItem('software_patent_theme', theme.value)
}

function toggleTheme() {
  theme.value = theme.value === 'light' ? 'dark' : 'light'
  applyTheme()
}

function defaultPageFor(role) {
  return role === 'admin' ? 'adminHub' : 'hub'
}

function allowedPages(role) {
  return role === 'admin' ? adminCatalog.map((item) => item.key) : pageCatalog.map((item) => item.key)
}

function pageFromHash(role) {
  const raw = window.location.hash.replace(/^#\/?/, '')
  return allowedPages(role).includes(raw) ? raw : defaultPageFor(role)
}

function goTo(target) {
  if (!user.value || !allowedPages(user.value.role).includes(target)) return
  page.value = target
  window.location.hash = target
}

function syncHash() {
  if (!user.value) return
  page.value = pageFromHash(user.value.role)
}

function showOk(text) {
  message.value = text
  error.value = ''
  toast.value = { type: 'success', text }
  window.clearTimeout(showOk.timer)
  showOk.timer = window.setTimeout(() => { toast.value = null }, 2600)
}

function showError(err) {
  const text = err.message || String(err)
  error.value = text
  message.value = ''
  toast.value = { type: 'error', text }
  window.clearTimeout(showError.timer)
  showError.timer = window.setTimeout(() => { toast.value = null }, 4200)
}

function isBusy(key) {
  return Boolean(busy.value[key])
}

async function withBusy(key, task) {
  if (isBusy(key)) return
  busy.value = { ...busy.value, [key]: true }
  try {
    return await task()
  } finally {
    busy.value = { ...busy.value, [key]: false }
  }
}

function setErrors(errors) {
  fieldErrors.value = errors
  const count = Object.keys(errors).length
  if (count) showError(new Error(`还有 ${count} 项需要修正`))
  return count === 0
}

function validateGeneration() {
  const errors = {}
  if (generationForm.value.count < 1 || generationForm.value.count > 50) errors.generation_count = '生成数量必须在 1-50 之间'
  if (generationForm.value.modal_depth < 1 || generationForm.value.modal_depth > 3) errors.generation_depth = '嵌套深度必须为 1-3'
  const llmFields = [generationForm.value.base_url, generationForm.value.api_key, generationForm.value.model_name].filter(Boolean)
  if (llmFields.length > 0 && llmFields.length < 3) errors.generation_llm = '真实调用需同时填写 base_url、api_key 和 model_name；全部留空则进入演示模式'
  if (generationForm.value.base_url && !/^https?:\/\//.test(generationForm.value.base_url)) errors.generation_base_url = 'base_url 需以 http:// 或 https:// 开头'
  return setErrors(errors)
}

function validateQuestion() {
  const errors = {}
  const answer = questionForm.value.answer.trim()
  if (!questionForm.value.title.trim()) errors.question_title = '请填写题目标题'
  if (!questionForm.value.question_text.trim()) errors.question_text = '请填写题干'
  if (!answer) errors.question_answer = '请填写标准答案'
  if (questionForm.value.question_type === 'true_false' && !['True', 'False'].includes(answer)) errors.question_answer = 'True/False 题答案只能是 True 或 False'
  if (questionForm.value.question_type === 'multiple_choice' && !['A', 'B', 'C', 'D'].includes(answer)) errors.question_answer = '多选题答案只能是 A/B/C/D'
  if (questionForm.value.question_type === 'multiple_choice' && questionForm.value.optionsText.split('\n').filter(Boolean).length < 2) errors.question_options = '多选题至少需要两个选项'
  return setErrors(errors)
}

function validateImport() {
  const errors = {}
  if (!importForm.value.content.trim()) errors.import_content = '请粘贴 JSON 数组或 CSV 文本'
  if (importForm.value.format === 'json' && importForm.value.content.trim()) {
    try {
      const parsed = JSON.parse(importForm.value.content)
      if (!Array.isArray(parsed)) errors.import_content = 'JSON 导入内容必须是题目数组'
    } catch {
      errors.import_content = 'JSON 格式无效，请检查括号、逗号和引号'
    }
  }
  return setErrors(errors)
}

function validateDataset() {
  return setErrors(datasetForm.value.name.trim() ? {} : { dataset_name: '请填写数据集名称' })
}

function validateTemplate() {
  const errors = {}
  if (!templateForm.value.name.trim()) errors.template_name = '请填写模板名称'
  if (!templateForm.value.template_content.trim()) errors.template_content = '请填写模板内容'
  if (templateForm.value.template_content && !templateForm.value.template_content.includes('{question}')) errors.template_content = '模板建议包含 {question} 占位符'
  return setErrors(errors)
}

function validateEvalTask() {
  const errors = {}
  if (!evalForm.value.dataset_id) errors.eval_dataset = '请选择数据集'
  if (!evalForm.value.task_name.trim()) errors.eval_name = '请填写评测任务名称'
  evalForm.value.models.forEach((model, index) => {
    if (!model.model_name.trim()) errors[`eval_model_${index}`] = `第 ${index + 1} 个模型缺少 model_name`
    const filled = [model.base_url, model.api_key].filter(Boolean).length
    if (filled === 1) errors[`eval_model_${index}`] = `第 ${index + 1} 个模型真实调用需同时填写 base_url 和 api_key`
    if (model.base_url && !/^https?:\/\//.test(model.base_url)) errors[`eval_model_${index}`] = `第 ${index + 1} 个模型 base_url 格式无效`
  })
  if (!evalForm.value.strategies.length) errors.eval_strategy = '至少选择一个提示策略'
  return setErrors(errors)
}

async function signIn() {
  await withBusy('auth', async () => {
    const path = authMode.value === 'login' ? '/auth/login' : '/auth/register'
    const body = authMode.value === 'login'
      ? { username: authForm.value.username, password: authForm.value.password }
      : authForm.value
    try {
      const data = await api(path, { method: 'POST', body: JSON.stringify(body) })
      setToken(data.token)
      user.value = data.user
      goTo(pageFromHash(data.user.role))
      await loadDashboard()
      showOk('登录成功')
    } catch (err) {
      showError(err)
    }
  })
}

async function logout() {
  setToken('')
  user.value = null
  selectedDataset.value = null
  selectedTask.value = null
  page.value = 'hub'
  window.location.hash = ''
}

async function loadMe() {
  if (!getToken()) return
  try {
    user.value = await api('/auth/me')
    goTo(pageFromHash(user.value.role))
    await loadDashboard()
  } catch {
    setToken('')
  }
}

async function changePassword() {
  await withBusy('password', async () => {
    try {
      await api('/auth/change-password', { method: 'POST', body: JSON.stringify(passwordForm.value) })
      passwordForm.value = { old_password: '', new_password: '' }
      showOk('密码已修改')
    } catch (err) {
      showError(err)
    }
  })
}

async function loadDashboard() {
  await withBusy('dashboard', async () => {
    await Promise.all([loadQuestions(), loadDatasets(), loadTemplates(), loadTasks()])
    if (!isAdminMode.value) await loadQuestionStats()
    if (user.value?.role === 'admin') await loadAdmin()
  })
}

// ── 题目加载（分页版）─────────────────────────────────────────

async function loadQuestions() {
  const pageSize = isAdminMode.value ? 500 : 20
  const currentPage = isAdminMode.value ? 1 : questionsPage.value
  try {
    const data = await fetchQuestionsPage(filters.value, currentPage, pageSize)
    questions.value = data.items
    questionsTotal.value = data.total
    questionsTotalPages.value = data.total_pages
  } catch {
    // 兼容旧版后端（直接返回数组）
    const query = new URLSearchParams()
    Object.entries(filters.value).forEach(([key, value]) => value && query.set(key, value))
    const raw = await api(`/questions${query.toString() ? `?${query}` : ''}`)
    if (Array.isArray(raw)) {
      questions.value = raw
      questionsTotal.value = raw.length
      questionsTotalPages.value = 1
    }
  }
}

async function loadQuestionStats() {
  try {
    questionStats.value = await fetchQuestionStats()
  } catch {}
}

async function goQuestionsPage(p) {
  questionsPage.value = p
  selectedQuestionIds.value = new Set()
  await loadQuestions()
}

async function applyFilters() {
  questionsPage.value = 1
  selectedQuestionIds.value = new Set()
  await loadQuestions()
}

// ── 批量操作 ──────────────────────────────────────────────────

const allOnPageSelected = computed(() =>
  questions.value.length > 0 && questions.value.every((q) => selectedQuestionIds.value.has(q.id))
)

function toggleSelectAll() {
  if (allOnPageSelected.value) {
    selectedQuestionIds.value = new Set()
  } else {
    selectedQuestionIds.value = new Set(questions.value.map((q) => q.id))
  }
}

function toggleSelect(id) {
  const next = new Set(selectedQuestionIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedQuestionIds.value = next
}

async function batchConfirm() {
  const ids = [...selectedQuestionIds.value]
  if (!ids.length) return
  await withBusy('batchConfirm', async () => {
    try {
      const result = await batchConfirmQuestions(ids)
      selectedQuestionIds.value = new Set()
      await loadQuestions()
      await loadQuestionStats()
      showOk(`已批量确认 ${result.confirmed} 道题目`)
    } catch (err) {
      showError(err)
    }
  })
}

async function batchDelete() {
  const ids = [...selectedQuestionIds.value]
  if (!ids.length || !window.confirm(`确认删除选中的 ${ids.length} 道题目？此操作不可撤销。`)) return
  await withBusy('batchDelete', async () => {
    try {
      for (const id of ids) {
        await api(`/questions/${id}`, { method: 'DELETE' })
      }
      selectedQuestionIds.value = new Set()
      await loadQuestions()
      await loadQuestionStats()
      showOk(`已删除 ${ids.length} 道题目`)
    } catch (err) {
      showError(err)
    }
  })
}

// ── 题目预览弹窗 ──────────────────────────────────────────────

function openPreview(question) {
  previewQuestion.value = question
}

function closePreview() {
  previewQuestion.value = null
}

// ── 复制题目 ──────────────────────────────────────────────────

async function duplicateQuestion(question) {
  await withBusy(`dup-${question.id}`, async () => {
    try {
      const payload = {
        title: `${question.title}（副本）`,
        premises: question.premises,
        question_text: question.question_text,
        options: question.options,
        answer: question.answer,
        question_type: question.question_type,
        modal_type: question.modal_type,
        logic_system: question.logic_system,
        modal_depth: question.modal_depth,
        difficulty: question.difficulty,
        source: 'manual',
        explanation: question.explanation || '',
        review_status: 'draft'
      }
      const newQ = await api('/questions', { method: 'POST', body: JSON.stringify(payload) })
      await loadQuestions()
      await loadQuestionStats()
      newItemId.value = newQ.id
      setTimeout(() => { newItemId.value = null }, 2200)
      showOk('题目已复制为新草稿')
    } catch (err) {
      showError(err)
    }
  })
}

// ── 键盘快捷键 ────────────────────────────────────────────────

function handleKeydown(e) {
  // Esc 关闭预览弹窗
  if (e.key === 'Escape' && previewQuestion.value) {
    closePreview()
    return
  }
  // Ctrl+Enter 提交当前页面主表单
  if (e.ctrlKey && e.key === 'Enter') {
    if (page.value === 'generate') generateQuestions()
    else if (page.value === 'questions') saveQuestion()
    else if (page.value === 'evaluate') createEvalTask()
  }
}

// ── 题目 CRUD ─────────────────────────────────────────────────

function normalizeQuestionForm() {
  return {
    ...questionForm.value,
    premises: questionForm.value.premisesText.split('\n').map((item) => item.trim()).filter(Boolean),
    options: questionForm.value.optionsText.split('\n').map((item) => item.trim()).filter(Boolean)
  }
}

async function saveQuestion() {
  if (!validateQuestion()) return
  await withBusy('questionSave', async () => {
    try {
      const payload = normalizeQuestionForm()
      delete payload.premisesText
      delete payload.optionsText
      if (editingQuestionId.value) {
        await api(`/questions/${editingQuestionId.value}`, { method: 'PUT', body: JSON.stringify(payload) })
        showOk('题目已更新')
      } else {
        await api('/questions', { method: 'POST', body: JSON.stringify(payload) })
        showOk('题目已创建')
      }
      questionForm.value = blankQuestion()
      editingQuestionId.value = null
      await loadQuestions()
      await loadQuestionStats()
    } catch (err) {
      showError(err)
    }
  })
}

function editQuestion(question) {
  editingQuestionId.value = question.id
  questionForm.value = {
    ...question,
    premisesText: question.premises.join('\n'),
    optionsText: question.options.join('\n')
  }
  goTo('questions')
}

async function confirmQuestion(id) {
  await withBusy(`confirm-${id}`, async () => {
    try {
      await api(`/questions/${id}/confirm`, { method: 'POST' })
      await loadQuestions()
      await loadQuestionStats()
      showOk('题目已确认')
    } catch (err) {
      showError(err)
    }
  })
}

async function deleteQuestion(id) {
  if (!window.confirm('确认删除该题目？')) return
  await withBusy(`delete-question-${id}`, async () => {
    try {
      await api(`/questions/${id}`, { method: 'DELETE' })
      await loadQuestions()
      await loadQuestionStats()
      showOk('题目已删除')
    } catch (err) {
      showError(err)
    }
  })
}

async function generateQuestions() {
  if (!validateGeneration()) return
  await withBusy('generate', async () => {
    try {
      await api('/questions/generate', { method: 'POST', body: JSON.stringify(generationForm.value) })
      await loadQuestions()
      await loadQuestionStats()
      showOk('已生成草稿题目，可在题目管理中编辑确认')
    } catch (err) {
      showError(err)
    }
  })
}

async function importQuestions() {
  if (!validateImport()) return
  await withBusy('import', async () => {
    try {
      const result = await api('/questions/import', { method: 'POST', body: JSON.stringify(importForm.value) })
      await loadQuestions()
      await loadQuestionStats()
      showOk(`导入完成：成功${result.created}条，错误${result.errors.length}条`)
      if (result.errors.length) fieldErrors.value = { import_content: result.errors.join('；') }
    } catch (err) {
      showError(err)
    }
  })
}

async function doExportQuestions(format) {
  await withBusy(`exportQ-${format}`, async () => {
    try {
      await exportQuestions(filters.value, format)
    } catch (err) {
      showError(err)
    }
  })
}

// ── 数据集 ────────────────────────────────────────────────────

async function loadDatasets() {
  datasets.value = await api('/datasets')
  if (selectedDataset.value) await openDataset(selectedDataset.value.id)
}

async function createDataset() {
  if (!validateDataset()) return
  await withBusy('datasetCreate', async () => {
    try {
      const data = await api('/datasets', { method: 'POST', body: JSON.stringify(datasetForm.value) })
      datasetForm.value = { name: '', description: '' }
      selectedDataset.value = data
      await loadDatasets()
      showOk('数据集已创建')
    } catch (err) {
      showError(err)
    }
  })
}

async function openDataset(id) {
  selectedDataset.value = await api(`/datasets/${id}`)
  goTo('datasets')
}

async function addToDataset(questionId) {
  if (!selectedDataset.value) {
    showError(new Error('请先选择一个数据集'))
    return
  }
  await withBusy(`add-dataset-${questionId}`, async () => {
    try {
      selectedDataset.value = await api(`/datasets/${selectedDataset.value.id}/questions`, {
        method: 'POST',
        body: JSON.stringify({ question_id: questionId })
      })
      await loadDatasets()
      showOk('已加入数据集')
    } catch (err) {
      showError(err)
    }
  })
}

async function removeFromDataset(questionId) {
  try {
    selectedDataset.value = await api(`/datasets/${selectedDataset.value.id}/questions/${questionId}`, { method: 'DELETE' })
    await loadDatasets()
  } catch (err) {
    showError(err)
  }
}

async function deleteDataset(id) {
  if (!window.confirm('确认删除该数据集？')) return
  await withBusy(`delete-dataset-${id}`, async () => {
    try {
      await api(`/datasets/${id}`, { method: 'DELETE' })
      if (selectedDataset.value?.id === id) selectedDataset.value = null
      await loadDatasets()
      showOk('数据集已删除')
    } catch (err) {
      showError(err)
    }
  })
}

// ── 提示模板 ──────────────────────────────────────────────────

async function loadTemplates() {
  templates.value = await api('/prompt-templates')
}

async function createTemplate() {
  if (!validateTemplate()) return
  await withBusy('templateCreate', async () => {
    try {
      await api('/prompt-templates', { method: 'POST', body: JSON.stringify(templateForm.value) })
      templateForm.value = { name: '', strategy_type: 'zero_shot', template_content: '' }
      await loadTemplates()
      showOk('模板已创建')
    } catch (err) {
      showError(err)
    }
  })
}

async function deleteTemplate(template) {
  if (!window.confirm('确认删除该模板？')) return
  try {
    await api(`/prompt-templates/${template.id}`, { method: 'DELETE' })
    await loadTemplates()
  } catch (err) {
    showError(err)
  }
}

// ── 评测任务 ──────────────────────────────────────────────────

async function loadTasks() {
  tasks.value = await api('/eval-tasks')
  if (selectedTask.value) selectedTask.value = await api(`/eval-tasks/${selectedTask.value.id}`)
}

function addModel() {
  evalForm.value.models.push({ model_name: '', base_url: '', api_key: '' })
}

function addStrategy() {
  evalForm.value.strategies.push({ strategy_type: 'zero_shot', prompt_template_id: 1 })
}

async function createEvalTask() {
  if (!validateEvalTask()) return
  await withBusy('evalCreate', async () => {
    try {
      const data = await api('/eval-tasks', { method: 'POST', body: JSON.stringify(evalForm.value) })
      selectedTask.value = data
      await loadTasks()
      showOk('评测任务已创建，系统正在后台执行')
    } catch (err) {
      showError(err)
    }
  })
}

async function openTask(id) {
  selectedTask.value = await api(`/eval-tasks/${id}`)
  goTo('reports')
}

async function cancelTask(id) {
  try {
    selectedTask.value = await api(`/eval-tasks/${id}/cancel`, { method: 'POST' })
    await loadTasks()
    showOk('已请求取消任务')
  } catch (err) {
    showError(err)
  }
}

// ── 管理员 ────────────────────────────────────────────────────

async function loadAdmin() {
  adminUsers.value = await api('/admin/users')
  adminOverview.value = await api('/admin/overview')
  await loadActivityLog()
  try {
    await api('/health')
    systemHealth.value = 'healthy'
  } catch {
    systemHealth.value = 'offline'
  }
}

async function loadActivityLog() {
  try {
    activityLog.value = await fetchActivityLog(15)
  } catch {}
}

async function deleteUser(id) {
  if (!window.confirm('确认删除该用户及其数据？')) return
  try {
    await api(`/admin/users/${id}`, { method: 'DELETE' })
    await loadAdmin()
  } catch (err) {
    showError(err)
  }
}

// ── 演示流程 ──────────────────────────────────────────────────

async function createDemoFlow() {
  if (isAdminMode.value) return
  await withBusy('demoFlow', async () => {
    try {
      const demoForm = { ...generationForm.value, count: 5, base_url: '', api_key: '', model_name: '' }
      const drafts = await api('/questions/generate', { method: 'POST', body: JSON.stringify(demoForm) })
      for (const item of drafts) {
        await api(`/questions/${item.id}/confirm`, { method: 'POST' })
      }
      const dataset = await api('/datasets', {
        method: 'POST',
        body: JSON.stringify({
          name: `演示数据集 ${new Date().toLocaleString('zh-CN')}`,
          description: '一键演示流程自动创建，用于软著截图和核心流程验收。'
        })
      })
      for (const item of drafts) {
        await api(`/datasets/${dataset.id}/questions`, { method: 'POST', body: JSON.stringify({ question_id: item.id }) })
      }
      selectedDataset.value = await api(`/datasets/${dataset.id}`)
      await loadDashboard()
      goTo('datasets')
      showOk('演示数据已创建：题目已确认并加入数据集')
    } catch (err) {
      showError(err)
    }
  })
}

// ── 报告辅助 ──────────────────────────────────────────────────

const reportGroupOrder = ['modal_type', 'logic_system', 'difficulty', 'question_type', 'model', 'strategy']
const reportGroupLabels = {
  modal_type: '模态类型',
  logic_system: '逻辑系统',
  difficulty: '难度',
  question_type: '题目格式',
  model: '模型对比',
  strategy: '策略对比'
}

const reportGroupTypes = computed(() => {
  const types = new Set(selectedTask.value?.reports?.filter((r) => r.group_type !== 'overall').map((r) => r.group_type) || [])
  return reportGroupOrder.filter((t) => types.has(t))
})

function reportsOfType(groupType) {
  return (selectedTask.value?.reports || []).filter((r) => r.group_type === groupType)
}

// ── 通用工具 ──────────────────────────────────────────────────

function labelOf(list, value) {
  return list.find((item) => item.value === value)?.label || value
}

function templatesForStrategy(strategyType) {
  return templates.value.filter((template) => template.strategy_type === strategyType)
}

function sourceLabel(source) {
  const labels = { manual: '手动录入', llm_generated: '系统生成', imported: '已导入' }
  return labels[source] || source
}

function percent(value, total) {
  if (!total) return '0%'
  return `${Math.round((value / total) * 100)}%`
}

function activityTypeLabel(type) {
  const labels = { question: '题目', dataset: '数据集', eval_task: '评测' }
  return labels[type] || type
}

// ── 派生计算 ──────────────────────────────────────────────────

const confirmedQuestions = computed(() => questions.value.filter((item) => item.review_status === 'confirmed'))
const draftQuestions = computed(() => questions.value.filter((item) => item.review_status === 'draft'))
const importedQuestions = computed(() => questions.value.filter((item) => item.source === 'imported'))
const reportOverall = computed(() => selectedTask.value?.reports?.find((item) => item.group_type === 'overall'))
const pageInfo = computed(() => moduleMeta[page.value] || moduleMeta.generate)
const runningTasks = computed(() => tasks.value.filter((item) => ['pending', 'running'].includes(item.status)).length)
const completedTasks = computed(() => tasks.value.filter((item) => item.status === 'completed').length)
const failedTasks = computed(() => tasks.value.filter((item) => item.status === 'failed').length)
const confirmedRate = computed(() => percent(confirmedCountGlobal.value, totalQuestionsCount.value))
const failedPredictions = computed(() => tasks.value.reduce((sum, task) => sum + (task.failed_count || 0), 0))
const invalidQuestions = computed(() => questions.value.filter((item) => {
  const premises = Array.isArray(item.premises) ? item.premises : []
  const options = Array.isArray(item.options) ? item.options : []
  return !item.title || !item.question_text || !item.answer || premises.length === 0 || !item.explanation || (item.question_type === 'multiple_choice' && options.length < 2)
}))
const riskyTasks = computed(() => tasks.value.filter((task) => {
  const failed = task.failed_count || 0
  return ['failed', 'cancelled'].includes(task.status) || failed > 0
}))
const userProfiles = computed(() => adminUsers.value.map((item) => ({
  ...item,
  questions: questions.value.filter((q) => q.user_id === item.id).length,
  datasets: datasets.value.filter((dataset) => dataset.user_id === item.id).length,
  tasks: tasks.value.filter((task) => task.user_id === item.id).length
})))
const workflowCards = computed(() => [
  { key: 'generate', step: '01', title: '题目生成', text: '配置模态类型、逻辑系统、难度和题目格式，生成待确认题目。', metric: `${draftCountGlobal.value} 个草稿`, cta: '进入题目生成' },
  { key: 'questions', step: '02', title: '题目确认', text: '检查题干、前提、答案和解析，确认后进入正式题库。', metric: `${confirmedCountGlobal.value}/${totalQuestionsCount.value} 已确认`, cta: '查看题库' },
  { key: 'datasets', step: '03', title: '数据集构建', text: '从已确认题目中选择样本，形成可导出的评测数据集。', metric: `${datasets.value.length} 个数据集`, cta: '构建数据集' },
  { key: 'evaluate', step: '04', title: '模型评测', text: '配置模型、接口和提示模板，对数据集执行批量评测。', metric: `${runningTasks.value} 个运行中`, cta: '发起评测' },
  { key: 'reports', step: '05', title: '报告导出', text: '查看准确率、分类统计和单题输出，并导出 JSON/CSV。', metric: `${completedTasks.value} 份完成`, cta: '查看统计报告' }
])
const adminCards = computed(() => [
  { key: 'adminUsers', title: '用户管理', value: adminUsers.value.length, hint: '注册账号 / 管理员身份' },
  { key: 'adminContent', title: '内容审核', value: questions.value.length, hint: `${draftQuestions.value.length} 个草稿待确认` },
  { key: 'adminContent', title: '数据集监管', value: datasets.value.length, hint: '全量数据集与题目关联' },
  { key: 'adminTasks', title: '任务监管', value: tasks.value.length, hint: `${failedTasks.value} 个失败任务` }
])

onMounted(() => {
  applyTheme()
  window.addEventListener('hashchange', syncHash)
  window.addEventListener('keydown', handleKeydown)
  loadMe()
})

onUnmounted(() => {
  window.removeEventListener('hashchange', syncHash)
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <!-- Toast 通知 -->
  <div v-if="toast" class="toast" :class="toast.type">
    <span class="toast-dot"></span>
    <strong>{{ toast.type === 'success' ? '操作完成' : '需要处理' }}</strong>
    <p>{{ toast.text }}</p>
  </div>

  <!-- 题目预览弹窗 -->
  <teleport to="body">
    <div v-if="previewQuestion" class="question-modal-overlay" @click.self="closePreview">
      <div class="question-modal">
        <div class="question-modal-head">
          <h3>{{ previewQuestion.title }}</h3>
          <button class="ghost" @click="closePreview" title="关闭 (Esc)">✕</button>
        </div>
        <div class="question-modal-body">
          <div v-if="previewQuestion.premises && previewQuestion.premises.length">
            <p class="section-tag">前提条件</p>
            <ul>
              <li v-for="(p, i) in previewQuestion.premises" :key="i">{{ p }}</li>
            </ul>
          </div>
          <div>
            <p class="section-tag">题干</p>
            <p>{{ previewQuestion.question_text }}</p>
          </div>
          <div v-if="previewQuestion.options && previewQuestion.options.length">
            <p class="section-tag">选项</p>
            <ul>
              <li v-for="(opt, i) in previewQuestion.options" :key="i">{{ opt }}</li>
            </ul>
          </div>
          <div>
            <p class="section-tag">标准答案</p>
            <span class="answer-badge">{{ previewQuestion.answer }}</span>
          </div>
          <div v-if="previewQuestion.explanation">
            <p class="section-tag">解析</p>
            <p>{{ previewQuestion.explanation }}</p>
          </div>
          <div>
            <p class="section-tag">分类信息</p>
            <p>{{ previewQuestion.modal_type }} · {{ previewQuestion.logic_system }} · {{ labelOf(difficulties, previewQuestion.difficulty) }} · 嵌套深度 {{ previewQuestion.modal_depth }}</p>
          </div>
        </div>
        <div class="question-modal-foot">
          <span class="pill stamp" :class="previewQuestion.review_status">
            {{ previewQuestion.review_status === 'confirmed' ? '已确认' : '草稿' }}
          </span>
          <button @click="editQuestion(previewQuestion); closePreview()">编辑题目</button>
        </div>
      </div>
    </div>
  </teleport>

  <!-- 批量操作浮出栏 -->
  <transition name="bulk-slide">
    <div v-if="selectedQuestionIds.size > 0" class="bulk-action-bar">
      <span>已选 {{ selectedQuestionIds.size }} 道题目</span>
      <button @click="batchConfirm" :disabled="isBusy('batchConfirm')">
        <span v-if="isBusy('batchConfirm')" class="spinner"></span>
        批量确认
      </button>
      <button class="danger" @click="batchDelete" :disabled="isBusy('batchDelete')">
        <span v-if="isBusy('batchDelete')" class="spinner"></span>
        批量删除
      </button>
      <button class="ghost" @click="selectedQuestionIds = new Set()">取消选择</button>
    </div>
  </transition>

  <!-- 未登录：认证页 -->
  <main v-if="!user" class="auth-shell">
    <section class="auth-hero">
      <div class="hero-copy">
        <p class="eyebrow">V1.0 · 软件著作权演示系统</p>
        <h1>模态逻辑推理数据集构建与评测系统</h1>
        <p class="hero-text">系统支持题目生成、题库管理、数据集构建、模型评测、统计报告和结果导出，便于完成完整流程演示。</p>
        <div class="hero-metrics">
          <div><span>模态类型</span><strong>4</strong></div>
          <div><span>逻辑系统</span><strong>K/T/S4/S5</strong></div>
          <div><span>统计维度</span><strong>7</strong></div>
        </div>
        <div class="signal-strip">
          <i></i><i></i><i></i><i></i>
        </div>
      </div>
      <div class="hero-visual">
        <img :src="logicNetwork" alt="模态逻辑评测网络" />
      </div>
    </section>

    <section class="auth-panel">
      <div class="panel-kicker">系统登录</div>
      <h2>{{ authMode === 'login' ? '进入评测系统' : '创建用户账号' }}</h2>
      <div class="segmented">
        <button :class="{ active: authMode === 'login' }" @click="authMode = 'login'">登录</button>
        <button :class="{ active: authMode === 'register' }" @click="authMode = 'register'">注册</button>
      </div>
      <form class="stack" @submit.prevent="signIn">
        <input v-model="authForm.username" placeholder="用户名" required />
        <input v-if="authMode === 'register'" v-model="authForm.email" placeholder="邮箱" required />
        <input v-model="authForm.password" placeholder="密码" type="password" required />
        <button class="primary" type="submit" :disabled="isBusy('auth')">
          <span v-if="isBusy('auth')" class="spinner"></span>
          {{ isBusy('auth') ? '正在进入...' : (authMode === 'login' ? '启动系统' : '创建账号') }}
        </button>
      </form>
      <p class="muted">默认管理员：admin / admin123</p>
      <p v-if="error" class="notice error">{{ error }}</p>
    </section>
  </main>

  <!-- 已登录：主 Shell -->
  <main v-else class="shell" :class="{ 'admin-shell': isAdminMode }">
    <aside class="nav-rail">
      <div class="brand">
        <span class="brand-mark">ML</span>
        <div>
          <strong>模态逻辑评测系统</strong>
          <span>{{ isAdminMode ? '系统管理' : '题库构建与评测' }}</span>
        </div>
      </div>
      <nav>
        <button v-for="item in navItems" :key="item.key" :class="{ active: page === item.key }" @click="goTo(item.key)">
          <span class="nav-code">{{ item.code }}</span>
          <span>{{ item.label }}</span>
        </button>
      </nav>
      <div class="rail-card">
        <span>当前身份</span>
        <strong>{{ user.role === 'admin' ? '管理员' : '研究用户' }}</strong>
        <small>{{ user.username }}</small>
      </div>
      <button class="theme-toggle" type="button" @click="toggleTheme">
        <span>{{ theme === 'light' ? '浅色' : '深色' }}</span>
        <strong>{{ theme === 'light' ? '切换深色' : '切换浅色' }}</strong>
      </button>
      <form class="password-box" @submit.prevent="changePassword">
        <input v-model="passwordForm.old_password" type="password" placeholder="原密码" />
        <input v-model="passwordForm.new_password" type="password" placeholder="新密码" />
        <button type="submit" :disabled="isBusy('password')">
          <span v-if="isBusy('password')" class="spinner"></span>
          {{ isBusy('password') ? '修改中' : '修改密码' }}
        </button>
      </form>
      <button class="ghost" @click="logout">退出登录</button>
    </aside>

    <section class="workspace">
      <header class="topbar">
        <div>
          <p class="eyebrow">{{ pageInfo.accent }}</p>
          <h1>{{ pageInfo.title }}</h1>
          <span>{{ pageInfo.subtitle }}</span>
        </div>
        <div class="topbar-metrics">
          <template v-if="!isAdminMode">
            <div><span>题库</span><strong>{{ totalQuestionsCount }}</strong></div>
            <div><span>确认率</span><strong>{{ confirmedRate }}</strong></div>
            <div><span>运行中</span><strong>{{ runningTasks }}</strong></div>
            <div><span>已完成</span><strong>{{ completedTasks }}</strong></div>
          </template>
          <template v-else>
            <div><span>用户</span><strong>{{ adminUsers.length }}</strong></div>
            <div><span>题目</span><strong>{{ questions.length }}</strong></div>
            <div><span>数据集</span><strong>{{ datasets.length }}</strong></div>
            <div><span>健康</span><strong>{{ systemHealth === 'healthy' ? 'OK' : '检查中' }}</strong></div>
          </template>
        </div>
      </header>

      <div v-if="message && !toast" class="notice success">{{ message }}</div>
      <div v-if="error && !toast" class="notice error">{{ error }}</div>

      <!-- ══ 系统首页 ══════════════════════════════════════════════ -->
      <section v-if="page === 'hub'" class="page hub-canvas">
        <div class="hub-hero">
          <div>
            <p class="section-tag">系统流程</p>
            <h2>从题目生成到报告导出的完整评测流程</h2>
            <p>点击下方步骤进入对应模块。系统会汇总题目状态、数据集数量、评测进度和报告完成情况。</p>
            <div class="hero-actions">
              <button class="primary" type="button" @click="createDemoFlow" :disabled="isBusy('demoFlow')">
                <span v-if="isBusy('demoFlow')" class="spinner"></span>
                {{ isBusy('demoFlow') ? '正在生成演示数据' : '一键准备演示数据' }}
              </button>
              <button type="button" @click="goTo('generate')">进入题目生成</button>
            </div>
          </div>
          <img :src="logicNetwork" alt="模态逻辑系统流程" />
        </div>
        <div class="workflow-map">
          <button v-for="card in workflowCards" :key="card.key" class="module-card" @click="goTo(card.key)">
            <span class="step">{{ card.step }}</span>
            <strong>{{ card.title }}</strong>
            <p>{{ card.text }}</p>
            <b>{{ card.metric }}</b>
            <em>{{ card.cta }}</em>
          </button>
        </div>
        <div class="hub-grid">
          <article class="insight-panel">
            <p class="section-tag">题库概览</p>
            <h3>题库状态统计</h3>
            <div class="mini-bars">
              <div><span>已确认</span><i :style="{ width: confirmedRate }"></i><b>{{ confirmedCountGlobal }}</b></div>
              <div><span>草稿</span><i :style="{ width: percent(draftCountGlobal, totalQuestionsCount) }"></i><b>{{ draftCountGlobal }}</b></div>
              <div><span>导入</span><i :style="{ width: percent(importedQuestions.length, totalQuestionsCount) }"></i><b>{{ importedQuestions.length }}</b></div>
            </div>
            <!-- 难度分布（来自 stats 接口） -->
            <template v-if="questionStats && questionStats.by_difficulty && Object.keys(questionStats.by_difficulty).length">
              <p class="section-tag" style="margin-top: 16px">难度分布</p>
              <div class="mini-bars">
                <div v-for="(count, diff) in questionStats.by_difficulty" :key="diff">
                  <span>{{ labelOf(difficulties, diff) }}</span>
                  <i :style="{ width: percent(count, questionStats.total) }"></i>
                  <b>{{ count }}</b>
                </div>
              </div>
            </template>
          </article>
          <!-- 最近活动（仅管理员） -->
          <article v-if="isAdminMode" class="insight-panel">
            <p class="section-tag">最近活动</p>
            <h3>系统活动日志</h3>
            <div class="activity-log">
              <div v-for="(event, i) in activityLog.slice(0, 5)" :key="i" class="activity-item">
                <span class="activity-dot" :class="event.type"></span>
                <div>
                  <strong>{{ event.description }}</strong>
                  <small>{{ event.username }} · {{ event.time }}</small>
                </div>
              </div>
              <div v-if="!activityLog.length" class="muted">暂无活动记录，可先创建题目或数据集。</div>
            </div>
          </article>
          <article v-else class="insight-panel image-slot">
            <img :src="emptyState" alt="系统说明图" />
            <div>
              <p class="section-tag">材料预留</p>
              <h3>系统说明图与截图位置</h3>
              <span>后续可替换为系统流程图、软著截图或操作说明图，不影响页面布局。</span>
            </div>
          </article>
        </div>
      </section>

      <!-- ══ 题目生成 ══════════════════════════════════════════════ -->
      <section v-if="page === 'generate'" class="page">
        <header class="page-head">
          <div>
            <p class="section-tag">题目生成</p>
            <h2>题目生成</h2>
          </div>
          <button @click="loadQuestions">刷新题库</button>
        </header>
        <div class="experiment-hero">
          <div>
            <span>生成流程</span>
            <strong>参数设置 → 生成草稿 → 人工确认 → 进入题库</strong>
          </div>
          <div class="pipeline">
            <i class="active">01</i><i>02</i><i>03</i><i>04</i>
          </div>
        </div>
        <form class="grid-form form-panel" @submit.prevent="generateQuestions">
          <label>模态类型<select v-model="generationForm.modal_type"><option v-for="item in modalTypes" :key="item">{{ item }}</option></select></label>
          <label>逻辑系统<select v-model="generationForm.logic_system"><option v-for="item in logicSystems" :key="item">{{ item }}</option></select></label>
          <label>难度<select v-model="generationForm.difficulty"><option v-for="item in difficulties" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
          <label>嵌套深度<input v-model.number="generationForm.modal_depth" type="number" min="1" max="3" /><small v-if="fieldErrors.generation_depth" class="field-error">{{ fieldErrors.generation_depth }}</small></label>
          <label>题目格式<select v-model="generationForm.question_type"><option v-for="item in questionTypes" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
          <label>生成数量<input v-model.number="generationForm.count" type="number" min="1" max="50" /><small v-if="fieldErrors.generation_count" class="field-error">{{ fieldErrors.generation_count }}</small></label>
          <label>base_url<input v-model="generationForm.base_url" placeholder="可留空进入演示模式" /><small v-if="fieldErrors.generation_base_url" class="field-error">{{ fieldErrors.generation_base_url }}</small></label>
          <label>model_name<input v-model="generationForm.model_name" placeholder="可留空" /></label>
          <label class="wide">api_key<input v-model="generationForm.api_key" type="password" placeholder="仅本次请求使用，不入库" /><small v-if="fieldErrors.generation_llm" class="field-error">{{ fieldErrors.generation_llm }}</small></label>
          <button class="primary wide" type="submit" :disabled="isBusy('generate')">
            <span v-if="isBusy('generate')" class="spinner"></span>
            {{ isBusy('generate') ? '生成中...' : '生成草稿题目 (Ctrl+Enter)' }}
          </button>
        </form>
      </section>

      <!-- ══ 题库管理 ══════════════════════════════════════════════ -->
      <section v-if="page === 'questions'" class="page">
        <header class="page-head">
          <div><p class="section-tag">题库管理</p><h2>题库管理</h2></div>
          <div class="actions">
            <button @click="doExportQuestions('json')" :disabled="isBusy('exportQ-json')">
              <span v-if="isBusy('exportQ-json')" class="spinner"></span>导出 JSON
            </button>
            <button @click="doExportQuestions('csv')" :disabled="isBusy('exportQ-csv')">
              <span v-if="isBusy('exportQ-csv')" class="spinner"></span>导出 CSV
            </button>
            <button @click="applyFilters">刷新</button>
          </div>
        </header>

        <div class="filters command-bar">
          <select v-model="filters.modal_type"><option value="">全部模态</option><option v-for="item in modalTypes" :key="item">{{ item }}</option></select>
          <select v-model="filters.logic_system"><option value="">全部系统</option><option v-for="item in logicSystems" :key="item">{{ item }}</option></select>
          <select v-model="filters.difficulty"><option value="">全部难度</option><option v-for="item in difficulties" :key="item.value" :value="item.value">{{ item.label }}</option></select>
          <select v-model="filters.review_status"><option value="">全部状态</option><option value="draft">草稿</option><option value="confirmed">已确认</option></select>
          <select v-model="filters.source"><option value="">全部来源</option><option value="manual">手动</option><option value="llm_generated">LLM生成</option><option value="imported">导入</option></select>
          <button @click="applyFilters">筛选</button>
        </div>

        <form class="editor form-panel" @submit.prevent="saveQuestion">
          <h3>{{ editingQuestionId ? '编辑题目' : '手动录入题目' }}</h3>
          <div class="grid-form">
            <label>标题<input v-model="questionForm.title" required /><small v-if="fieldErrors.question_title" class="field-error">{{ fieldErrors.question_title }}</small></label>
            <label>答案<input v-model="questionForm.answer" required /><small v-if="fieldErrors.question_answer" class="field-error">{{ fieldErrors.question_answer }}</small></label>
            <label>题型<select v-model="questionForm.question_type"><option v-for="item in questionTypes" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
            <label>模态类型<select v-model="questionForm.modal_type"><option v-for="item in modalTypes" :key="item">{{ item }}</option></select></label>
            <label>逻辑系统<select v-model="questionForm.logic_system"><option v-for="item in logicSystems" :key="item">{{ item }}</option></select></label>
            <label>难度<select v-model="questionForm.difficulty"><option v-for="item in difficulties" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
            <label>嵌套深度<input v-model.number="questionForm.modal_depth" type="number" min="1" max="3" /></label>
            <label>状态<select v-model="questionForm.review_status"><option value="draft">草稿</option><option value="confirmed">已确认</option></select></label>
            <label class="wide">前提列表<textarea v-model="questionForm.premisesText" placeholder="每行一个前提"></textarea></label>
            <label class="wide">题干<textarea v-model="questionForm.question_text" required></textarea><small v-if="fieldErrors.question_text" class="field-error">{{ fieldErrors.question_text }}</small></label>
            <label class="wide">选项<textarea v-model="questionForm.optionsText" placeholder="多选题每行一个选项"></textarea><small v-if="fieldErrors.question_options" class="field-error">{{ fieldErrors.question_options }}</small></label>
            <label class="wide">解析<textarea v-model="questionForm.explanation"></textarea></label>
          </div>
          <button class="primary" type="submit" :disabled="isBusy('questionSave')">
            <span v-if="isBusy('questionSave')" class="spinner"></span>
            {{ isBusy('questionSave') ? '保存中...' : (editingQuestionId ? '保存修改 (Ctrl+Enter)' : '创建题目 (Ctrl+Enter)') }}
          </button>
          <button type="button" @click="questionForm = blankQuestion(); editingQuestionId = null">清空</button>
        </form>

        <div class="editor form-panel">
          <h3>批量导入</h3>
          <div class="inline">
            <select v-model="importForm.format"><option value="json">JSON</option><option value="csv">CSV</option></select>
            <button @click="importQuestions" :disabled="isBusy('import')">
              <span v-if="isBusy('import')" class="spinner"></span>
              {{ isBusy('import') ? '导入中' : '导入' }}
            </button>
          </div>
          <textarea v-model="importForm.content" placeholder="粘贴JSON数组或CSV文本"></textarea>
          <small v-if="fieldErrors.import_content" class="field-error">{{ fieldErrors.import_content }}</small>
        </div>

        <!-- 题目表格（分页 + 批量选择） -->
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th class="check-cell">
                  <input type="checkbox" class="row-check" :checked="allOnPageSelected" @change="toggleSelectAll" title="全选当前页" />
                </th>
                <th>标题</th>
                <th>类型</th>
                <th>系统</th>
                <th>状态</th>
                <th>来源</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in questions"
                :key="item.id"
                :class="{ 'row-highlight': newItemId === item.id }"
              >
                <td class="check-cell">
                  <input type="checkbox" class="row-check" :checked="selectedQuestionIds.has(item.id)" @change="toggleSelect(item.id)" />
                </td>
                <td>
                  <span class="q-title-link" @click="openPreview(item)">{{ item.title }}</span>
                </td>
                <td>{{ item.modal_type }} / {{ labelOf(difficulties, item.difficulty) }}</td>
                <td>{{ item.logic_system }} · {{ item.modal_depth }}层</td>
                <td><span class="pill stamp" :class="item.review_status">{{ item.review_status === 'confirmed' ? '已确认' : '草稿' }}</span></td>
                <td><span class="pill source-stamp" :class="{ imported: item.source === 'imported' }">{{ sourceLabel(item.source) }}</span></td>
                <td class="actions">
                  <button @click="editQuestion(item)">编辑</button>
                  <button @click="openPreview(item)">预览</button>
                  <button @click="duplicateQuestion(item)" :disabled="isBusy(`dup-${item.id}`)">
                    <span v-if="isBusy(`dup-${item.id}`)" class="spinner"></span>复制
                  </button>
                  <button v-if="item.review_status !== 'confirmed'" @click="confirmQuestion(item.id)" :disabled="isBusy(`confirm-${item.id}`)">
                    <span v-if="isBusy(`confirm-${item.id}`)" class="spinner"></span>确认
                  </button>
                  <button v-if="selectedDataset && item.review_status === 'confirmed'" @click="addToDataset(item.id)" :disabled="isBusy(`add-dataset-${item.id}`)">加入数据集</button>
                  <button class="danger" @click="deleteQuestion(item.id)" :disabled="isBusy(`delete-question-${item.id}`)">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="!questions.length" class="table-empty">
            <strong>题库还没有样本</strong>
            <span>可以先生成演示题，或手动录入一条题目。</span>
            <button type="button" @click="goTo('generate')">进入题目生成</button>
          </div>
        </div>

        <!-- 分页控件 -->
        <div v-if="questionsTotalPages > 1" class="pagination">
          <button :disabled="questionsPage === 1" @click="goQuestionsPage(1)" title="第一页">«</button>
          <button :disabled="questionsPage === 1" @click="goQuestionsPage(questionsPage - 1)" title="上一页">‹</button>
          <span>第 {{ questionsPage }} / {{ questionsTotalPages }} 页 · 共 {{ questionsTotal }} 题</span>
          <button :disabled="questionsPage === questionsTotalPages" @click="goQuestionsPage(questionsPage + 1)" title="下一页">›</button>
          <button :disabled="questionsPage === questionsTotalPages" @click="goQuestionsPage(questionsTotalPages)" title="最后一页">»</button>
        </div>
      </section>

      <!-- ══ 数据集管理 ════════════════════════════════════════════ -->
      <section v-if="page === 'datasets'" class="page">
        <header class="page-head"><div><p class="section-tag">数据集管理</p><h2>数据集管理</h2></div><button @click="loadDatasets">刷新</button></header>
        <form class="inline command-bar" @submit.prevent="createDataset">
          <span class="input-wrap"><input v-model="datasetForm.name" placeholder="数据集名称" required /><small v-if="fieldErrors.dataset_name" class="field-error">{{ fieldErrors.dataset_name }}</small></span>
          <input v-model="datasetForm.description" placeholder="描述" />
          <button class="primary" type="submit" :disabled="isBusy('datasetCreate')">
            <span v-if="isBusy('datasetCreate')" class="spinner"></span>
            {{ isBusy('datasetCreate') ? '创建中...' : '创建数据集' }}
          </button>
        </form>
        <div class="split">
          <div class="list-panel">
            <button v-for="dataset in datasets" :key="dataset.id" class="list-item" :class="{ active: selectedDataset?.id === dataset.id }" @click="openDataset(dataset.id)">
              <strong>{{ dataset.name }}</strong><span>{{ dataset.question_count }}题</span>
            </button>
          </div>
          <div v-if="selectedDataset" class="detail-panel dataset-profile">
            <div class="page-head">
              <h3>{{ selectedDataset.name }}</h3>
              <div class="actions">
                <span class="export-badge">可导出 JSON</span>
                <button @click="download(`/datasets/${selectedDataset.id}/export`, `dataset-${selectedDataset.id}.json`)">导出JSON</button>
                <button class="danger" @click="deleteDataset(selectedDataset.id)" :disabled="isBusy(`delete-dataset-${selectedDataset.id}`)">删除</button>
              </div>
            </div>
            <p class="muted">{{ selectedDataset.description || '无描述' }}</p>
            <div class="metrics">
              <div><span>题目总数</span><strong>{{ selectedDataset.stats.total }}</strong></div>
              <div><span>已确认题库</span><strong>{{ confirmedCountGlobal }}</strong></div>
            </div>
            <div class="charts">
              <div v-for="(group, key) in selectedDataset.stats" v-show="key !== 'total'" :key="key" class="chart">
                <h4>{{ key }}</h4>
                <div v-for="(value, name) in group" :key="name" class="bar-row">
                  <span>{{ name }}</span>
                  <i :style="{ width: percent(value, selectedDataset.stats.total) }"></i>
                  <b>{{ value }}</b>
                </div>
              </div>
            </div>
            <div class="table-wrap">
              <table>
                <thead><tr><th>题目</th><th>答案</th><th>分类</th><th>操作</th></tr></thead>
                <tbody>
                  <tr v-for="item in selectedDataset.questions" :key="item.id">
                    <td>{{ item.title }}</td>
                    <td>{{ item.answer }}</td>
                    <td>{{ item.modal_type }} / {{ item.logic_system }}</td>
                    <td><button @click="removeFromDataset(item.id)">移除</button></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div v-else class="empty-state">
            <img :src="emptyState" alt="暂无数据集" />
            <strong>选择或创建一个数据集</strong>
            <span>这里会展示题目分布、格式比例和 JSON 导出入口。</span>
            <button type="button" @click="createDemoFlow" :disabled="isBusy('demoFlow')">一键准备演示数据</button>
          </div>
        </div>
      </section>

      <!-- ══ 模型评测 ══════════════════════════════════════════════ -->
      <section v-if="page === 'evaluate'" class="page">
        <header class="page-head"><div><p class="section-tag">模型评测</p><h2>模型评测</h2></div><button @click="loadTasks">刷新任务</button></header>
        <div class="experiment-hero amber">
          <div>
            <span>评测流程</span>
            <strong>选择数据集 → 配置模型 → 选择提示模板 → 生成统计报告</strong>
          </div>
          <div class="pipeline">
            <i class="active">数据</i><i>模型</i><i>模板</i><i>报告</i>
          </div>
        </div>
        <form class="editor form-panel" @submit.prevent="createEvalTask">
          <div class="grid-form">
            <label>数据集<select v-model.number="evalForm.dataset_id" required><option value="">请选择</option><option v-for="dataset in datasets" :key="dataset.id" :value="dataset.id">{{ dataset.name }}</option></select><small v-if="fieldErrors.eval_dataset" class="field-error">{{ fieldErrors.eval_dataset }}</small></label>
            <label>任务名称<input v-model="evalForm.task_name" required /><small v-if="fieldErrors.eval_name" class="field-error">{{ fieldErrors.eval_name }}</small></label>
          </div>
          <h3>模型配置</h3>
          <div v-for="(model, index) in evalForm.models" :key="index" class="grid-form compact">
            <label>model_name<input v-model="model.model_name" required /><small v-if="fieldErrors[`eval_model_${index}`]" class="field-error">{{ fieldErrors[`eval_model_${index}`] }}</small></label>
            <label>base_url<input v-model="model.base_url" placeholder="演示模式可留空" /></label>
            <label>api_key<input v-model="model.api_key" type="password" placeholder="仅运行时使用" /></label>
          </div>
          <button type="button" @click="addModel">添加模型</button>
          <h3>提示策略</h3>
          <div v-for="(strategy, index) in evalForm.strategies" :key="index" class="grid-form compact">
            <label>策略<select v-model="strategy.strategy_type"><option v-for="item in strategies" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
            <label>模板<select v-model.number="strategy.prompt_template_id"><option v-for="template in templatesForStrategy(strategy.strategy_type)" :key="template.id" :value="template.id">{{ template.name }}</option></select><small v-if="fieldErrors.eval_strategy" class="field-error">{{ fieldErrors.eval_strategy }}</small></label>
          </div>
          <button type="button" @click="addStrategy">添加策略</button>
          <button class="primary" type="submit" :disabled="isBusy('evalCreate')">
            <span v-if="isBusy('evalCreate')" class="spinner"></span>
            {{ isBusy('evalCreate') ? '任务创建中...' : '发起评测 (Ctrl+Enter)' }}
          </button>
        </form>
      </section>

      <!-- ══ 统计报告 ══════════════════════════════════════════════ -->
      <section v-if="page === 'reports'" class="page">
        <header class="page-head"><div><p class="section-tag">统计报告</p><h2>统计报告</h2></div><button @click="loadTasks">刷新</button></header>
        <div class="split">
          <div class="list-panel">
            <button v-for="task in tasks" :key="task.id" class="list-item" :class="{ active: selectedTask?.id === task.id }" @click="openTask(task.id)">
              <strong>{{ task.task_name }}</strong><span>{{ task.status }} · {{ task.finished_questions }}/{{ task.total_questions }}</span>
            </button>
          </div>
          <div v-if="selectedTask" class="detail-panel report-dashboard">
            <div class="page-head">
              <h3>{{ selectedTask.task_name }}</h3>
              <div class="actions">
                <button @click="download(`/eval-tasks/${selectedTask.id}/export?format=json`, `eval-${selectedTask.id}.json`)">导出JSON</button>
                <button @click="download(`/eval-tasks/${selectedTask.id}/export?format=csv`, `eval-${selectedTask.id}.csv`)">导出CSV</button>
                <button v-if="['pending','running'].includes(selectedTask.status)" @click="cancelTask(selectedTask.id)">取消</button>
              </div>
            </div>
            <div class="progress"><i :style="{ width: percent(selectedTask.finished_questions, selectedTask.total_questions) }"></i></div>
            <h4 class="subsection-title">准确率统计</h4>
            <div class="metrics">
              <div><span>状态</span><strong>{{ selectedTask.status }}</strong></div>
              <div><span>总体准确率</span><strong>{{ reportOverall ? Math.round(reportOverall.accuracy * 100) + '%' : '待生成' }}</strong></div>
              <div><span>总预测数</span><strong>{{ selectedTask.predictions.length }}</strong></div>
              <div><span>失败数量</span><strong>{{ selectedTask.predictions.filter(p => p.status === 'failed').length }}</strong></div>
            </div>

            <!-- 分组 SVG 条形图 -->
            <h4 class="subsection-title">分类统计图表</h4>
            <div class="report-charts-grid">
              <div v-for="groupType in reportGroupTypes" :key="groupType" class="report-chart-section">
                <h4>{{ reportGroupLabels[groupType] || groupType }}</h4>
                <div v-for="report in reportsOfType(groupType)" :key="report.id" class="chart-bar-row">
                  <span class="chart-bar-label">{{ report.group_name }}</span>
                  <div class="chart-bar-track">
                    <div class="chart-bar-fill" :style="{ '--bar-w': `${Math.round(report.accuracy * 100)}%` }"></div>
                  </div>
                  <span class="chart-bar-value">{{ Math.round(report.accuracy * 100) }}%</span>
                  <small class="chart-bar-meta">{{ report.correct }}/{{ report.total }}</small>
                </div>
              </div>
            </div>

            <h4 class="subsection-title">原始输出</h4>
            <div class="table-wrap">
              <table>
                <thead><tr><th>题目ID</th><th>模型</th><th>策略</th><th>解析/标准</th><th>状态</th><th>原始输出</th></tr></thead>
                <tbody>
                  <tr v-for="item in selectedTask.predictions" :key="item.id">
                    <td>{{ item.question_id }}</td>
                    <td>{{ item.model_name }}</td>
                    <td>{{ item.strategy_type }}</td>
                    <td>{{ item.parsed_answer }} / {{ item.gold_answer }}</td>
                    <td>{{ item.status }} {{ item.is_correct ? '✓正确' : '✗错误' }}</td>
                    <td class="raw">{{ item.raw_output || item.error_message }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div v-else class="empty-state report-empty">
            <img :src="reportGraphic" alt="暂无评测报告" />
            <strong>选择一个历史评测任务</strong>
            <span>模型对比、策略对比和单题输出会在这里形成统计报告。</span>
            <button type="button" @click="goTo('evaluate')">去创建评测任务</button>
          </div>
        </div>
      </section>

      <!-- ══ 提示模板 ══════════════════════════════════════════════ -->
      <section v-if="page === 'templates'" class="page">
        <header class="page-head"><div><p class="section-tag">提示模板</p><h2>提示模板</h2></div><button @click="loadTemplates">刷新</button></header>
        <form class="editor form-panel" @submit.prevent="createTemplate">
          <div class="grid-form">
            <label>名称<input v-model="templateForm.name" required /><small v-if="fieldErrors.template_name" class="field-error">{{ fieldErrors.template_name }}</small></label>
            <label>策略<select v-model="templateForm.strategy_type"><option v-for="item in strategies" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
            <label class="wide">模板内容<textarea v-model="templateForm.template_content" required placeholder="使用 {question} 和 {examples} 占位"></textarea><small v-if="fieldErrors.template_content" class="field-error">{{ fieldErrors.template_content }}</small></label>
          </div>
          <button class="primary" type="submit" :disabled="isBusy('templateCreate')">
            <span v-if="isBusy('templateCreate')" class="spinner"></span>
            {{ isBusy('templateCreate') ? '创建中...' : '新建模板' }}
          </button>
        </form>
        <div class="template-grid">
          <article v-for="template in templates" :key="template.id">
            <h3>{{ template.name }}</h3>
            <p class="muted">{{ template.strategy_type }} · {{ template.user_id ? '自定义' : '系统默认' }}</p>
            <pre>{{ template.template_content }}</pre>
            <button v-if="template.user_id" class="danger" @click="deleteTemplate(template)">删除</button>
          </article>
        </div>
      </section>

      <!-- ══ 管理后台 ══════════════════════════════════════════════ -->
      <section v-if="page === 'adminHub'" class="page admin-console">
        <header class="page-head"><div><p class="section-tag">系统管理</p><h2>系统管理后台</h2></div><button @click="loadAdmin">刷新管理数据</button></header>
        <div class="admin-hero">
          <div>
            <span class="status-dot" :class="systemHealth"></span>
            <p class="section-tag">接口状态</p>
            <h2>{{ systemHealth === 'healthy' ? '系统接口运行正常' : '接口状态检查中' }}</h2>
            <p>管理员可集中查看用户、题目、数据集、评测任务和异常情况。</p>
          </div>
          <img :src="reportGraphic" alt="系统管理概览图" />
        </div>
        <div class="admin-grid">
          <button v-for="card in adminCards" :key="card.title" class="module-card admin-card" @click="goTo(card.key)">
            <strong>{{ card.title }}</strong>
            <b>{{ card.value }}</b>
            <span>{{ card.hint }}</span>
          </button>
        </div>
        <div v-if="adminOverview" class="metrics">
          <div><span>用户</span><strong>{{ adminOverview.users }}</strong></div>
          <div><span>题目</span><strong>{{ adminOverview.questions }}</strong></div>
          <div><span>数据集</span><strong>{{ adminOverview.datasets }}</strong></div>
          <div><span>评测</span><strong>{{ adminOverview.eval_tasks }}</strong></div>
        </div>

        <!-- 活动日志 -->
        <div class="hub-grid">
          <article class="insight-panel">
            <p class="section-tag">最近活动</p>
            <h3>系统活动日志</h3>
            <div class="activity-log">
              <div v-for="(event, i) in activityLog.slice(0, 8)" :key="i" class="activity-item">
                <span class="activity-dot" :class="event.type"></span>
                <div>
                  <strong>{{ event.description }}</strong>
                  <small>{{ event.username }} · {{ event.time }}</small>
                </div>
              </div>
              <div v-if="!activityLog.length" class="muted">暂无活动记录。</div>
            </div>
          </article>
          <article class="insight-panel">
            <p class="section-tag">风险概览</p>
            <h3>需关注事项</h3>
            <div class="risk-grid" style="grid-template-columns: 1fr">
              <article class="risk-panel">
                <span class="risk-level amber">待审核</span>
                <strong>{{ draftQuestions.length }} 个草稿题</strong>
                <p>建议优先确认题干、前提、答案和解析完整性，避免未审样本进入数据集。</p>
                <button type="button" @click="goTo('adminContent')">查看内容</button>
              </article>
              <article class="risk-panel">
                <span class="risk-level red">异常任务</span>
                <strong>{{ riskyTasks.length }} 个需关注</strong>
                <p>包含失败、取消或有失败预测的评测任务，可作为管理员运维入口。</p>
                <button type="button" @click="goTo('adminTasks')">查看任务</button>
              </article>
            </div>
          </article>
        </div>
      </section>

      <section v-if="page === 'adminUsers'" class="page admin-console">
        <header class="page-head"><div><p class="section-tag">用户管理</p><h2>用户管理</h2></div><button @click="loadAdmin">刷新用户</button></header>
        <div class="profile-grid">
          <article v-for="item in userProfiles" :key="`profile-${item.id}`" class="profile-card">
            <div>
              <strong>{{ item.username }}</strong>
              <span>{{ item.role }}</span>
            </div>
            <p>{{ item.email || '未填写邮箱' }}</p>
            <div class="profile-metrics">
              <b>{{ item.questions }}</b><span>题</span>
              <b>{{ item.datasets }}</b><span>集</span>
              <b>{{ item.tasks }}</b><span>任务</span>
            </div>
          </article>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>ID</th><th>用户名</th><th>邮箱</th><th>角色</th><th>创建时间</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="item in adminUsers" :key="item.id">
                <td>{{ item.id }}</td>
                <td>{{ item.username }}</td>
                <td>{{ item.email }}</td>
                <td><span class="pill confirmed">{{ item.role }}</span></td>
                <td>{{ item.created_at }}</td>
                <td><button v-if="item.id !== user.id" class="danger" @click="deleteUser(item.id)">删除用户</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-if="page === 'adminContent'" class="page admin-console">
        <header class="page-head"><div><p class="section-tag">内容审核</p><h2>内容审核</h2></div><button @click="loadDashboard">刷新内容</button></header>
        <div class="metrics">
          <div><span>题目总数</span><strong>{{ questions.length }}</strong></div>
          <div><span>待确认草稿</span><strong>{{ draftQuestions.length }}</strong></div>
          <div><span>已确认题目</span><strong>{{ confirmedQuestions.length }}</strong></div>
          <div><span>数据集</span><strong>{{ datasets.length }}</strong></div>
        </div>
        <div class="risk-grid">
          <article class="risk-panel">
            <span class="risk-level amber">审核队列</span>
            <strong>{{ draftQuestions.length }} 个草稿待确认</strong>
            <p>草稿题不会进入数据集，管理员可在表格中直接确认或删除异常样本。</p>
          </article>
          <article class="risk-panel">
            <span class="risk-level cyan">质量巡检</span>
            <strong>{{ invalidQuestions.length }} 个题目缺字段</strong>
            <p>重点检查前提、题干、答案、解析和选择题选项，保证软著演示数据完整。</p>
          </article>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>题目</th><th>归属用户</th><th>分类</th><th>状态</th><th>来源</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="item in questions" :key="item.id">
                <td>{{ item.title }}</td>
                <td>#{{ item.user_id }}</td>
                <td>{{ item.modal_type }} / {{ item.logic_system }} / {{ labelOf(difficulties, item.difficulty) }}</td>
                <td><span class="pill stamp" :class="item.review_status">{{ item.review_status === 'confirmed' ? '已确认' : '草稿' }}</span></td>
                <td><span class="pill source-stamp" :class="{ imported: item.source === 'imported' }">{{ sourceLabel(item.source) }}</span></td>
                <td class="actions">
                  <button v-if="item.review_status !== 'confirmed'" @click="confirmQuestion(item.id)">确认</button>
                  <button class="danger" @click="deleteQuestion(item.id)">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>数据集</th><th>归属用户</th><th>题目数</th><th>描述</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="dataset in datasets" :key="dataset.id">
                <td>{{ dataset.name }}</td>
                <td>#{{ dataset.user_id }}</td>
                <td>{{ dataset.question_count }}</td>
                <td>{{ dataset.description || '无描述' }}</td>
                <td><button class="danger" @click="deleteDataset(dataset.id)">删除</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-if="page === 'adminTasks'" class="page admin-console">
        <header class="page-head"><div><p class="section-tag">评测任务监管</p><h2>评测任务监管</h2></div><button @click="loadTasks">刷新任务</button></header>
        <div class="metrics">
          <div><span>任务总数</span><strong>{{ tasks.length }}</strong></div>
          <div><span>运行中</span><strong>{{ runningTasks }}</strong></div>
          <div><span>已完成</span><strong>{{ completedTasks }}</strong></div>
          <div><span>失败任务</span><strong>{{ failedTasks }}</strong></div>
        </div>
        <div class="risk-grid">
          <article class="risk-panel">
            <span class="risk-level red">异常任务</span>
            <strong>{{ riskyTasks.length }} 个任务需关注</strong>
            <p>失败、取消或存在失败预测的任务会进入该队列，便于截图展示运维能力。</p>
          </article>
          <article class="risk-panel">
            <span class="risk-level cyan">预测失败</span>
            <strong>{{ failedPredictions }} 条失败记录</strong>
            <p>失败记录来自模型调用或解析阶段，报告页仍会保留原始输出与错误信息。</p>
          </article>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>任务</th><th>用户</th><th>数据集</th><th>状态</th><th>进度</th><th>创建时间</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="task in tasks" :key="task.id">
                <td>{{ task.task_name }}</td>
                <td>#{{ task.user_id }}</td>
                <td>#{{ task.dataset_id }}</td>
                <td><span class="pill" :class="{ confirmed: task.status === 'completed' }">{{ task.status }}</span></td>
                <td>{{ task.finished_questions }}/{{ task.total_questions }}</td>
                <td>{{ task.created_at }}</td>
                <td><button v-if="['pending','running'].includes(task.status)" @click="cancelTask(task.id)">取消</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </section>
  </main>
</template>
