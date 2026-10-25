import axios from 'axios'

export const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use(config => {
  const token = localStorage.getItem('rw_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  r => r,
  async err => {
    if (err.response?.status === 401) {
      const refresh = localStorage.getItem('rw_refresh_token')
      if (refresh) {
        try {
          const res = await axios.post('/api/auth/refresh', { refresh_token: refresh })
          const { access_token, refresh_token } = res.data
          localStorage.setItem('rw_token', access_token)
          localStorage.setItem('rw_refresh_token', refresh_token)
          err.config.headers.Authorization = `Bearer ${access_token}`
          return api.request(err.config)
        } catch {
          ;['rw_token', 'rw_refresh_token', 'rw_user_id', 'rw_email'].forEach(k => localStorage.removeItem(k))
          window.location.href = '/login'
          return
        }
      } else {
        ;['rw_token', 'rw_refresh_token', 'rw_user_id', 'rw_email'].forEach(k => localStorage.removeItem(k))
        window.location.href = '/login'
        return
      }
    }
    return Promise.reject(err)
  }
)
