import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useChatStore = defineStore('chat', () => {
  const messages = ref([])
  const sessionId = ref('default')
  const isLoading = ref(false)

  function addMessage(role, content) {
    messages.value.push({
      role,
      content,
      timestamp: new Date().toISOString()
    })
  }

  function clearMessages() {
    messages.value = []
  }

  return {
    messages,
    sessionId,
    isLoading,
    addMessage,
    clearMessages
  }
})
