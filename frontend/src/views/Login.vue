<template>
  <div class="login-container min-h-screen flex items-center justify-center bg-gradient-to-tr from-[#DDFCAD]/30 via-[#E8EEDB]/40 to-[#C8E087]/20 px-4">
    <div class="w-full max-w-md rounded-[2.5rem] border border-white/80 bg-white/70 p-8 shadow-soft backdrop-blur-xl">
      <div class="text-center mb-8">
        <el-tag class="!rounded-full !border-0 !bg-[#C8E087] !font-bold !text-[#303326] !px-4 !py-1 mb-3">Vision Project</el-tag>
        <h1 class="text-3xl font-black tracking-tight text-[#303326]">欢迎回来</h1>
        <p class="mt-2 text-sm text-[#82846D] font-medium">智慧交通视频监控系统</p>
      </div>

      <el-form :model="loginForm" :rules="rules" ref="loginFormRef" label-position="top" @keyup.enter="handleLogin">
        <el-form-item label="用户名" prop="username">
          <el-input 
            v-model="loginForm.username" 
            placeholder="请输入用户名" 
            class="custom-input"
            clearable
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input 
            v-model="loginForm.password" 
            type="password" 
            placeholder="请输入密码" 
            class="custom-input"
            show-password
            clearable
          />
        </el-form-item>

        <div class="mt-8">
          <el-button 
            type="primary" 
            class="w-full !h-12 !rounded-full !border-0 !bg-[#303326] hover:!bg-[#82846D] !font-black !text-white !text-base tracking-widest transition-all shadow-md hover:scale-[1.02] active:scale-[0.98]"
            :loading="loading"
            @click="handleLogin"
          >
            立即登录
          </el-button>
        </div>
      </el-form>

      <div class="text-center mt-6">
        <span class="text-sm text-[#82846D]">还没有账号？</span>
        <router-link to="/register" class="text-sm font-bold text-[#95A472] hover:text-[#303326] ml-1 transition-colors">
          立即注册
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const loginFormRef = ref(null)
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度需在 3 到 20 个字符之间', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度需在 6 到 20 个字符之间', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        const { data } = await axios.post('/api/login', {
          username: loginForm.username,
          password: loginForm.password
        })
        if (data.success) {
          ElMessage.success({
            message: '登录成功，欢迎回来！',
            type: 'success',
            duration: 2000
          })
          localStorage.setItem('vision_token', data.token)
          localStorage.setItem('vision_username', data.username)
          router.push('/')
        } else {
          ElMessage.error(data.message || '登录失败，请检查用户名和密码')
        }
      } catch (error) {
        console.error('Login error:', error)
        const errorMsg = error.response?.data?.message || '网络连接失败，请稍后重试'
        ElMessage.error(errorMsg)
      } finally {
        loading.value = false
      }
    } else {
      ElMessage.warning('请正确填写用户名和密码')
    }
  })
}
</script>

<style scoped>
.custom-input :deep(.el-input__wrapper) {
  border-radius: 1rem;
  padding: 8px 16px;
  background-color: rgba(255, 255, 255, 0.5);
  box-shadow: 0 0 0 1px rgba(130, 132, 109, 0.15) inset;
  transition: all 0.3s;
}

.custom-input :deep(.el-input__wrapper.is-focus) {
  background-color: #fff;
  box-shadow: 0 0 0 1px #95A472 inset, 0 4px 12px rgba(149, 164, 114, 0.15) !important;
}

:deep(.el-form-item__label) {
  font-weight: 700;
  color: #303326;
  margin-bottom: 6px;
  padding-left: 4px;
}
</style>
