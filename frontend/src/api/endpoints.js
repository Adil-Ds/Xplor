import api from './client'

// ── Auth ──────────────────────────────────────────────────
export const authAPI = {
  login:    (data) => api.post('/auth/login', data),
  register: (data) => api.post('/auth/register', data),
  me:       ()     => api.get('/auth/me'),
}

// ── Datasets ──────────────────────────────────────────────
export const datasetAPI = {
  list:    ()          => api.get('/datasets'),
  get:     (id)        => api.get(`/datasets/${id}`),
  upload:  (formData)  => api.post('/datasets/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  delete:  (id)        => api.delete(`/datasets/${id}`),
  preview: (id, rows)  => api.get(`/datasets/${id}/preview?rows=${rows ?? 100}`),
  profile: (id)        => api.get(`/datasets/${id}/profile`),
}

// ── Cleaning ──────────────────────────────────────────────
export const cleanAPI = {
  applyStep:   (id, step)   => api.post(`/clean/${id}/step`, step),
  getRecipe:   (id)         => api.get(`/clean/${id}/recipe`),
  removeStep:  (id, stepIdx) => api.delete(`/clean/${id}/recipe/${stepIdx}`),
  preview:     (id)         => api.get(`/clean/${id}/preview`),
  applyAll:    (id)         => api.post(`/clean/${id}/apply`),
  getSaved:    (id)         => api.get(`/clean/${id}/saved`),
}

// ── Explore / Analysis ───────────────────────────────────
export const exploreAPI = {
  stats:       (id)         => api.get(`/explore/${id}/stats`),
  correlation: (id)         => api.get(`/explore/${id}/correlation`),
  distribution:(id, col)    => api.get(`/explore/${id}/distribution?column=${col}`),
  outliers:    (id, col)    => api.get(`/explore/${id}/outliers?column=${col}`),
  suggestions: (id)         => api.get(`/explore/${id}/suggestions`),
  query:       (id, q)      => api.post(`/explore/${id}/query`, q),
}

// ── Dashboards ───────────────────────────────────────────
export const dashboardAPI = {
  list:   ()         => api.get('/dashboards'),
  get:    (id)       => api.get(`/dashboards/${id}`),
  create: (data)     => api.post('/dashboards', data),
  update: (id, data) => api.put(`/dashboards/${id}`, data),
  delete: (id)       => api.delete(`/dashboards/${id}`),
}

// ── Reports ──────────────────────────────────────────────
export const reportAPI = {
  list:   ()          => api.get('/reports'),
  create: (data)      => api.post('/reports', data),
  delete: (id)        => api.delete(`/reports/${id}`),
  share:  (id)        => api.post(`/reports/${id}/share`),
}
