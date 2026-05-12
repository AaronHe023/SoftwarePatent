<script setup>
import { computed, onMounted, ref } from 'vue'
import { api, download, getToken, setToken } from './api'
import logicNetwork from './assets/logic-network.svg'
import emptyLab from './assets/empty-lab.svg'
import reportMatrix from './assets/report-matrix.svg'

const user = ref(null)
const page = ref('hub')
const theme = ref(localStorage.getItem('software_patent_theme') || 'light')
const message = ref('')
const error = ref('')
const authMode = ref('login')
const authForm = ref({ username: '', email: '', password: '' })
const passwordForm = ref({ old_password: '', new_password: '' })

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
  hub: { code: 'HUB', title: '实验舱首页', subtitle: '从生成、确认、构建、评测到导出，按科研流程推进一次完整实验', accent: 'Workbench Hub' },
  generate: { code: 'GEN', title: '实验生成台', subtitle: '按模态类型、逻辑系统和推理深度编排题目生成实验', accent: '题目生产' },
  questions: { code: 'QBK', title: '题库资产库', subtitle: '沉淀、筛选、确认和复用模态逻辑推理样本', accent: '样本治理' },
  datasets: { code: 'DST', title: '数据集画像', subtitle: '把确认题目组织成可导出的评测数据资产', accent: '数据构建' },
  evaluate: { code: 'RUN', title: '评测任务编排', subtitle: '组合模型与提示策略，形成批量推理评测任务', accent: '实验运行' },
  reports: { code: 'RPT', title: '评测报告矩阵', subtitle: '查看总体准确率、分类指标和模型策略对比', accent: '结果分析' },
  templates: { code: 'TPL', title: '提示词模板库', subtitle: '管理 Zero-shot、CoT、Few-shot 等策略模板', accent: 'Prompt资产' },
  adminHub: { code: 'ADM', title: '系统管理舱', subtitle: '管理员查看系统健康、用户、内容资产和评测任务风险', accent: 'Admin Console' },
  adminUsers: { code: 'USR', title: '用户与权限', subtitle: '查看用户清单、角色身份和账号创建情况', accent: 'Identity Control' },
  adminContent: { code: 'CNT', title: '内容监管', subtitle: '集中查看题目资产、数据集资产与待确认内容', accent: 'Content Review' },
  adminTasks: { code: 'OPS', title: '任务运维', subtitle: '追踪评测任务状态、失败数量与运行进度', accent: 'Evaluation Ops' }
}

const pageCatalog = [
  { key: 'hub', label: '实验舱', code: 'HUB' },
  { key: 'generate', label: '生成', code: 'GEN' },
  { key: 'questions', label: '题库', code: 'QBK' },
  { key: 'datasets', label: '数据集', code: 'DST' },
  { key: 'evaluate', label: '评测', code: 'RUN' },
  { key: 'reports', label: '报告', code: 'RPT' },
  { key: 'templates', label: '模板', code: 'TPL' }
]

const adminCatalog = [
  { key: 'adminHub', label: '总览', code: 'ADM' },
  { key: 'adminUsers', label: '用户', code: 'USR' },
  { key: 'adminContent', label: '内容', code: 'CNT' },
  { key: 'adminTasks', label: '任务', code: 'OPS' }
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
}

function showError(err) {
  error.value = err.message || String(err)
  message.value = ''
}

async function signIn() {
  try {
    const path = authMode.value === 'login' ? '/auth/login' : '/auth/register'
    const body = authMode.value === 'login'
      ? { username: authForm.value.username, password: authForm.value.password }
      : authForm.value
    const data = await api(path, { method: 'POST', body: JSON.stringify(body) })
    setToken(data.token)
    user.value = data.user
    goTo(pageFromHash(data.user.role))
    await loadDashboard()
    showOk('登录成功')
  } catch (err) {
    showError(err)
  }
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
  try {
    await api('/auth/change-password', { method: 'POST', body: JSON.stringify(passwordForm.value) })
    passwordForm.value = { old_password: '', new_password: '' }
    showOk('密码已修改')
  } catch (err) {
    showError(err)
  }
}

