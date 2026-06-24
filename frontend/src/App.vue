<template>
  <div class="min-h-screen overflow-hidden bg-[#f7faef] text-[#303326]">
    <div class="pointer-events-none fixed inset-0 -z-10">
      <div class="absolute -left-24 top-10 h-72 w-72 rounded-full bg-primary/70 blur-3xl"></div>
      <div class="absolute right-0 top-60 h-96 w-96 rounded-full bg-secondary/60 blur-3xl"></div>
      <div class="absolute bottom-0 left-1/3 h-80 w-80 rounded-full bg-sage/20 blur-3xl"></div>
    </div>

    <header v-if="!isAuthPage" class="sticky top-0 z-50 border-b border-white/50 bg-[#f7faef]/80 backdrop-blur-xl">
      <nav class="mx-auto flex max-w-7xl items-center justify-between px-6 py-4 lg:px-8">
        <RouterLink to="/" class="flex items-center gap-3">
          <div class="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#DDFCAD] shadow-soft">
            <el-icon :size="24"><Monitor /></el-icon>
          </div>
          <div>
            <p class="text-lg font-black tracking-tight">智慧路口</p>
            <p class="text-xs font-medium text-olive">Video Monitor System</p>
          </div>
        </RouterLink>

        <div class="hidden items-center gap-2 rounded-full border border-white/70 bg-white/60 p-1 shadow-sm md:flex">
          <RouterLink v-for="item in navItems" :key="item.path" :to="item.path" class="rounded-full px-4 py-2 text-sm font-semibold text-olive transition hover:bg-primary/70 hover:text-[#303326]">
            {{ item.label }}
          </RouterLink>
        </div>

        <div class="flex items-center gap-4">
          <div v-if="username" class="flex items-center gap-3 bg-white/60 px-4 py-1.5 rounded-full border border-white/80 shadow-sm">
            <span class="text-sm font-bold text-[#303326]">👤 {{ username }}</span>
            <el-button class="!rounded-full !border-0 !bg-[#82846D]/15 !px-3 !py-1 !h-7 !text-xs !font-bold !text-[#82846D] hover:!bg-[#82846D] hover:!text-white transition-colors" @click="handleLogout">
              退出
            </el-button>
          </div>
          <el-button v-else class="!rounded-full !border-0 !bg-[#82846D] !px-6 !font-bold !text-white hover:!bg-[#6f715c]" @click="goDetection">
            开始检测
          </el-button>
        </div>
      </nav>
    </header>

    <main>
      <RouterView />
    </main>

    <footer v-if="!isAuthPage" class="border-t border-white/70 bg-white/50">
      <div class="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-8 text-sm text-olive md:flex-row md:items-center md:justify-between lg:px-8">
        <p>© 2026 智慧路口视频监控系统</p>
        <div class="flex gap-5">
          <RouterLink to="/detection" class="hover:text-[#303326]">检测中心</RouterLink>
          <RouterLink to="/analysis" class="hover:text-[#303326]">数据分析</RouterLink>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted } from 'vue'
import { RouterLink, RouterView, useRouter, useRoute } from 'vue-router'
import { Monitor } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()

const isAuthPage = computed(() => route.path === '/login' || route.path === '/register')
const username = ref('')

const updateUsername = () => {
  username.value = localStorage.getItem('vision_username') || ''
}

watch(() => route.path, () => {
  updateUsername()
})

onMounted(() => {
  updateUsername()
})

const handleLogout = () => {
  localStorage.removeItem('vision_token')
  localStorage.removeItem('vision_username')
  username.value = ''
  router.push('/login')
}

const navItems = [
  { label: 'Home', path: '/' },
  { label: '检测中心', path: '/detection' },
  { label: '数据分析', path: '/analysis' }
]

const goDetection = () => {
  router.push('/detection')
}
</script>
