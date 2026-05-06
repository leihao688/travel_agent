
<template>
  <div class="attraction-images" v-if="attractionName">
    <div class="images-header" @click="toggleExpand">
      <span class="title">📸 {{ attractionName }} 实景</span>
      <el-icon class="arrow" :class="{ expanded: isExpanded }">
        <ArrowDown />
      </el-icon>
    </div>
    
    <div v-show="isExpanded" class="images-container">
      <div v-if="loading" class="loading">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>正在加载图片...</span>
      </div>
      
      <div v-else-if="error" class="error">
        <span>图片加载失败</span>
      </div>
      
      <div v-else-if="images.length > 0" class="image-grid">
        <div
          v-for="(img, index) in images"
          :key="index"
          class="image-item"
          @click="previewImage(img.url)"
        >
          <img :src="img.url" :alt="img.alt" loading="lazy" />
          <div class="image-overlay">
            <span class="author">📷 {{ img.author }}</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 图片预览对话框 -->
    <el-image-viewer
      v-if="showPreview"
      :url-list="images.map(img => img.url)"
      :initial-index="previewIndex"
      @close="showPreview = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ArrowDown, Loading } from '@element-plus/icons-vue'
import { searchImages } from '@/api/travel'
import { ElMessage } from 'element-plus'

const props = defineProps({
  attractionName: {
    type: String,
    required: true
  }
})

const isExpanded = ref(false)
const loading = ref(false)
const error = ref(false)
const images = ref([])
const showPreview = ref(false)
const previewIndex = ref(0)

const toggleExpand = async () => {
  isExpanded.value = !isExpanded.value
  
  // 首次展开时加载图片
  if (isExpanded.value && images.value.length === 0 && !loading.value) {
    await loadImages()
  }
}


const loadImages = async () => {
  loading.value = true
  error.value = false

  try {
    const response = await searchImages({
      query: props.attractionName,
      count: 2
    })

    // 🔥 修改：尝试多层提取，确保拿到数组
    // 情况 1: 后端返回 { code: 200, data: [...] } -> response.data.data
    // 情况 2: 后端返回 { code: 200, data: { code: 200, data: [...] } } -> response.data
    let dataArray = null
    if (Array.isArray(response?.data?.data)) {
      dataArray = response.data.data
    } else if (Array.isArray(response?.data)) {
      dataArray = response.data
    }

    if (Array.isArray(dataArray)) {
      images.value = dataArray.map(item => ({
        url: item.url,
        alt: item.alt || props.attractionName,
        author: item.author || 'Unsplash'
      })).filter(img => img.url)

      if (images.value.length === 0) error.value = true
    } else {
      console.error('提取失败，dataArray 不是数组:', response)
      error.value = true
    }
  } catch (err) {
    console.error('图片加载异常:', err)
    error.value = true
  } finally {
    loading.value = false
  }
}



const previewImage = (url) => {
  previewIndex.value = images.value.findIndex(img => img.url === url)
  showPreview.value = true
}
</script>

<style scoped>
.attraction-images {
  margin: 12px 0;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
  background: #fafafa;
}

.images-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  cursor: pointer;
  background: #f5f7fa;
  transition: background 0.2s;
}

.images-header:hover {
  background: #e8edf3;
}

.title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.arrow {
  transition: transform 0.3s;
  color: #909399;
}

.arrow.expanded {
  transform: rotate(180deg);
}

.images-container {
  padding: 12px;
}

.loading, .error {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #909399;
  font-size: 13px;
  padding: 20px 0;
  justify-content: center;
}

.error {
  color: #f56c6c;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.image-item {
  position: relative;
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  aspect-ratio: 16/10;
  transition: transform 0.2s;
}

.image-item:hover {
  transform: scale(1.02);
}

.image-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(transparent, rgba(0,0,0,0.6));
  padding: 8px 12px;
  color: white;
  font-size: 12px;
  opacity: 0;
  transition: opacity 0.2s;
}

.image-item:hover .image-overlay {
  opacity: 1;
}

.author {
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
