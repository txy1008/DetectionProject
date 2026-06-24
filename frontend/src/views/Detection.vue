<template>
  <section class="mx-auto max-w-[1600px] px-4 py-8 lg:px-6">
    <div class="mb-6 flex flex-col justify-between gap-4 rounded-[2rem] border border-white/80 bg-white/70 p-6 shadow-soft backdrop-blur-xl lg:flex-row lg:items-center">
      <div>
        <el-tag class="!rounded-full !border-0 !bg-primary !font-bold !text-[#303326]">Detection Center</el-tag>
        <h1 class="mt-3 text-3xl font-black tracking-tight md:text-4xl">交通目标检测中心</h1>
        <p class="mt-2 text-sm leading-6 text-olive">支持视频流、文件检测、模型切换、检测结果轮询、ID 高亮与报表导出。</p>
      </div>
      <div class="flex items-center gap-3 rounded-2xl bg-[#303326] px-5 py-3 text-white">
        <span class="h-3 w-3 rounded-full" :class="isRunning ? 'bg-green-400' : 'bg-orange-300'"></span>
        <span class="text-sm font-bold">{{ isRunning ? '检测运行中' : '等待启动' }}</span>
      </div>
    </div>

    <div class="grid gap-5 xl:grid-cols-[310px_1fr_430px]">
      <aside class="rounded-[2rem] border border-white/80 bg-white/75 p-5 shadow-soft backdrop-blur-xl">
        <div class="mb-5 flex items-center justify-between">
          <h2 class="text-xl font-black">控制面板</h2>
          <el-icon class="text-olive" :size="22"><Operation /></el-icon>
        </div>

        <div class="space-y-5">
          <div class="rounded-3xl bg-[#f7faef] p-4">
            <p class="mb-3 text-sm font-black text-[#303326]">文件检测</p>
            <el-upload drag :auto-upload="false" :limit="1" :on-change="handleFileChange" :on-remove="handleFileRemove">
              <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
              <div class="el-upload__text">拖拽文件或 <em>点击上传</em></div>
              <template #tip>
                <div class="text-xs text-olive">支持图片/视频，后续提交到后端接口。</div>
              </template>
            </el-upload>
          </div>

          <div>
            <label class="mb-2 block text-sm font-black">模型选择</label>
            <el-select v-model="selectedModel" class="w-full" size="large" @change="setModel">
              <el-option v-for="model in models" :key="model" :label="model" :value="model" />
            </el-select>
          </div>

          <div>
            <div class="mb-2 flex items-center justify-between">
              <label class="text-sm font-black">置信度阈值</label>
              <span class="rounded-full bg-primary px-3 py-1 text-xs font-black text-[#303326]">{{ confidence.toFixed(2) }}</span>
            </div>
            <el-slider v-model="confidence" :min="0.05" :max="0.95" :step="0.01" @change="setConfidence" />
          </div>

          <div class="grid grid-cols-2 gap-3">
            <el-button class="!h-11 !rounded-2xl !border-0 !bg-[#82846D] !font-bold !text-white" @click="openCamera">
              打开摄像头
            </el-button>
            <el-button class="!m-0 !h-11 !rounded-2xl !border-0 !bg-primary !font-bold !text-[#303326]" @click="startDetection">
              开始
            </el-button>
            <el-button class="!m-0 !h-11 !rounded-2xl !border-0 !bg-[#C8E087] !font-bold !text-[#303326]" @click="pauseDetection">
              暂停
            </el-button>
            <el-button class="!m-0 !h-11 !rounded-2xl !border-0 !bg-[#303326] !font-bold !text-white" @click="stopDetection">
              停止
            </el-button>
          </div>

          <div class="rounded-3xl bg-[#303326] p-4 text-white">
            <p class="text-sm font-black text-primary">后端接口状态</p>
            <div class="mt-3 space-y-2 text-xs text-white/70">
              <p>/video_feed：{{ videoFeedUrl }}</p>
              <p>/detection_results：{{ apiStatus }}</p>
              <p>/set_model：{{ modelStatus }}</p>
            </div>
          </div>
        </div>
      </aside>

      <main class="space-y-5">
        <div v-if="!isVideoFile" class="rounded-[2rem] border border-white/80 bg-white/75 p-5 shadow-soft backdrop-blur-xl">
          <div class="mb-4 flex items-center justify-between">
            <div>
              <p class="text-xs font-black uppercase tracking-[0.25em] text-sage">Original Stream</p>
              <h2 class="text-xl font-black">原始画面</h2>
            </div>
            <el-tag class="!rounded-full !border-0 !bg-[#C8E087] !font-bold !text-[#303326]">{{ sourceLabel }}</el-tag>
          </div>
          <div class="relative aspect-video overflow-hidden rounded-[1.5rem] bg-[#181a14]">
            <video v-if="isVideoFile && originalPreview" ref="originalVideoRef" :src="originalPreview" class="h-full w-full object-contain" controls muted playsinline alt="原始视频" />
            <img v-else-if="originalPreview" :src="originalPreview" class="h-full w-full object-contain" alt="原始图片" />
            <img v-else-if="showCameraStream" :src="originalFeedUrlWithParams" class="h-full w-full object-contain" alt="原始视频流" />
            <div v-else class="flex h-full items-center justify-center text-white/50">等待输入源</div>
          </div>
        </div>

        <div class="rounded-[2rem] border border-white/80 bg-white/75 p-5 shadow-soft backdrop-blur-xl">
          <div class="mb-4 flex items-center justify-between">
            <div>
              <p class="text-xs font-black uppercase tracking-[0.25em] text-sage">Detection Result</p>
              <h2 class="text-xl font-black">检测结果画面</h2>
            </div>
            <div class="flex items-center gap-2">
              <el-tag class="!rounded-full !border-0 !bg-primary !font-bold !text-[#303326]">Highlight ID: {{ highlightedId ?? 'None' }}</el-tag>
              <el-button v-if="highlightedId !== null" size="small" class="!rounded-full !border-0 !bg-[#303326] !font-bold !text-white" @click="clearHighlight">
                取消高亮
              </el-button>
            </div>
          </div>
          <div ref="resultStageRef" class="relative aspect-video overflow-hidden rounded-[1.5rem] bg-[#181a14]">
            <img v-if="highlightPreview" :src="highlightPreview" class="h-full w-full object-contain" alt="高亮结果" />
            <img v-else-if="showDetectionStream" :src="videoFeedUrlWithParams" class="h-full w-full object-contain" alt="检测视频流" />
            <img v-else-if="resultPreview" :src="resultPreview" class="h-full w-full object-contain" alt="检测结果" />
            <div v-else class="flex h-full items-center justify-center text-white/50">启动检测后显示结果流</div>
          </div>
        </div>
      </main>

      <aside class="space-y-5">
        <div class="grid grid-cols-2 gap-4">
          <div v-for="card in statCards" :key="card.label" class="rounded-[1.5rem] border border-white/80 bg-white/75 p-5 shadow-sm">
            <p class="text-sm font-bold text-olive">{{ card.label }}</p>
            <p class="mt-2 text-3xl font-black text-[#303326]">{{ card.value }}</p>
          </div>
        </div>

        <div class="rounded-[2rem] border border-white/80 bg-white/75 p-5 shadow-soft backdrop-blur-xl">
          <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p class="text-xs font-black uppercase tracking-[0.25em] text-sage">Records</p>
              <h2 class="text-xl font-black">检测结果表格</h2>
            </div>
            <div class="flex gap-2">
              <el-button class="!rounded-full !border-0 !bg-[#C8E087] !font-bold !text-[#303326]" @click="exportCsv">导出CSV</el-button>
              <el-button class="!rounded-full !border-0 !bg-[#82846D] !font-bold !text-white" @click="exportWord">导出Word</el-button>
              <el-button v-if="isVideoFile" class="!rounded-full !border-0 !bg-[#303326] !font-bold !text-white" @click="exportVideo">导出视频</el-button>
            </div>
          </div>

          <el-table :data="results" height="520" class="rounded-2xl" highlight-current-row @row-click="highlightRow">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="category" label="类别" width="90" />
            <el-table-column prop="confidence" label="置信度" width="90">
              <template #default="{ row }">{{ formatConfidence(row.confidence) }}</template>
            </el-table-column>
            <el-table-column prop="time" label="时间" width="110" />
            <el-table-column prop="path" label="路径" min-width="150" show-overflow-tooltip />
          </el-table>
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup>
import axios from 'axios'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Operation, UploadFilled } from '@element-plus/icons-vue'

