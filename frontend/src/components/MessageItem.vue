<script setup>
import {computed, ref, watch} from 'vue'
import MarkdownIt from 'markdown-it'
import AttractionImage from './AttractionImage.vue' // 引入刚才创建的图片组件

const props = defineProps({
  message: {
    type: Object,
    required: true
  }
})

const md = new MarkdownIt()

// 1. 修复报错：定义 template 中使用的变量
const role = computed(() => props.message.role)
const content = computed(() => props.message.content)

// 2. 用于存储提取出的景点名称
const attractionNames = ref([])

// 3. 渲染 Markdown 内容
const renderedContent = computed(() => {
  if (props.message.role === 'assistant') {
    return md.render(props.message.content)
  }
  return props.message.content
})

// 4. 自动提取景点名称的逻辑 (监听 content 变化)
watch(content, (newContent) => {
  if (!newContent || props.message.role !== 'assistant') {
    attractionNames.value = []
    return
  }

  const names = new Set()


  const tagRegex = /<!--IMAGE_TAGS:\s*(\[.*?\])\s*-->/
  const match = newContent.match(tagRegex)

 if (match) {
    try {
      // match[1] 是字符串形式的数组，如 '["上海迪士尼", "外滩"]'
      const parsedArray = JSON.parse(match[1])

      // 🔥 关键修改：遍历数组，提取每个景点名
      if (Array.isArray(parsedArray)) {
        parsedArray.forEach(item => {
          if (typeof item === 'string' && item.trim()) {
            names.add(item.trim())
          }
        })
      }

      console.log('✅ 提取到的景点名称:', Array.from(names))
    } catch (e) {
      console.error('❌ 解析景点标签失败:', e, '原始内容:', match[1])
    }
  }

  attractionNames.value = Array.from(names).slice(0, 5)
}, { immediate: true })


</script>

<template>
  <div class="message-item" :class="message.role">
    <div class="avatar">
      {{ message.role === 'user' ? '👤' : '🤖' }}
    </div>
    <div class="content">
      <!-- 渲染 Markdown 文本 -->
      <div v-if="message.role === 'assistant'" v-html="renderedContent"></div>
      <div v-else class="user-text">{{ message.content }}</div>

      <!-- 🔥 新增：在助手回复下方自动展示景点图片 -->
      <div v-if="message.role === 'assistant' && attractionNames.length > 0" class="attractions-section">
        <div class="section-title"> 相关景点实景图</div>
        <div class="image-list">
          <AttractionImage
              v-for="(name, index) in attractionNames"
              :key="index"
              :attraction-name="name"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.message-item {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
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
  flex-shrink: 0;
}

.content {
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
  font-size: 15px;
  word-wrap: break-word;
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

/* Markdown 渲染样式 */
:deep(h3) {
  margin: 16px 0 8px;
  font-size: 1.2em;
}

:deep(h4) {
  margin: 12px 0 6px;
  font-size: 1.1em;
}

:deep(p) {
  margin: 8px 0;
}

:deep(ul) {
  padding-left: 20px;
}

:deep(strong) {
  font-weight: bold;
}

/* 🔥 新增：景点图片区域样式 */
.attractions-section {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px dashed #dcdfe6;
}

.section-title {
  font-size: 14px;
  font-weight: bold;
  color: #606266;
  margin-bottom: 12px;
}

.image-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
</style>
