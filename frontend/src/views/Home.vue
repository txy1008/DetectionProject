<template>
  <section class="mx-auto max-w-7xl px-6 py-16 lg:px-8 lg:py-24">
    <div class="grid items-center gap-12 lg:grid-cols-[1.05fr_0.95fr]">
      <div>
        <el-tag class="!mb-6 !rounded-full !border-0 !bg-primary !px-4 !py-3 !text-sm !font-bold !text-[#303326]">
          AI Traffic Vision Platform
        </el-tag>
        <h1 class="max-w-4xl text-5xl font-black leading-tight tracking-tight text-[#303326] md:text-7xl">
          智慧路口视频监控系统
        </h1>
        <p class="mt-6 max-w-2xl text-xl font-semibold text-[#5d614d]">
          让路口感知更精准，让交通治理更高效。
        </p>
        <p class="mt-5 max-w-2xl text-base leading-8 text-olive">
          系统面向城市道路场景，融合 YOLOv8 目标检测、DeepSORT 多目标追踪与数据分析能力，支持实时视频、文件上传、检测统计与后端数据库对接。
        </p>
        <div class="mt-9 flex flex-wrap gap-4">
          <el-button size="large" class="!h-12 !rounded-full !border-0 !bg-[#82846D] !px-8 !font-bold !text-white hover:!bg-[#6f715c]" @click="$router.push('/detection')">
            进入检测中心
          </el-button>
          <el-button size="large" class="!h-12 !rounded-full !border-[#95A472] !bg-white/70 !px-8 !font-bold !text-[#5d614d]" @click="$router.push('/analysis')">
            查看数据分析
          </el-button>
        </div>
      </div>

      <div class="relative">
        <div class="rounded-[2rem] border border-white/80 bg-white/70 p-5 shadow-soft backdrop-blur-xl">
          <div class="rounded-[1.5rem] bg-[#303326] p-4 text-white">
            <div class="mb-4 flex items-center justify-between">
              <div>
                <p class="text-sm text-primary">Live Intersection</p>
                <p class="text-2xl font-black">实时监控面板</p>
              </div>
              <div class="rounded-full bg-primary px-3 py-1 text-xs font-black text-[#303326]">ONLINE</div>
            </div>
            <div class="grid gap-3 sm:grid-cols-3">
              <div v-for="item in stats" :key="item.label" class="rounded-2xl bg-white/10 p-4">
                <p class="text-xs text-white/60">{{ item.label }}</p>
                <p class="mt-2 text-3xl font-black text-primary">{{ item.value }}</p>
              </div>
            </div>
            <div class="mt-5 rounded-3xl bg-gradient-to-br from-[#DDFCAD] to-[#95A472] p-5 text-[#303326]">
              <div class="grid grid-cols-6 gap-2">
                <div v-for="index in 24" :key="index" class="h-10 rounded-xl bg-white/40" :class="index % 5 === 0 ? 'bg-[#82846D]/70' : ''"></div>
              </div>
              <p class="mt-5 text-sm font-bold">检测流、追踪 ID、分类统计与告警数据可通过 API 实时接入。</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <section class="mt-24">
      <div class="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p class="text-sm font-black uppercase tracking-[0.3em] text-sage">Services</p>
          <h2 class="mt-3 text-4xl font-black">核心服务能力</h2>
        </div>
        <p class="max-w-xl text-olive">面向前后端分离系统设计，后续可直接连接 Python Flask 或 FastAPI 接口。</p>
      </div>

      <div class="grid gap-6 md:grid-cols-3">
        <div v-for="service in services" :key="service.title" class="group rounded-[2rem] border border-white/80 bg-white/70 p-7 shadow-sm transition hover:-translate-y-1 hover:shadow-soft">
          <div class="mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-[#303326] transition group-hover:bg-[#82846D] group-hover:text-white">
            <el-icon :size="26"><component :is="service.icon" /></el-icon>
          </div>
          <h3 class="text-2xl font-black">{{ service.title }}</h3>
          <p class="mt-4 leading-7 text-olive">{{ service.desc }}</p>
        </div>
      </div>
    </section>

    <section class="mt-24 rounded-[2.5rem] bg-[#303326] p-8 text-white shadow-soft lg:p-12">
      <div class="grid gap-10 lg:grid-cols-[0.8fr_1.2fr]">
        <div>
          <p class="text-sm font-black uppercase tracking-[0.3em] text-primary">Showcase</p>
          <h2 class="mt-3 text-4xl font-black">项目展示</h2>
          <p class="mt-5 leading-8 text-white/70">首页为系统门户，后续检测中心可接入视频流上传、模型选择、检测结果返回；数据分析页可接入 MySQL 统计接口。</p>
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div v-for="item in showcase" :key="item" class="rounded-3xl bg-white/10 p-6">
            <p class="text-xl font-black text-primary">{{ item }}</p>
          </div>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup>
import { DataAnalysis, UploadFilled, VideoCamera } from '@element-plus/icons-vue'

const stats = [
  { label: '机动车', value: '128' },
  { label: '非机动车', value: '76' },
  { label: '行人', value: '43' }
]

const services = [
  { title: '实时检测', desc: '接入摄像头或视频流，实时识别机动车、非机动车和行人。', icon: VideoCamera },
  { title: '文件检测', desc: '支持上传图片或视频文件，调用 Python 后端完成检测与结果返回。', icon: UploadFilled },
  { title: '数据分析', desc: '结合数据库记录生成趋势、分类占比和检测报表。', icon: DataAnalysis }
]

const showcase = ['YOLOv8 目标检测', 'DeepSORT 轨迹追踪', 'MySQL 数据持久化', 'Vue3 前端展示']
</script>