const API_BASE = '/api'
const getLastVideoKey = () => {
  const username = localStorage.getItem('vision_username') || 'guest'
  return `vision_last_video_${username}`
}
const models = ['best1.pt', 'best2.pt', 'best3.pt', 'yolov8n.pt', 'yolov8m.pt']
const selectedModel = ref('best3.pt')
const confidence = ref(0.22)
const isRunning = ref(false)
const selectedFile = ref(null)
const persistedVideoName = ref('')
const originalPreview = ref('')
const resultPreview = ref('')
const highlightPreview = ref('')
const uploadedVideoReady = ref(false)
const cameraRequested = ref(false)
const results = ref([])
const highlightedId = ref(null)
const apiStatus = ref('waiting')
const modelStatus = ref('waiting')
const resultStageRef = ref(null)
const pollTimer = ref(null)
const originalVideoRef = ref(null)
const streamTimestamp = ref(Date.now())
const isPaused = ref(false)

// 监听运行状态，联动播放、暂停和复位原始视频，确保完全同步
watch(isRunning, (running) => {
  if (isVideoFile.value && originalVideoRef.value) {
    if (running) {
      originalVideoRef.value.play().catch(err => {
        console.warn('Auto play original video failed:', err)
      })
    } else {
      originalVideoRef.value.pause()
    }
  }
})

