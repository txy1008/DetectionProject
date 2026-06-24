<template>
  <section class="mx-auto max-w-[1500px] px-4 py-8 lg:px-6">
    <div class="mb-6 rounded-[2rem] border border-white/80 bg-white/75 p-6 shadow-soft backdrop-blur-xl">
      <div class="flex flex-col justify-between gap-5 lg:flex-row lg:items-center">
        <div>
          <el-tag class="!rounded-full !border-0 !bg-primary !font-bold !text-[#303326]">Data Analysis</el-tag>
          <h1 class="mt-3 text-3xl font-black tracking-tight md:text-4xl">检测数据分析中心</h1>
          <p class="mt-2 max-w-3xl text-sm leading-6 text-olive">选择历史 CSV 文件，查看检测类别统计、时间趋势、记录明细，并导出 Word 报告。</p>
        </div>
        <div class="flex flex-wrap gap-3">
          <el-button class="!rounded-full !border-0 !bg-[#C8E087] !font-bold !text-[#303326]" @click="loadCsvFiles">刷新文件</el-button>
          <el-button class="!rounded-full !border-0 !bg-[#303326] !font-bold !text-white" @click="exportWord">导出Word</el-button>
        </div>
      </div>
    </div>

    <div class="grid gap-5 xl:grid-cols-[340px_1fr]">
      <aside class="space-y-5">
        <div class="rounded-[2rem] border border-white/80 bg-white/75 p-5 shadow-soft backdrop-blur-xl">
          <div class="mb-4 flex items-center justify-between">
            <h2 class="text-xl font-black">历史 CSV 文件</h2>
            <el-icon class="text-olive" :size="22"><FolderOpened /></el-icon>
          </div>
          <el-select v-model="selectedCsv" class="w-full" size="large" placeholder="选择历史 CSV" filterable @change="loadHistoryData">
            <el-option v-for="file in csvFiles" :key="file.name" :label="file.name" :value="file.name">
              <div class="flex items-center justify-between gap-3">
                <span>{{ file.name }}</span>
                <span class="text-xs text-olive">{{ file.size_kb }} KB</span>
              </div>
            </el-option>
          </el-select>
          <div class="mt-4 rounded-3xl bg-[#f7faef] p-4 text-sm leading-7 text-olive">
            <p>接口：/api/history/files</p>
            <p>数据：/api/history/data</p>
            <p>当前：{{ selectedCsv || '未选择' }}</p>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div v-for="card in statCards" :key="card.label" class="rounded-[1.5rem] border border-white/80 bg-white/75 p-5 shadow-sm">
            <p class="text-sm font-bold text-olive">{{ card.label }}</p>
            <p class="mt-2 text-3xl font-black text-[#303326]">{{ card.value }}</p>
          </div>
        </div>
      </aside>

      <main class="space-y-5">
        <div class="grid gap-5 lg:grid-cols-2">
          <div class="rounded-[2rem] border border-white/80 bg-white/75 p-5 shadow-soft backdrop-blur-xl">
            <div class="mb-4">
              <p class="text-xs font-black uppercase tracking-[0.25em] text-sage">Category Bar</p>
              <h2 class="text-xl font-black">类别数量柱状图</h2>
            </div>
            <div ref="barChartRef" class="h-[360px]"></div>
          </div>

          <div class="rounded-[2rem] border border-white/80 bg-white/75 p-5 shadow-soft backdrop-blur-xl">
            <div class="mb-4">
              <p class="text-xs font-black uppercase tracking-[0.25em] text-sage">Time Trend</p>
              <h2 class="text-xl font-black">检测时间趋势折线图</h2>
            </div>
            <div ref="lineChartRef" class="h-[360px]"></div>
          </div>
        </div>

        <div class="rounded-[2rem] border border-white/80 bg-white/75 p-5 shadow-soft backdrop-blur-xl">
          <div class="mb-4 flex flex-col justify-between gap-3 md:flex-row md:items-center">
            <div>
              <p class="text-xs font-black uppercase tracking-[0.25em] text-sage">History Records</p>
              <h2 class="text-xl font-black">历史检测记录</h2>
            </div>
            <el-input v-model="keyword" class="md:!w-72" clearable placeholder="搜索类别 / 路径 / 时间" />
          </div>

          <el-table :data="filteredRecords" height="460" class="rounded-2xl">
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="category" label="类别" width="120" />
            <el-table-column prop="time" label="时间" width="130" />
            <el-table-column prop="path" label="存储路径" min-width="260" show-overflow-tooltip />
          </el-table>
        </div>
      </main>
    </div>
  </section>
</template>

<script setup>
import axios from 'axios'
import * as echarts from 'echarts'
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { FolderOpened } from '@element-plus/icons-vue'

