<template>
  <div class="register-container min-h-screen flex items-center justify-center bg-gradient-to-tr from-[#DDFCAD]/30 via-[#E8EEDB]/40 to-[#C8E087]/20 px-4">
    <div class="w-full max-w-md rounded-[2.5rem] border border-white/80 bg-white/70 p-8 shadow-soft backdrop-blur-xl">
      <div class="text-center mb-8">
        <el-tag class="!rounded-full !border-0 !bg-[#C8E087] !font-bold !text-[#303326] !px-4 !py-1 mb-3">Vision Project</el-tag>
        <h1 class="text-3xl font-black tracking-tight text-[#303326]">加入我们</h1>
        <p class="mt-2 text-sm text-[#82846D] font-medium">创建您的智慧交通监控账号</p>
      </div>

      <el-form :model="registerForm" :rules="rules" ref="registerFormRef" label-position="top" @keyup.enter="handleRegister">
        <el-form-item label="用户名" prop="username">
          <el-input 
            v-model="registerForm.username" 
            placeholder="请设置用户名 (3-20个字符)" 
            class="custom-input"
            clearable
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input 
            v-model="registerForm.password" 
            type="password" 
            placeholder="请设置密码 (6-20个字符)" 
            class="custom-input"
            show-password
            clearable
          />
        </el-form-item>

        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input 
            v-model="registerForm.confirmPassword" 
            type="password" 
            placeholder="请再次确认密码" 
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
            @click="handleRegister"
          >
            立即注册
          </el-button>
        </div>
      </el-form>

      <div class="text-center mt-6">
        <span class="text-sm text-[#82846D]">已有账号？</span>
        <router-link to="/login" class="text-sm font-bold text-[#95A472] hover:text-[#303326] ml-1 transition-colors">
          直接登录
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
const registerFormRef = ref(null)
const loading = ref(false)

const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: ''
})

const validateConfirmPass = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('请再次输入密码'))
  } else if (value !== registerForm.password) {
    callback(new Error('两次输入密码不一致!'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请设置用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度需在 3 到 20 个字符之间', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请设置密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度需在 6 到 20 个字符之间', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPass, trigger: 'blur' }
  ]
}

const handleRegister = async () => {
  if (!registerFormRef.value) return
  
  await registerFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        const { data } = await axios.post('/api/register', {
          username: registerForm.username,
          password: registerForm.password
        })
        if (data.success) {
          ElMessage.success({
            message: '注册成功！正在跳转至登录页...',
            type: 'success',
            duration: 2000
          })
          setTimeout(() => {
            router.push('/login')
          }, 1500)
        } else {
          ElMessage.error(data.message || '注册失败，请稍后重试')
        }
      } catch (error) {
        console.error('Register error:', error)
        const errorMsg = error.response?.data?.message || '网络连接失败，请稍后重试'
        ElMessage.error(errorMsg)
      } finally {
        loading.value = false
      }
    } else {
      ElMessage.warning('请按照规范正确填写注册信息')
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