const videoFeedUrl = `${API_BASE}/video_feed`
const originalFeedUrl = `${API_BASE}/original_feed`
const videoFeedUrlWithParams = computed(() => `${videoFeedUrl}?model=${encodeURIComponent(selectedModel.value)}&conf=${confidence.value}&t=${streamTimestamp.value}`)
const originalFeedUrlWithParams = computed(() => `${originalFeedUrl}?t=${streamTimestamp.value}`)
const sourceLabel = computed(() => selectedFile.value ? selectedFile.value.name : persistedVideoName.value || 'Camera / Stream')
const isVideoFile = computed(() => {
  const name = selectedFile.value?.name ?? persistedVideoName.value
  return selectedFile.value?.type?.startsWith('video/') || /\.(mp4|avi|mov|mkv|webm)$/i.test(name)
})
const showCameraStream = computed(() => cameraRequested.value || (isRunning.value && !selectedFile.value))
const showDetectionStream = computed(() => isRunning.value && (!selectedFile.value || uploadedVideoReady.value))

const normalizedResults = computed(() => results.value.map((item, index) => ({
  id: item.id ?? item.ID ?? index + 1,
  category: item.category ?? item.type ?? item.label ?? 'unknown',
  confidence: item.confidence ?? item.conf ?? 0,
  time: item.time ?? item.detect_time ?? new Date().toLocaleTimeString(),
  path: item.path ?? item.img_path ?? item.file ?? '',
  box: item.box ?? item.bbox ?? item.xyxy ?? null
})))

const statCards = computed(() => {
  const counts = { car: 0, bicycle: 0, person: 0 }
  normalizedResults.value.forEach((item) => {
    if (counts[item.category] !== undefined) {
      counts[item.category] += 1
    }
  })
  return [
    { label: '机动车', value: counts.car },
    { label: '非机动车', value: counts.bicycle },
    { label: '行人', value: counts.person },
    { label: '总计', value: normalizedResults.value.length }
  ]
})

const handleFileChange = (uploadFile) => {
  selectedFile.value = uploadFile.raw
  originalPreview.value = URL.createObjectURL(uploadFile.raw)
  persistedVideoName.value = ''
  cameraRequested.value = false
  resultPreview.value = ''
  highlightPreview.value = ''
  uploadedVideoReady.value = false
  highlightedId.value = null
  isPaused.value = false
}

const handleFileRemove = () => {
  selectedFile.value = null
  originalPreview.value = ''
  persistedVideoName.value = ''
  resultPreview.value = ''
  highlightPreview.value = ''
  uploadedVideoReady.value = false
  highlightedId.value = null
  isPaused.value = false
  localStorage.removeItem(getLastVideoKey())
}

