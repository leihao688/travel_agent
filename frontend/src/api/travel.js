import axios from 'axios'

const request = axios.create({
  baseURL: '/api',
  timeout: 60000
})

export function sendChatMessage(data) {
  return request({
    url: '/chat',
    method: 'post',
    data
  })
}
// 🔥 新增：流式请求方法
export async function streamChatMessage(data, onChunk) {
  // ... 前面的 fetch 逻辑不变 ...
  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop();

    for (const line of lines) {
      if (line.trim()) {
        try {
          // 尝试解析 JSON
          const parsed = JSON.parse(line);
          const content = parsed.data || parsed.content || parsed.output || '';
          if (content) onChunk(content);
        } catch (e) {
          // 如果不是 JSON，直接作为纯文本传递
          onChunk(line);
        }
      }
    }
  }
  // 处理最后一段
  if (buffer.trim()) {
      try {
          const parsed = JSON.parse(buffer);
          const content = parsed.data || parsed.content || parsed.output || '';
          if (content) onChunk(content);
      } catch (e) {
          onChunk(buffer);
      }
  }
}
