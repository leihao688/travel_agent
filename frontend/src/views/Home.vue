<template>
  <div class="home-container">
    <!-- 左侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="logo">🌍 小旅</div>
        <el-button @click="createNewChat" type="primary" size="small" class="new-chat-btn">
          <el-icon><Plus /></el-icon> 新对话
        </el-button>
      </div>

      <div class="chat-history">
        <div class="history-section">
          <div class="section-title">最近对话</div>
          <div
            v-for="(chat, index) in chatHistory"
            :key="index"
            class="chat-item"
            :class="{ active: currentChatId === chat.id }"
            @click="switchChat(chat.id)"
          >
            <el-icon><ChatDotRound /></el-icon>
            <span class="chat-title">{{ chat.title }}</span>
            <el-icon class="delete-icon" @click.stop="deleteChat(chat.id)"><Delete /></el-icon>
          </div>
        </div>
      </div>

      <div class="sidebar-footer">
        <div class="user-info">
          <el-avatar :size="32" class="user-avatar">👤</el-avatar>
          <span class="user-name">用户</span>
        </div>
      </div>
    </aside>

    <!-- 右侧主聊天区域 -->
    <main class="main-content">
      <ChatWindow />
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Plus, ChatDotRound, Delete } from '@element-plus/icons-vue'
import ChatWindow from '@/components/ChatWindow.vue'
import { useChatStore } from '@/stores/chat'
import { ElMessageBox, ElMessage } from 'element-plus'

const chatStore = useChatStore()

// 模拟历史对话数据（后续可接入后端）
const chatHistory = ref([
  { id: 1, title: '三亚三日游规划', timestamp: '2026-05-05' },
  { id: 2, title: '北京天气查询', timestamp: '2026-05-04' },
  { id: 3, title: '上海酒店推荐', timestamp: '2026-05-03' }
])

const currentChatId = ref(1)

const createNewChat = () => {
  const newId = chatHistory.value.length + 1
  chatHistory.value.unshift({
    id: newId,
    title: `新对话 ${newId}`,
    timestamp: new Date().toISOString().split('T')[0]
  })
  currentChatId.value = newId
  chatStore.clearMessages()
  ElMessage.success('已创建新对话')
}

const switchChat = (id) => {
  currentChatId.value = id
  // TODO: 加载对应对话的历史消息
  ElMessage.info(`切换到对话 ${id}`)
}

const deleteChat = (id) => {
  ElMessageBox.confirm('确定要删除这个对话吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    chatHistory.value = chatHistory.value.filter(chat => chat.id !== id)
    ElMessage.success('已删除对话')
  }).catch(() => {})
}
</script>

<style scoped>
.home-container {
  height: 100vh;
  display: flex;
  background-color: #f9fafb;
}

/* 左侧边栏 */
.sidebar {
  width: 260px;
  background-color: #202123;
  color: white;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #2d2f31;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #2d2f31;
}

.logo {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 12px;
}

.new-chat-btn {
  width: 100%;
}

.chat-history {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.history-section {
  margin-top: 8px;
}

.section-title {
  font-size: 12px;
  color: #8e8ea0;
  padding: 8px;
  text-transform: uppercase;
}

.chat-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s;
  margin-bottom: 4px;
}

.chat-item:hover {
  background-color: #2a2b32;
}

.chat-item.active {
  background-color: #343541;
}

.chat-title {
  flex: 1;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.delete-icon {
  opacity: 0;
  transition: opacity 0.2s;
  color: #8e8ea0;
}

.chat-item:hover .delete-icon {
  opacity: 1;
}

.delete-icon:hover {
  color: #ef4444;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid #2d2f31;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-avatar {
  background-color: #343541;
}

.user-name {
  font-size: 14px;
}

/* 右侧主内容 */
.main-content {
 flex: 1;
  overflow: hidden;
  position: relative;
}
.main-content::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: url('https://images.unsplash.com/photo-1506929562872-bb421503ef21?w=1920&q=80');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  opacity: 0.3;
  z-index: 0;
}

.main-content > * {
  position: relative;
  z-index: 1;
}
</style>
