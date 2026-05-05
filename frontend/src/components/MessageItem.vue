<script setup>
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'

const props = defineProps({
  message: {
    type: Object,
    required: true
  }
})

const md = new MarkdownIt()

const renderedContent = computed(() => {
  if (props.message.role === 'assistant') {
    return md.render(props.message.content)
  }
  return props.message.content
})
</script>

<template>
  <div class="message-item" :class="message.role">
    <div class="avatar">
      {{ message.role === 'user' ? '👤' : '' }}
    </div>
    <div class="content">
      <!-- 使用 v-html 渲染解析后的 Markdown -->
      <div v-if="message.role === 'assistant'" v-html="renderedContent"></div>
      <div v-else>{{ message.content }}</div>
    </div>
  </div>
</template>

<style scoped>
.message-item {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  padding: 10px;
}

.message-item.user {
  flex-direction: row-reverse;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background-color: #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.content {
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
  font-size: 15px;
}

.message-item.user .content {
  background-color: #409eff;
  color: white;
  border-top-right-radius: 2px;
}

.message-item.assistant .content {
  background-color: #f5f7fa;
  color: #303133;
  border-top-left-radius: 2px;
}

/* 添加一些 Markdown 渲染后的基础样式 */
:deep(h3) { margin: 16px 0 8px; font-size: 1.2em; }
:deep(h4) { margin: 12px 0 6px; font-size: 1.1em; }
:deep(p) { margin: 8px 0; }
:deep(ul) { padding-left: 20px; }
:deep(strong) { font-weight: bold; }
</style>