async function loadDashboard() {
  await Promise.all([loadQuestions(), loadDatasets(), loadTemplates(), loadTasks()])
  if (user.value?.role === 'admin') await loadAdmin()
}

async function loadQuestions() {
  const query = new URLSearchParams()
  Object.entries(filters.value).forEach(([key, value]) => value && query.set(key, value))
  questions.value = await api(`/questions${query.toString() ? `?${query}` : ''}`)
}

function normalizeQuestionForm() {
  return {
    ...questionForm.value,
    premises: questionForm.value.premisesText.split('\n').map((item) => item.trim()).filter(Boolean),
    options: questionForm.value.optionsText.split('\n').map((item) => item.trim()).filter(Boolean)
  }
}

async function saveQuestion() {
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
  } catch (err) {
    showError(err)
  }
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
  try {
    await api(`/questions/${id}/confirm`, { method: 'POST' })
    await loadQuestions()
    showOk('题目已确认')
  } catch (err) {
    showError(err)
  }
}

async function deleteQuestion(id) {
  if (!window.confirm('确认删除该题目？')) return
  try {
    await api(`/questions/${id}`, { method: 'DELETE' })
    await loadQuestions()
    showOk('题目已删除')
  } catch (err) {
    showError(err)
  }
}

async function generateQuestions() {
  try {
    await api('/questions/generate', { method: 'POST', body: JSON.stringify(generationForm.value) })
    await loadQuestions()
    showOk('已生成草稿题目，可在题目管理中编辑确认')
  } catch (err) {
    showError(err)
  }
}

async function importQuestions() {
  try {
    const result = await api('/questions/import', { method: 'POST', body: JSON.stringify(importForm.value) })
    await loadQuestions()
    showOk(`导入完成：成功${result.created}条，错误${result.errors.length}条`)
  } catch (err) {
    showError(err)
  }
}

async function loadDatasets() {
  datasets.value = await api('/datasets')
  if (selectedDataset.value) await openDataset(selectedDataset.value.id)
}

async function createDataset() {
  try {
    const data = await api('/datasets', { method: 'POST', body: JSON.stringify(datasetForm.value) })
    datasetForm.value = { name: '', description: '' }
    selectedDataset.value = data
    await loadDatasets()
    showOk('数据集已创建')
  } catch (err) {
    showError(err)
  }
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
  try {
    await api(`/datasets/${id}`, { method: 'DELETE' })
    if (selectedDataset.value?.id === id) selectedDataset.value = null
    await loadDatasets()
    showOk('数据集已删除')
  } catch (err) {
    showError(err)
  }
}

async function loadTemplates() {
  templates.value = await api('/prompt-templates')
}

