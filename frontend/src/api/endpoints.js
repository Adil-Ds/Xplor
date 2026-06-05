import api from './client'

// ── Auth ──────────────────────────────────────────────────
export const authAPI = {
  login:      (data)        => api.post('/auth/login', data),
  register:   (data)        => api.post('/auth/register', data),
  me:         ()            => api.get('/auth/me'),
  // Admin only
  users:      ()            => api.get('/auth/users'),
  updateRole: (id, role)    => api.put(`/auth/users/${id}/role`, { role }),
  deleteUser: (id)          => api.delete(`/auth/users/${id}`),
}

// ── Datasets ──────────────────────────────────────────────
export const datasetAPI = {
  list:     ()          => api.get('/datasets'),
  get:      (id)        => api.get(`/datasets/${id}`),
  upload:   (formData)  => api.post('/datasets/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  delete:   (id)        => api.delete(`/datasets/${id}`),
  preview:  (id, rows)  => api.get(`/datasets/${id}/preview?rows=${rows ?? 100}`),
  profile:  (id)        => api.get(`/datasets/${id}/profile`),
  analysis: (id)        => api.get(`/datasets/${id}/analysis`),
}

// ── Cleaning ──────────────────────────────────────────────
export const cleanAPI = {
  applyStep:   (id, step)    => api.post(`/clean/${id}/step`, step),
  getRecipe:   (id)          => api.get(`/clean/${id}/recipe`),
  removeStep:  (id, stepIdx) => api.delete(`/clean/${id}/recipe/${stepIdx}`),
  preview:     (id)          => api.get(`/clean/${id}/preview`),
  applyAll:    (id)          => api.post(`/clean/${id}/apply`),
  getSaved:    (id)          => api.get(`/clean/${id}/saved`),
}

// ── Explore / Analysis ────────────────────────────────────
export const exploreAPI = {
  stats:        (id)       => api.get(`/explore/${id}/stats`),
  correlation:  (id)       => api.get(`/explore/${id}/correlation`),
  distribution: (id, col)  => api.get(`/explore/${id}/distribution?column=${col}`),
  outliers:     (id, col)  => api.get(`/explore/${id}/outliers?column=${col}`),
  suggestions:  (id)       => api.get(`/explore/${id}/suggestions`),
  anomalies:    (id)       => api.get(`/explore/${id}/anomalies`),
  query:        (id, q)    => api.post(`/explore/${id}/query`, q),
  narrative:    (id)       => api.get(`/explore/${id}/narrative`),
}

// ── Chat / AI NL Queries ──────────────────────────────────
export const chatAPI = {
  status: ()                    => api.get('/chat/status'),
  models: ()                    => api.get('/chat/models'),
  ask:    (id, question, model) => api.post(`/chat/${id}`, {
    question,
    ...(model ? { model } : {}),
  }),
}

// ── Dashboards ────────────────────────────────────────────
export const dashboardAPI = {
  list:          ()           => api.get('/dashboards'),
  get:           (id)         => api.get(`/dashboards/${id}`),
  create:        (data)       => api.post('/dashboards', data),
  update:        (id, data)   => api.put(`/dashboards/${id}`, data),
  delete:        (id)         => api.delete(`/dashboards/${id}`),
  suggest:       (id)         => api.get(`/dashboards/suggest/${id}`),
  suggestSchema:  (body)       => api.post('/dashboards/suggest-schema', body, { timeout: 200_000 }),
  widgetInsight:  (body)       => api.post('/dashboards/widget-insight',  body, { timeout: 60_000 }),
}

// ── Reports ───────────────────────────────────────────────
export const reportAPI = {
  list:   ()     => api.get('/reports'),
  create: (data) => api.post('/reports', data),
  delete: (id)   => api.delete(`/reports/${id}`),
  share:  (id)   => api.post(`/reports/${id}/share`),
}

// ── AI Models Health ──────────────────────────────────────
export const modelsAPI = {
  status: () => api.get('/models/status'),
  health: () => api.get('/health'),
}