const request = async (method, url, data = undefined, config = {}) => {
  return axios({ method, url: `${API_BASE}${url}`, data, ...config })
}

const setModel = async () => {
  try {
    await request('post', '/set_model', { model: selectedModel.value })
    modelStatus.value = 'ok'
    ElMessage.success(`已切换模型：${selectedModel.value}`)
  } catch (error) {
    modelStatus.value = 'offline'
    ElMessage.warning('模型切换接口暂未连接，前端选择已保留')
  }
}

const setConfidence = async () => {
  try {
    await request('post', '/set_confidence', { confidence: confidence.value })
  } catch (error) {
    ElMessage.info('置信度接口暂未连接，将作为视频流参数传递')
  }
}

const openCamera = async () => {
  streamTimestamp.value = Date.now()
  selectedFile.value = null
  originalPreview.value = ''
  persistedVideoName.value = ''
  resultPreview.value = ''
  highlightPreview.value = ''
  uploadedVideoReady.value = false
  highlightedId.value = null
  isPaused.value = false
  localStorage.removeItem(getLastVideoKey())
  try {
    await request('post', '/open_camera')
    cameraRequested.value = true
    isRunning.value = true
    startPolling()
    ElMessage.success('摄像头请求已发送')
  } catch (error) {
    ElMessage.info('摄像头接口暂未连接，将使用 /video_feed 预览')
  }
}

