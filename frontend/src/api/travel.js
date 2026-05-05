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