const API_BASE = '/api'
const csvFiles = ref([])
const selectedCsv = ref('')
const records = ref([])
const keyword = ref('')
const barChartRef = ref(null)
const lineChartRef = ref(null)
let barChart = null
let lineChart = null

const request = async (url, config = {}) => axios({ url: `${API_BASE}${url}`, ...config })

const normalizedRecords = computed(() => records.value.map((item, index) => ({
  id: item.id ?? item.ID ?? index + 1,
  category: item.category ?? item.type ?? item['类别'] ?? 'unknown',
  time: item.time ?? item['时间'] ?? '',
  path: item.path ?? item['存储路径'] ?? item.img_path ?? ''
})))

const filteredRecords = computed(() => {
  const key = keyword.value.trim().toLowerCase()
  if (!key) return normalizedRecords.value
  return normalizedRecords.value.filter((item) => Object.values(item).some((value) => String(value).toLowerCase().includes(key)))
})

const categoryCounts = computed(() => {
  const counts = { car: 0, bicycle: 0, person: 0, unknown: 0 }
  normalizedRecords.value.forEach((item) => {
    if (counts[item.category] === undefined) {
      counts.unknown += 1
    } else {
      counts[item.category] += 1
    }
  })
  return counts
})

const timeCounts = computed(() => {
  const counts = {}
  normalizedRecords.value.forEach((item) => {
    const key = String(item.time || '未知').slice(0, 5)
    counts[key] = (counts[key] || 0) + 1
  })
  return Object.entries(counts).sort(([a], [b]) => a.localeCompare(b))
})

const statCards = computed(() => [
  { label: '机动车', value: categoryCounts.value.car },
  { label: '非机动车', value: categoryCounts.value.bicycle },
  { label: '行人', value: categoryCounts.value.person },
  { label: '总计', value: normalizedRecords.value.length }
])

const loadCsvFiles = async () => {
  try {
    const { data } = await request('/history/files')
    csvFiles.value = data.files || []
    if (!selectedCsv.value && csvFiles.value.length) {
      selectedCsv.value = csvFiles.value[0].name
      await loadHistoryData()
    }
  } catch (error) {
    ElMessage.error('历史 CSV 文件接口未连接')
  }
}

const loadHistoryData = async () => {
  if (!selectedCsv.value) return
  try {
    const { data } = await request('/history/data', { params: { file: selectedCsv.value } })
    records.value = data.records || []
    await nextTick()
    renderCharts()
  } catch (error) {
    ElMessage.error('历史数据加载失败')
  }
}

const renderCharts = () => {
  if (!barChartRef.value || !lineChartRef.value) return
  barChart = barChart || echarts.init(barChartRef.value)
  lineChart = lineChart || echarts.init(lineChartRef.value)

  const categoryLabels = ['机动车', '非机动车', '行人', '未知']
  const categoryValues = [categoryCounts.value.car, categoryCounts.value.bicycle, categoryCounts.value.person, categoryCounts.value.unknown]
  barChart.setOption({
    color: ['#82846D'],
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 30, bottom: 40 },
    xAxis: { type: 'category', data: categoryLabels, axisLine: { lineStyle: { color: '#95A472' } } },
    yAxis: { type: 'value', axisLine: { lineStyle: { color: '#95A472' } }, splitLine: { lineStyle: { color: '#E8EEDB' } } },
    series: [{ type: 'bar', data: categoryValues, barWidth: 38, itemStyle: { borderRadius: [12, 12, 0, 0], color: '#C8E087' } }]
  })

  const trend = timeCounts.value
  lineChart.setOption({
    color: ['#82846D'],
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 30, bottom: 40 },
    xAxis: { type: 'category', data: trend.map(([time]) => time), axisLine: { lineStyle: { color: '#95A472' } } },
    yAxis: { type: 'value', axisLine: { lineStyle: { color: '#95A472' } }, splitLine: { lineStyle: { color: '#E8EEDB' } } },
    series: [{ type: 'line', smooth: true, data: trend.map(([, count]) => count), areaStyle: { color: 'rgba(221,252,173,0.45)' }, lineStyle: { width: 4 }, symbolSize: 8 }]
  })
}

const exportWord = () => {
  const token = localStorage.getItem('vision_token')
  const query = selectedCsv.value
    ? `?file=${encodeURIComponent(selectedCsv.value)}&token=${token}`
    : `?token=${token}`
  window.open(`${API_BASE}/history/export_word${query}`, '_blank')
}

const resizeCharts = () => {
  barChart?.resize()
  lineChart?.resize()
}

onMounted(async () => {
  await loadCsvFiles()
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  barChart?.dispose()
  lineChart?.dispose()
})
</script>