const startDetection = async () => {
  streamTimestamp.value = Date.now()
  try {
    if (!selectedFile.value && persistedVideoName.value) {
      ElMessage.warning('检测服务已重置，请在“文件检测”中重新选择或拖入该视频文件再点击开始！')
      return
    }
    if (isPaused.value && (uploadedVideoReady.value || cameraRequested.value)) {
      await request('post', '/start_detection', { model: selectedModel.value, confidence: confidence.value })
      isPaused.value = false
      isRunning.value = true
      ElMessage.success('已恢复检测')
    } else if (selectedFile.value) {
      const formData = new FormData()
      formData.append('file', selectedFile.value)
      formData.append('model', selectedModel.value)
      formData.append('confidence', confidence.value)
      const { data } = await request('post', '/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
      if (data.type === 'video') {
        const videoUrl = data.video_url?.startsWith('/uploads') ? data.video_url : `/uploads/${selectedFile.value.name}`
        originalPreview.value = `${videoUrl}?t=${Date.now()}`
        persistedVideoName.value = selectedFile.value.name
        localStorage.setItem(getLastVideoKey(), JSON.stringify({ type: 'video', name: selectedFile.value.name, url: videoUrl }))
        uploadedVideoReady.value = true
        resultPreview.value = ''
        isRunning.value = true
        isPaused.value = false
        ElMessage.success('视频已上传，正在显示检测流')
      } else if (data.original_image) {
        const token = localStorage.getItem('vision_token')
        originalPreview.value = `${API_BASE}${data.original_image.replace(/^\/api/, '')}?t=${Date.now()}&token=${token}`
        if (data.result_image) {
          resultPreview.value = `${API_BASE}${data.result_image.replace(/^\/api/, '')}?t=${Date.now()}&token=${token}`
        }
        if (data.results) {
          results.value = data.results
        }
        localStorage.setItem(getLastVideoKey(), JSON.stringify({
          type: 'image',
          name: selectedFile.value.name,
          original_image: data.original_image,
          result_image: data.result_image,
          results: data.results
        }))
        isRunning.value = false
        isPaused.value = false
      }
      highlightPreview.value = ''
      highlightedId.value = null
    } else {
      await request('post', '/start_detection', { model: selectedModel.value, confidence: confidence.value })
      cameraRequested.value = true
      highlightPreview.value = ''
      highlightedId.value = null
      isRunning.value = true
      isPaused.value = false
    }
  } catch (error) {
    console.error('startDetection failed:', error)
    ElMessage.info('启动接口暂未连接，已进入前端预览状态')
    if (!selectedFile.value) {
      isRunning.value = true
    }
  }
  if (originalVideoRef.value && isRunning.value) {
    originalVideoRef.value.play().catch(err => console.warn('Sync original video play failed:', err))
  }
  startPolling()
}

const pauseDetection = async () => {
  try {
    await request('post', '/pause_detection')
    if (originalVideoRef.value) {
      originalVideoRef.value.pause()
    }
    isPaused.value = true
  } catch (error) {
    ElMessage.info('暂停接口暂未连接')
  }
}

const stopDetection = async () => {
  try {
    await request('post', '/stop_detection')
  } catch (error) {
    ElMessage.info('停止接口暂未连接')
  }
  if (originalVideoRef.value) {
    originalVideoRef.value.currentTime = 0
  }
  isPaused.value = false
  isRunning.value = false
  cameraRequested.value = false
  highlightPreview.value = ''
  uploadedVideoReady.value = false
  highlightedId.value = null
  stopPolling()
}

const fetchResults = async () => {
  try {
    const { data } = await request('get', '/detection_results')
    const list = Array.isArray(data) ? data : data.results ?? data.records ?? []
    results.value = list.map((item, index) => ({
      id: item.id ?? item.ID ?? index + 1,
      category: item.category ?? item.type ?? item.label ?? 'unknown',
      confidence: item.confidence ?? item.conf ?? 0,
      time: item.time ?? item.detect_time ?? new Date().toLocaleTimeString(),
      path: item.path ?? item.img_path ?? item.file ?? '',
      box: item.box ?? item.bbox ?? item.xyxy ?? null
    }))
    if (data.result_image || data.image) {
      const image = data.result_image ?? data.image
      resultPreview.value = image.startsWith('/api') ? image : `${API_BASE}${image}`
    }
    apiStatus.value = 'ok'
  } catch (error) {
    apiStatus.value = 'offline'
  }
}

const startPolling = () => {
  stopPolling()
  fetchResults()
  pollTimer.value = window.setInterval(fetchResults, 1200)
}

const stopPolling = () => {
  if (pollTimer.value) {
    window.clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

const highlightRow = async (row) => {
  highlightedId.value = row.id
  highlightPreview.value = `${API_BASE}/highlight/${row.id}?t=${Date.now()}`
  ElMessage.success(`已高亮目标 ID：${row.id}`)
}

const clearHighlight = () => {
  highlightedId.value = null
  highlightPreview.value = ''
}

const exportCsv = () => {
  const token = localStorage.getItem('vision_token')
  window.open(`${API_BASE}/export_csv?token=${token}`, '_blank')
}

const exportWord = () => {
  const token = localStorage.getItem('vision_token')
  window.open(`${API_BASE}/export_word?token=${token}`, '_blank')
}

const exportVideo = () => {
  const token = localStorage.getItem('vision_token')
  window.open(`${API_BASE}/export_video?token=${token}`, '_blank')
}

const formatConfidence = (value) => {
  const numberValue = Number(value)
  if (Number.isNaN(numberValue)) return '0.00'
  return numberValue <= 1 ? numberValue.toFixed(2) : `${numberValue.toFixed(1)}%`
}

onMounted(() => {
  const savedSource = localStorage.getItem(getLastVideoKey())
  if (savedSource) {
    try {
      const source = JSON.parse(savedSource)
      if (source.type === 'video' || (!source.type && source.url)) {
        // 视频源：加载视频
        originalPreview.value = `${source.url}?t=${Date.now()}`
        persistedVideoName.value = source.name
        uploadedVideoReady.value = true
      } else if (source.type === 'image') {
        // 图片源：加载并还原刚才测试完的图片内容
        const token = localStorage.getItem('vision_token')
        originalPreview.value = `${API_BASE}${source.original_image.replace(/^\/api/, '')}?t=${Date.now()}&token=${token}`
        if (source.result_image) {
          resultPreview.value = `${API_BASE}${source.result_image.replace(/^\/api/, '')}?t=${Date.now()}&token=${token}`
        }
        if (source.results) {
          results.value = source.results
        }
        persistedVideoName.value = source.name
      }
    } catch (error) {
      localStorage.removeItem(getLastVideoKey())
    }
  }
  fetchResults()
})

onBeforeUnmount(() => {
  stopPolling()
})
</script>
