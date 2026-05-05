<template>
  <div class="chat-window">
    <div class="messages-container" ref="messagesRef">
      <MessageItem
        v-for="(msg, index) in messages"
        :key="index"
        :message="msg"
      />
      <div v-if="isLoading" class="loading-indicator">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>AI 正在思考...</span>
      </div>
    </div>

     <div class="input-area">
      <div class="input-wrapper">
        <el-popover
          trigger="click"
          placement="top-start"
          :width="200"
          popper-class="upload-popover"
        >
          <template #reference>
            <el-icon class="add-icon"><Plus /></el-icon>
          </template>
          <div class="upload-menu">
            <div class="menu-item" @click="handleFileUpload">
              <el-icon><Paperclip /></el-icon>
              <span>添加照片和文件</span>
              <span class="shortcut">Ctrl + U</span>
            </div>
            <div class="menu-item" @click="createImage">
              <el-icon><Picture /></el-icon>
              <span>创建图片</span>
            </div>
            <div class="menu-item" @click="thinkMode">
              <el-icon><Lightning /></el-icon>
              <span>思考一下</span>
            </div>
            <div class="menu-item" @click="deepResearch">
              <el-icon><Search /></el-icon>
              <span>深度研究</span>
            </div>
            <div class="menu-item" @click="webSearch">
              <el-icon><Monitor /></el-icon>
              <span>网页搜索</span>
            </div>
            <div class="menu-item more">
              <span>更多</span>
              <el-icon><ArrowRight /></el-icon>
            </div>
          </div>
        </el-popover>

        <el-input
          v-model="inputValue"
          type="textarea"
          :rows="1"
          placeholder="有问题，尽管问"
          @keydown.ctrl.enter="sendMessage"
          resize="none"
          class="modern-input"
        />
        <div class="action-icons">
          <el-button
            type="primary"
            :loading="isLoading"
            @click="sendMessage"
            class="send-btn-modern"
            circle
          >
            <el-icon><Promotion /></el-icon>
          </el-button>
        </div>

        <input
          type="file"
          ref="fileInput"
          @change="onFileSelected"
          style="display: none"
          multiple
          accept="image/*,.pdf,.doc,.docx,.txt"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch, onMounted, onUnmounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import { sendChatMessage } from '@/api/travel'
import MessageItem from './MessageItem.vue'
import { ElMessage } from 'element-plus'
import {
  Loading,
  Plus,
  Promotion,
  Paperclip,
  Picture,
  Lightning,
  Search,
  Monitor,
  ArrowRight
} from '@element-plus/icons-vue'

const chatStore = useChatStore()
const messages = ref(chatStore.messages)
const inputValue = ref('')
const isLoading = ref(false)
const messagesRef = ref(null)
const fileInput = ref(null)

const handleFileUpload = () => {
  fileInput.value?.click()
}

const onFileSelected = (event) => {
  const files = Array.from(event.target.files)
  if (files.length > 0) {
    ElMessage.success(`已选择 ${files.length} 个文件`)
    console.log('上传的文件:', files)
  }
}

const createImage = () => ElMessage.info('创建图片功能开发中')
const thinkMode = () => ElMessage.info('思考模式已开启')
const deepResearch = () => ElMessage.info('深度研究功能开发中')
const webSearch = () => ElMessage.info('网页搜索功能开发中')

const handleKeyDown = (event) => {
  if (event.ctrlKey && event.key === 'u') {
    event.preventDefault()
    handleFileUpload()
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)
})

const sendMessage = async () => {
  if (!inputValue.value.trim() || isLoading.value) return

  const userMessage = inputValue.value.trim()
  chatStore.addMessage('user', userMessage)
  inputValue.value = ''
  isLoading.value = true

  try {
    scrollToBottom()
    const response = await sendChatMessage({
      query: userMessage,
      session_id: chatStore.sessionId,
      user_id: 'default_user'
    })

    const content = response?.data?.data?.content || response?.content || "AI 返回了空内容"
    chatStore.addMessage('assistant', content)
  } catch (error) {
    ElMessage.error('发送消息失败，请检查后端服务是否启动')
    console.error(error)
  } finally {
    isLoading.value = false
    scrollToBottom()
  }
}

const scrollToBottom = async () => {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

watch(messages, () => {
  scrollToBottom()
}, { deep: true })
</script>

<style scoped>
.chat-window {
  height: 100%;
  display: flex;
  flex-direction: column;
  max-width: 1000px;
  margin: 0 auto;
  width: 100%;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.loading-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #909399;
  font-size: 14px;
  margin-top: 10px;
}

.input-area {
  padding: 20px;
  background-color: transparent;
  display: flex;
  justify-content: center;
}

.input-wrapper {
  max-width: 800px;
  width: 100%;
  background-color: white;
  border-radius: 24px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  border: 1px solid #e4e7ed;
}

.add-icon {
  font-size: 36px;
  color: #909399;
  cursor: pointer;
  flex-shrink: 0;
  padding: 8px;
  border-radius: 50%;
  transition: all 0.2s;
}

.add-icon:hover {
  background-color: #f5f7fa;
  color: #409eff;
}

.modern-input {
  flex: 1;
  border: none;
  box-shadow: none;
}

.modern-input :deep(.el-textarea__inner) {
  border: none;
  box-shadow: none;
  padding: 4px 0;
  font-size: 15px;
  resize: none;
  line-height: 1.5;
}

.modern-input :deep(.el-textarea__inner):focus {
  box-shadow: none;
}

.action-icons {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.send-btn-modern {
  width: 40px;
  height: 40px;
  padding: 0;
  border-radius: 50%;
}

.send-btn-modern :deep(.el-icon) {
  font-size: 18px;
}

/* 补全缺失的下拉菜单样式 */
.upload-menu {
  padding: 8px 0;
  background: #fff;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  cursor: pointer;
  transition: background-color 0.2s;
  font-size: 14px;
  color: #303133;
}

.menu-item:hover {
  background-color: #f5f7fa;
}

.menu-item .el-icon {
  font-size: 18px;
  color: #606266;
}

.menu-item .shortcut {
  margin-left: auto;
  font-size: 12px;
  color: #909399;
}

.menu-item.more {
  border-top: 1px solid #e4e7ed;
  margin-top: 8px;
  padding-top: 12px;
  justify-content: space-between;
}
</style>
