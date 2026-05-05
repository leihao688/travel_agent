<template>
  <div :class="['message-item', message.role]">
    <el-avatar
      :icon="message.role === 'user' ? User : ChatDotRound"
      :size="40"
      class="avatar"
    />
    <div class="message-content">
      <div class="message-text">{{ message.content }}</div>
      <div class="message-time">{{ formatTime(message.timestamp) }}</div>
    </div>
  </div>
</template>

<script setup>
import { User, ChatDotRound } from '@element-plus/icons-vue'

defineProps({
  message: {
    type: Object,
    required: true
  }
})

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.message-item {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  animation: fadeIn 0.3s ease;
}

.message-item.user {
  flex-direction: row-reverse;
}

.message-content {
  max-width: 75%;
  background: #f5f7fa;
  padding: 12px 16px;
  border-radius: 12px;
  position: relative;
}

.message-item.user .message-content {
  background: #ecf5ff;
  color: #409eff;
}

.message-text {
  line-height: 1.6;
  word-wrap: break-word;
  white-space: pre-wrap;
}

.message-time {
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
  text-align: right;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
