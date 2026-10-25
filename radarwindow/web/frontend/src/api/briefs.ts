import { api } from './client'

export const listBriefs  = () => api.get('/briefs').then(r => r.data)
export const getBrief    = (id: string) => api.get(`/briefs/${id}`).then(r => r.data)
export const patchBrief  = (id: string, data: { content_md?: string; status?: string; is_public?: boolean }) =>
  api.patch(`/briefs/${id}`, data).then(r => r.data)
export const approveBrief = (id: string) =>
  api.post(`/briefs/${id}/approve`).then(r => r.data)
export const patchPost   = (postId: string, data: { content: string }) =>
  api.patch(`/briefs/posts/${postId}`, data).then(r => r.data)

export async function downloadMediaKit(id: string) {
  const res = await api.get(`/briefs/${id}/download`, { responseType: 'blob' })
  const disposition = res.headers['content-disposition'] || ''
  const match = disposition.match(/filename="?([^"]+)"?/)
  const filename = match ? match[1] : `radarwindow-brief-${id}.zip`
  const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/zip' }))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.URL.revokeObjectURL(url)
}