async function createTemplate() {
  try {
    await api('/prompt-templates', { method: 'POST', body: JSON.stringify(templateForm.value) })
    templateForm.value = { name: '', strategy_type: 'zero_shot', template_content: '' }
    await loadTemplates()
    showOk('模板已创建')
  } catch (err) {
    showError(err)
  }
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
  try {
    const data = await api('/eval-tasks', { method: 'POST', body: JSON.stringify(evalForm.value) })
    selectedTask.value = data
    await loadTasks()
    showOk('评测任务已创建，系统正在后台执行')
  } catch (err) {
    showError(err)
  }
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

async function loadAdmin() {
  adminUsers.value = await api('/admin/users')
  adminOverview.value = await api('/admin/overview')
  try {
    await api('/health')
    systemHealth.value = 'healthy'
  } catch {
    systemHealth.value = 'offline'
  }
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

function labelOf(list, value) {
  return list.find((item) => item.value === value)?.label || value
}

function templatesForStrategy(strategyType) {
  return templates.value.filter((template) => template.strategy_type === strategyType)
}

function percent(value, total) {
  if (!total) return '0%'
  return `${Math.round((value / total) * 100)}%`
}

const confirmedQuestions = computed(() => questions.value.filter((item) => item.review_status === 'confirmed'))
const draftQuestions = computed(() => questions.value.filter((item) => item.review_status === 'draft'))
const importedQuestions = computed(() => questions.value.filter((item) => item.source === 'imported'))
const reportOverall = computed(() => selectedTask.value?.reports?.find((item) => item.group_type === 'overall'))
const pageInfo = computed(() => moduleMeta[page.value] || moduleMeta.generate)
const runningTasks = computed(() => tasks.value.filter((item) => ['pending', 'running'].includes(item.status)).length)
const completedTasks = computed(() => tasks.value.filter((item) => item.status === 'completed').length)
const failedTasks = computed(() => tasks.value.filter((item) => item.status === 'failed').length)
const confirmedRate = computed(() => percent(confirmedQuestions.value.length, questions.value.length))
const failedPredictions = computed(() => tasks.value.reduce((sum, task) => sum + (task.failed_count || 0), 0))
const workflowCards = computed(() => [
  { key: 'generate', step: '01', title: '生成题目', text: '配置模态类型和逻辑系统，生成可编辑草稿。', metric: `${draftQuestions.value.length} 个草稿`, cta: '进入生成台' },
  { key: 'questions', step: '02', title: '确认题库', text: '审核题干、前提、答案和解析，沉淀 confirmed 样本。', metric: `${confirmedQuestions.value.length}/${questions.value.length} 已确认`, cta: '整理题库' },
  { key: 'datasets', step: '03', title: '构建数据集', text: '从确认题库中组装评测集合，并导出标准 JSON。', metric: `${datasets.value.length} 个数据集`, cta: '查看数据集' },
  { key: 'evaluate', step: '04', title: '运行评测', text: '组合模型和 Prompt 策略，批量记录模型输出。', metric: `${runningTasks.value} 个运行中`, cta: '编排任务' },
  { key: 'reports', step: '05', title: '分析报告', text: '查看准确率矩阵、分类表现和单题输出明细。', metric: `${completedTasks.value} 份完成`, cta: '查看报告' }
])
const adminCards = computed(() => [
  { key: 'adminUsers', title: '用户与权限', value: adminUsers.value.length, hint: '注册账号 / 管理身份' },
  { key: 'adminContent', title: '内容监管', value: questions.value.length, hint: `${draftQuestions.value.length} 个草稿待确认` },
  { key: 'adminContent', title: '数据集资产', value: datasets.value.length, hint: '全量数据集与题目关联' },
  { key: 'adminTasks', title: '评测运维', value: tasks.value.length, hint: `${failedTasks.value} 个失败任务` }
])

onMounted(() => {
  applyTheme()
  window.addEventListener('hashchange', syncHash)
  loadMe()
})
</script>

<template>
  <main v-if="!user" class="auth-shell">
    <section class="auth-hero">
      <div class="hero-copy">
        <p class="eyebrow">MODAL LOGIC LAB · V1.0</p>
        <h1>面向大语言模型的模态逻辑推理评测工作台</h1>
        <p class="hero-text">把题目生成、数据集构建、Prompt 策略和模型评测串成一条可演示、可追踪、可导出的科研流程。</p>
        <div class="hero-metrics">
          <div><span>Modal Types</span><strong>4</strong></div>
          <div><span>Logic Systems</span><strong>K/T/S4/S5</strong></div>
          <div><span>Report Groups</span><strong>7</strong></div>
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
      <div class="panel-kicker">Secure Workspace</div>
      <h2>{{ authMode === 'login' ? '进入评测工作台' : '创建研究账号' }}</h2>
      <div class="segmented">
        <button :class="{ active: authMode === 'login' }" @click="authMode = 'login'">登录</button>
        <button :class="{ active: authMode === 'register' }" @click="authMode = 'register'">注册</button>
      </div>
      <form class="stack" @submit.prevent="signIn">
        <input v-model="authForm.username" placeholder="用户名" required />
        <input v-if="authMode === 'register'" v-model="authForm.email" placeholder="邮箱" required />
        <input v-model="authForm.password" placeholder="密码" type="password" required />
        <button class="primary" type="submit">{{ authMode === 'login' ? '启动系统' : '创建账号' }}</button>
      </form>
      <p class="muted">默认管理员：admin / admin123</p>
      <p v-if="error" class="notice error">{{ error }}</p>
    </section>
  </main>

  <main v-else class="shell" :class="{ 'admin-shell': isAdminMode }">
    <aside class="nav-rail">
      <div class="brand">
        <span class="brand-mark">ML</span>
        <div>
          <strong>ModalLogic Lab</strong>
          <span>{{ isAdminMode ? '系统管理舱' : '科研评测工作台' }}</span>
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
        <button type="submit">修改密码</button>
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
            <div><span>题库</span><strong>{{ questions.length }}</strong></div>
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

      <div v-if="message" class="notice success">{{ message }}</div>
      <div v-if="error" class="notice error">{{ error }}</div>

      <section v-if="page === 'hub'" class="page hub-canvas">
        <div class="hub-hero">
          <div>
            <p class="section-tag">Research Flow</p>
            <h2>从一道模态逻辑题，到一份模型评测报告</h2>
            <p>点击流程节点直接进入对应模块。系统会把题目状态、数据集资产和评测结果持续汇总到这里。</p>
          </div>
          <img :src="logicNetwork" alt="模态逻辑实验流程" />
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
            <p class="section-tag">Asset Snapshot</p>
            <h3>题库资产状态</h3>
            <div class="mini-bars">
              <div><span>已确认</span><i :style="{ width: confirmedRate }"></i><b>{{ confirmedQuestions.length }}</b></div>
              <div><span>草稿</span><i :style="{ width: percent(draftQuestions.length, questions.length) }"></i><b>{{ draftQuestions.length }}</b></div>
              <div><span>导入</span><i :style="{ width: percent(importedQuestions.length, questions.length) }"></i><b>{{ importedQuestions.length }}</b></div>
            </div>
          </article>
          <article class="insight-panel image-slot">
            <img :src="emptyLab" alt="实验资产占位" />
            <div>
              <p class="section-tag">Image Slot</p>
              <h3>这里预留后续截图/插图位</h3>
              <span>可替换为系统流程图、软著截图或论文展示图。</span>
            </div>
          </article>
        </div>
      </section>

      <section v-if="page === 'generate'" class="page">
        <header class="page-head">
          <div>
            <p class="section-tag">Experiment Composer</p>
            <h2>题目生成</h2>
          </div>
          <button @click="loadQuestions">刷新题库</button>
        </header>
        <div class="experiment-hero">
          <div>
            <span>Pipeline</span>
            <strong>参数设定 → LLM 草稿 → 人工确认 → 题库沉淀</strong>
          </div>
          <div class="pipeline">
            <i class="active">01</i><i>02</i><i>03</i><i>04</i>
          </div>
        </div>
        <form class="grid-form lab-panel" @submit.prevent="generateQuestions">
          <label>模态类型<select v-model="generationForm.modal_type"><option v-for="item in modalTypes" :key="item">{{ item }}</option></select></label>
          <label>逻辑系统<select v-model="generationForm.logic_system"><option v-for="item in logicSystems" :key="item">{{ item }}</option></select></label>
          <label>难度<select v-model="generationForm.difficulty"><option v-for="item in difficulties" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
          <label>嵌套深度<input v-model.number="generationForm.modal_depth" type="number" min="1" max="3" /></label>
          <label>题目格式<select v-model="generationForm.question_type"><option v-for="item in questionTypes" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
          <label>生成数量<input v-model.number="generationForm.count" type="number" min="1" max="50" /></label>
          <label>base_url<input v-model="generationForm.base_url" placeholder="可留空进入演示模式" /></label>
          <label>model_name<input v-model="generationForm.model_name" placeholder="可留空" /></label>
          <label class="wide">api_key<input v-model="generationForm.api_key" type="password" placeholder="仅本次请求使用，不入库" /></label>
          <button class="primary wide" type="submit">生成草稿题目</button>
        </form>
      </section>

      <section v-if="page === 'questions'" class="page">
        <header class="page-head"><div><p class="section-tag">Question Asset Bank</p><h2>题目管理</h2></div><button @click="loadQuestions">刷新</button></header>
        <div class="filters command-bar">
          <select v-model="filters.modal_type"><option value="">全部模态</option><option v-for="item in modalTypes" :key="item">{{ item }}</option></select>
          <select v-model="filters.logic_system"><option value="">全部系统</option><option v-for="item in logicSystems" :key="item">{{ item }}</option></select>
          <select v-model="filters.difficulty"><option value="">全部难度</option><option v-for="item in difficulties" :key="item.value" :value="item.value">{{ item.label }}</option></select>
          <select v-model="filters.review_status"><option value="">全部状态</option><option value="draft">草稿</option><option value="confirmed">已确认</option></select>
          <select v-model="filters.source"><option value="">全部来源</option><option value="manual">手动</option><option value="llm_generated">LLM生成</option><option value="imported">导入</option></select>
          <button @click="loadQuestions">筛选</button>
        </div>
        <form class="editor lab-panel" @submit.prevent="saveQuestion">
          <h3>{{ editingQuestionId ? '编辑题目' : '手动录入题目' }}</h3>
          <div class="grid-form">
            <label>标题<input v-model="questionForm.title" required /></label>
            <label>答案<input v-model="questionForm.answer" required /></label>
            <label>题型<select v-model="questionForm.question_type"><option v-for="item in questionTypes" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
            <label>模态类型<select v-model="questionForm.modal_type"><option v-for="item in modalTypes" :key="item">{{ item }}</option></select></label>
            <label>逻辑系统<select v-model="questionForm.logic_system"><option v-for="item in logicSystems" :key="item">{{ item }}</option></select></label>
            <label>难度<select v-model="questionForm.difficulty"><option v-for="item in difficulties" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
            <label>嵌套深度<input v-model.number="questionForm.modal_depth" type="number" min="1" max="3" /></label>
            <label>状态<select v-model="questionForm.review_status"><option value="draft">草稿</option><option value="confirmed">已确认</option></select></label>
            <label class="wide">前提列表<textarea v-model="questionForm.premisesText" placeholder="每行一个前提"></textarea></label>
            <label class="wide">题干<textarea v-model="questionForm.question_text" required></textarea></label>
            <label class="wide">选项<textarea v-model="questionForm.optionsText" placeholder="多选题每行一个选项"></textarea></label>
            <label class="wide">解析<textarea v-model="questionForm.explanation"></textarea></label>
          </div>
          <button class="primary" type="submit">{{ editingQuestionId ? '保存修改' : '创建题目' }}</button>
          <button type="button" @click="questionForm = blankQuestion(); editingQuestionId = null">清空</button>
        </form>
        <div class="editor lab-panel">
          <h3>批量导入</h3>
          <div class="inline">
            <select v-model="importForm.format"><option value="json">JSON</option><option value="csv">CSV</option></select>
            <button @click="importQuestions">导入</button>
          </div>
          <textarea v-model="importForm.content" placeholder="粘贴JSON数组或CSV文本"></textarea>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>标题</th><th>类型</th><th>系统</th><th>状态</th><th>来源</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="item in questions" :key="item.id">
                <td>{{ item.title }}</td>
                <td>{{ item.modal_type }} / {{ labelOf(difficulties, item.difficulty) }}</td>
                <td>{{ item.logic_system }} · {{ item.modal_depth }}层</td>
                <td><span class="pill" :class="item.review_status">{{ item.review_status === 'confirmed' ? '已确认' : '草稿' }}</span></td>
                <td>{{ item.source }}</td>
                <td class="actions">
                  <button @click="editQuestion(item)">编辑</button>
                  <button v-if="item.review_status !== 'confirmed'" @click="confirmQuestion(item.id)">确认</button>
                  <button v-if="selectedDataset && item.review_status === 'confirmed'" @click="addToDataset(item.id)">加入数据集</button>
                  <button class="danger" @click="deleteQuestion(item.id)">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-if="page === 'datasets'" class="page">
        <header class="page-head"><div><p class="section-tag">Dataset Profile</p><h2>数据集管理</h2></div><button @click="loadDatasets">刷新</button></header>
        <form class="inline command-bar" @submit.prevent="createDataset">
          <input v-model="datasetForm.name" placeholder="数据集名称" required />
          <input v-model="datasetForm.description" placeholder="描述" />
          <button class="primary" type="submit">创建数据集</button>
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
                <button @click="download(`/datasets/${selectedDataset.id}/export`, `dataset-${selectedDataset.id}.json`)">导出JSON</button>
                <button class="danger" @click="deleteDataset(selectedDataset.id)">删除</button>
              </div>
            </div>
            <p class="muted">{{ selectedDataset.description || '无描述' }}</p>
            <div class="metrics">
              <div><span>题目总数</span><strong>{{ selectedDataset.stats.total }}</strong></div>
              <div><span>已确认题库</span><strong>{{ confirmedQuestions.length }}</strong></div>
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
            <img :src="emptyLab" alt="暂无数据集" />
            <strong>选择或创建一个数据集</strong>
            <span>数据集画像会在这里展示题目分布、格式比例和可导出资产。</span>
          </div>
        </div>
      </section>

      <section v-if="page === 'evaluate'" class="page">
        <header class="page-head"><div><p class="section-tag">Evaluation Orchestration</p><h2>评测中心</h2></div><button @click="loadTasks">刷新任务</button></header>
        <div class="experiment-hero amber">
          <div>
            <span>Runbook</span>
            <strong>数据集 → 模型组 → Prompt 策略 → 批量评测报告</strong>
          </div>
          <div class="pipeline">
            <i class="active">DATA</i><i>MODEL</i><i>PROMPT</i><i>REPORT</i>
          </div>
        </div>
        <form class="editor lab-panel" @submit.prevent="createEvalTask">
          <div class="grid-form">
            <label>数据集<select v-model.number="evalForm.dataset_id" required><option value="">请选择</option><option v-for="dataset in datasets" :key="dataset.id" :value="dataset.id">{{ dataset.name }}</option></select></label>
            <label>任务名称<input v-model="evalForm.task_name" required /></label>
          </div>
          <h3>模型配置</h3>
          <div v-for="(model, index) in evalForm.models" :key="index" class="grid-form compact">
            <label>model_name<input v-model="model.model_name" required /></label>
            <label>base_url<input v-model="model.base_url" placeholder="演示模式可留空" /></label>
            <label>api_key<input v-model="model.api_key" type="password" placeholder="仅运行时使用" /></label>
          </div>
          <button type="button" @click="addModel">添加模型</button>
          <h3>提示策略</h3>
          <div v-for="(strategy, index) in evalForm.strategies" :key="index" class="grid-form compact">
            <label>策略<select v-model="strategy.strategy_type"><option v-for="item in strategies" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
            <label>模板<select v-model.number="strategy.prompt_template_id"><option v-for="template in templatesForStrategy(strategy.strategy_type)" :key="template.id" :value="template.id">{{ template.name }}</option></select></label>
          </div>
          <button type="button" @click="addStrategy">添加策略</button>
          <button class="primary" type="submit">发起评测</button>
        </form>
      </section>

      <section v-if="page === 'reports'" class="page">
        <header class="page-head"><div><p class="section-tag">Result Matrix</p><h2>历史报告</h2></div><button @click="loadTasks">刷新</button></header>
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
            <div class="metrics">
              <div><span>状态</span><strong>{{ selectedTask.status }}</strong></div>
              <div><span>总体准确率</span><strong>{{ reportOverall ? Math.round(reportOverall.accuracy * 100) + '%' : '待生成' }}</strong></div>
              <div><span>失败数量</span><strong>{{ selectedTask.predictions.filter(p => p.status === 'failed').length }}</strong></div>
            </div>
            <div class="charts">
              <div v-for="report in selectedTask.reports.filter(r => r.group_type !== 'overall')" :key="report.id" class="chart">
                <h4>{{ report.group_type }} · {{ report.group_name }}</h4>
                <div class="bar-row"><span>准确率</span><i :style="{ width: `${Math.round(report.accuracy * 100)}%` }"></i><b>{{ Math.round(report.accuracy * 100) }}%</b></div>
              </div>
            </div>
            <div class="table-wrap">
              <table>
                <thead><tr><th>题目ID</th><th>模型</th><th>策略</th><th>解析/标准</th><th>状态</th><th>原始输出</th></tr></thead>
                <tbody>
                  <tr v-for="item in selectedTask.predictions" :key="item.id">
                    <td>{{ item.question_id }}</td>
                    <td>{{ item.model_name }}</td>
                    <td>{{ item.strategy_type }}</td>
                    <td>{{ item.parsed_answer }} / {{ item.gold_answer }}</td>
                    <td>{{ item.status }} {{ item.is_correct ? '正确' : '错误' }}</td>
                    <td class="raw">{{ item.raw_output || item.error_message }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div v-else class="empty-state report-empty">
            <img :src="reportMatrix" alt="暂无评测报告" />
            <strong>选择一个历史评测任务</strong>
            <span>模型横向对比、策略对比和单题输出会在这里形成报告矩阵。</span>
          </div>
        </div>
      </section>

      <section v-if="page === 'templates'" class="page">
        <header class="page-head"><div><p class="section-tag">Prompt Library</p><h2>模板管理</h2></div><button @click="loadTemplates">刷新</button></header>
        <form class="editor lab-panel" @submit.prevent="createTemplate">
          <div class="grid-form">
            <label>名称<input v-model="templateForm.name" required /></label>
            <label>策略<select v-model="templateForm.strategy_type"><option v-for="item in strategies" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
            <label class="wide">模板内容<textarea v-model="templateForm.template_content" required placeholder="使用 {question} 和 {examples} 占位"></textarea></label>
          </div>
          <button class="primary" type="submit">新建模板</button>
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

      <section v-if="page === 'adminHub'" class="page admin-console">
        <header class="page-head"><div><p class="section-tag">System Control</p><h2>管理舱总览</h2></div><button @click="loadAdmin">刷新管理数据</button></header>
        <div class="admin-hero">
          <div>
            <span class="status-dot" :class="systemHealth"></span>
            <p class="section-tag">API Health</p>
            <h2>{{ systemHealth === 'healthy' ? '系统接口运行正常' : '接口状态检查中' }}</h2>
            <p>管理员视角聚焦监管与运维，不混用普通研究用户的生成、构建、评测流程。</p>
          </div>
          <img :src="reportMatrix" alt="管理舱矩阵" />
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
      </section>

      <section v-if="page === 'adminUsers'" class="page admin-console">
        <header class="page-head"><div><p class="section-tag">Identity Control</p><h2>用户与权限</h2></div><button @click="loadAdmin">刷新用户</button></header>
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
        <header class="page-head"><div><p class="section-tag">Content Review</p><h2>内容监管</h2></div><button @click="loadDashboard">刷新内容</button></header>
        <div class="metrics">
          <div><span>题目总数</span><strong>{{ questions.length }}</strong></div>
          <div><span>待确认草稿</span><strong>{{ draftQuestions.length }}</strong></div>
          <div><span>已确认题目</span><strong>{{ confirmedQuestions.length }}</strong></div>
          <div><span>数据集</span><strong>{{ datasets.length }}</strong></div>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>题目</th><th>归属用户</th><th>分类</th><th>状态</th><th>来源</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="item in questions" :key="item.id">
                <td>{{ item.title }}</td>
                <td>#{{ item.user_id }}</td>
                <td>{{ item.modal_type }} / {{ item.logic_system }} / {{ labelOf(difficulties, item.difficulty) }}</td>
                <td><span class="pill" :class="item.review_status">{{ item.review_status === 'confirmed' ? '已确认' : '草稿' }}</span></td>
                <td>{{ item.source }}</td>
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
        <header class="page-head"><div><p class="section-tag">Evaluation Ops</p><h2>评测任务运维</h2></div><button @click="loadTasks">刷新任务</button></header>
        <div class="metrics">
          <div><span>任务总数</span><strong>{{ tasks.length }}</strong></div>
          <div><span>运行中</span><strong>{{ runningTasks }}</strong></div>
          <div><span>已完成</span><strong>{{ completedTasks }}</strong></div>
          <div><span>失败任务</span><strong>{{ failedTasks }}</strong></div>
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
