<script setup>
import { computed, onMounted, ref } from 'vue'
import { api, download, getToken, setToken } from './api'

const user = ref(null)
const page = ref('generate')
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

const questions = ref([])
const datasets = ref([])
const templates = ref([])
const tasks = ref([])
const adminUsers = ref([])
const adminOverview = ref(null)
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

const navItems = computed(() => {
  const items = [
    ['generate', '题目生成'],
    ['questions', '题目管理'],
    ['datasets', '数据集管理'],
    ['evaluate', '评测中心'],
    ['reports', '历史报告'],
    ['templates', '模板管理']
  ]
  if (user.value?.role === 'admin') items.push(['admin', '管理后台'])
  return items
})

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
}

async function loadMe() {
  if (!getToken()) return
  try {
    user.value = await api('/auth/me')
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
  page.value = 'questions'
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
  page.value = 'datasets'
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
  page.value = 'reports'
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
const reportOverall = computed(() => selectedTask.value?.reports?.find((item) => item.group_type === 'overall'))

onMounted(loadMe)
</script>

<template>
  <main v-if="!user" class="auth-shell">
    <section class="auth-panel">
      <div>
        <p class="eyebrow">Modal Logic Evaluation</p>
        <h1>模态逻辑推理数据集构建与评测系统</h1>
      </div>
      <div class="segmented">
        <button :class="{ active: authMode === 'login' }" @click="authMode = 'login'">登录</button>
        <button :class="{ active: authMode === 'register' }" @click="authMode = 'register'">注册</button>
      </div>
      <form class="stack" @submit.prevent="signIn">
        <input v-model="authForm.username" placeholder="用户名" required />
        <input v-if="authMode === 'register'" v-model="authForm.email" placeholder="邮箱" required />
        <input v-model="authForm.password" placeholder="密码" type="password" required />
        <button class="primary" type="submit">{{ authMode === 'login' ? '进入系统' : '创建账号' }}</button>
      </form>
      <p class="muted">默认管理员：admin / admin123</p>
      <p v-if="error" class="notice error">{{ error }}</p>
    </section>
  </main>

  <main v-else class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <strong>模态逻辑评测系统</strong>
        <span>{{ user.username }} · {{ user.role === 'admin' ? '管理员' : '普通用户' }}</span>
      </div>
      <nav>
        <button v-for="[key, label] in navItems" :key="key" :class="{ active: page === key }" @click="page = key">
          {{ label }}
        </button>
      </nav>
      <form class="password-box" @submit.prevent="changePassword">
        <input v-model="passwordForm.old_password" type="password" placeholder="原密码" />
        <input v-model="passwordForm.new_password" type="password" placeholder="新密码" />
        <button type="submit">修改密码</button>
      </form>
      <button class="ghost" @click="logout">退出登录</button>
    </aside>

    <section class="workspace">
      <div v-if="message" class="notice success">{{ message }}</div>
      <div v-if="error" class="notice error">{{ error }}</div>

      <section v-if="page === 'generate'" class="page">
        <header class="page-head">
          <h2>题目生成</h2>
          <button @click="loadQuestions">刷新题库</button>
        </header>
        <form class="grid-form" @submit.prevent="generateQuestions">
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
        <header class="page-head"><h2>题目管理</h2><button @click="loadQuestions">刷新</button></header>
        <div class="filters">
          <select v-model="filters.modal_type"><option value="">全部模态</option><option v-for="item in modalTypes" :key="item">{{ item }}</option></select>
          <select v-model="filters.logic_system"><option value="">全部系统</option><option v-for="item in logicSystems" :key="item">{{ item }}</option></select>
          <select v-model="filters.difficulty"><option value="">全部难度</option><option v-for="item in difficulties" :key="item.value" :value="item.value">{{ item.label }}</option></select>
          <select v-model="filters.review_status"><option value="">全部状态</option><option value="draft">草稿</option><option value="confirmed">已确认</option></select>
          <select v-model="filters.source"><option value="">全部来源</option><option value="manual">手动</option><option value="llm_generated">LLM生成</option><option value="imported">导入</option></select>
          <button @click="loadQuestions">筛选</button>
        </div>
        <form class="editor" @submit.prevent="saveQuestion">
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
        <div class="editor">
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
        <header class="page-head"><h2>数据集管理</h2><button @click="loadDatasets">刷新</button></header>
        <form class="inline" @submit.prevent="createDataset">
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
          <div v-if="selectedDataset" class="detail-panel">
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
        </div>
      </section>

      <section v-if="page === 'evaluate'" class="page">
        <header class="page-head"><h2>评测中心</h2><button @click="loadTasks">刷新任务</button></header>
        <form class="editor" @submit.prevent="createEvalTask">
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
        <header class="page-head"><h2>历史报告</h2><button @click="loadTasks">刷新</button></header>
        <div class="split">
          <div class="list-panel">
            <button v-for="task in tasks" :key="task.id" class="list-item" :class="{ active: selectedTask?.id === task.id }" @click="openTask(task.id)">
              <strong>{{ task.task_name }}</strong><span>{{ task.status }} · {{ task.finished_questions }}/{{ task.total_questions }}</span>
            </button>
          </div>
          <div v-if="selectedTask" class="detail-panel">
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
        </div>
      </section>

      <section v-if="page === 'templates'" class="page">
        <header class="page-head"><h2>模板管理</h2><button @click="loadTemplates">刷新</button></header>
        <form class="editor" @submit.prevent="createTemplate">
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

      <section v-if="page === 'admin'" class="page">
        <header class="page-head"><h2>管理后台</h2><button @click="loadAdmin">刷新</button></header>
        <div v-if="adminOverview" class="metrics">
          <div><span>用户</span><strong>{{ adminOverview.users }}</strong></div>
          <div><span>题目</span><strong>{{ adminOverview.questions }}</strong></div>
          <div><span>数据集</span><strong>{{ adminOverview.datasets }}</strong></div>
          <div><span>评测</span><strong>{{ adminOverview.eval_tasks }}</strong></div>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>ID</th><th>用户名</th><th>邮箱</th><th>角色</th><th>创建时间</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="item in adminUsers" :key="item.id">
                <td>{{ item.id }}</td>
                <td>{{ item.username }}</td>
                <td>{{ item.email }}</td>
                <td>{{ item.role }}</td>
                <td>{{ item.created_at }}</td>
                <td><button v-if="item.id !== user.id" class="danger" @click="deleteUser(item.id)">删除用户</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </section>
  </main>
</template>
