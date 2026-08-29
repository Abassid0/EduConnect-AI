import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "/api/v1";

const client = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = localStorage.getItem("refresh_token");
      if (refresh) {
        try {
          const { data } = await axios.post(`${API_BASE}/auth/refresh`, {
            refresh_token: refresh,
          });
          localStorage.setItem("access_token", data.access_token);
          localStorage.setItem("refresh_token", data.refresh_token);
          original.headers.Authorization = `Bearer ${data.access_token}`;
          return client(original);
        } catch {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          window.location.href = "/login";
        }
      } else {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default client;

export const auth = {
  login: (email, password) =>
    client.post("/auth/login", { email, password }),
  me: () => client.get("/admin/me"),
};

export const admin = {
  inbox: (params) => client.get("/admin/inbox", { params }),
  customer: (whatsapp) => client.get(`/admin/customer/${whatsapp}`),
  messages: (convId, limit = 100) =>
    client.get(`/admin/conversations/${convId}/messages`, {
      params: { limit },
    }),
  reply: (data) => client.post("/admin/reply", data),
  pause: (convId) => client.post(`/admin/conversations/${convId}/pause`),
  resume: (convId) => client.post(`/admin/conversations/${convId}/resume`),
  assign: (convId, agentId) =>
    client.post(`/admin/conversations/${convId}/assign`, {
      agent_id: agentId,
    }),
  close: (convId) => client.post(`/admin/conversations/${convId}/close`),
  agents: () => client.get("/admin/agents"),
};

export const tickets = {
  list: (params) => client.get("/admin/tickets", { params }),
  get: (id) => client.get(`/admin/tickets/${id}`),
  assign: (id, agentId) =>
    client.post(`/admin/tickets/${id}/assign`, { agent_id: agentId }),
  close: (id) => client.post(`/admin/tickets/${id}/close`),
  notes: (id) => client.get(`/admin/tickets/${id}/notes`),
  addNote: (id, content, conversationId) =>
    client.post(`/admin/tickets/${id}/notes`, {
      content,
      conversation_id: conversationId || null,
    }),
  stats: () => client.get("/admin/tickets/stats/counts"),
};

export const billing = {
  feeTypes: (params) => client.get("/billing/fee-types", { params }),
  createFeeType: (data) => client.post("/billing/fee-types", data),
  updateFeeType: (id, data) => client.put(`/billing/fee-types/${id}`, data),
  deleteFeeType: (id) => client.delete(`/billing/fee-types/${id}`),

  invoices: (params) => client.get("/billing/invoices", { params }),
  getInvoice: (id) => client.get(`/billing/invoices/${id}`),
  createInvoice: (data) => client.post("/billing/invoices", data),
  bulkCreateInvoices: (data) => client.post("/billing/invoices/bulk", data),
  cancelInvoice: (id) => client.post(`/billing/invoices/${id}/cancel`),
  sendInvoice: (id, data) => client.post(`/billing/invoices/${id}/send`, data),
  remindInvoice: (id) => client.post(`/billing/invoices/${id}/remind`),

  parentBalance: (parentId) => client.get(`/billing/parent/${parentId}/balance`),
  parentInvoices: (parentId, params) =>
    client.get(`/billing/parent/${parentId}/invoices`, { params }),

  stats: () => client.get("/billing/stats"),

  triggerReminders: () => client.post("/billing/tasks/send-reminders"),
  triggerOverdueCheck: () => client.post("/billing/tasks/check-overdue"),
};

export const broadcasts = {
  list: (limit = 50, offset = 0) =>
    client.get("/broadcasts", { params: { limit, offset } }).then((r) => r.data),
  get: (id) => client.get(`/broadcasts/${id}`).then((r) => r.data),
  create: (data) => client.post("/broadcasts", data).then((r) => r.data),
  preview: (id) => client.post(`/broadcasts/${id}/preview`).then((r) => r.data),
  send: (id) => client.post(`/broadcasts/${id}/send`).then((r) => r.data),
  cancel: (id) => client.delete(`/broadcasts/${id}`).then((r) => r.data),
};

export const calendar = {
  list: () => client.get("/calendar/events"),
  upcoming: (days = 30) => client.get("/calendar/events/upcoming", { params: { days } }),
  create: (data) => client.post("/calendar/events", data),
  update: (id, data) => client.put(`/calendar/events/${id}`, data),
  deactivate: (id) => client.delete(`/calendar/events/${id}`),
};

export const permissions = {
  listSlips: (limit = 50, offset = 0) =>
    client.get(`/permissions/slips?limit=${limit}&offset=${offset}`).then(r => r.data),
  getSlip: (id) =>
    client.get(`/permissions/slips/${id}`).then(r => r.data),
  createSlip: (data) =>
    client.post('/permissions/slips', data).then(r => r.data),
  sendSlip: (id) =>
    client.post(`/permissions/slips/${id}/send`).then(r => r.data),
  getResponses: (id) =>
    client.get(`/permissions/slips/${id}/responses`).then(r => r.data),
  closeSlip: (id) =>
    client.put(`/permissions/slips/${id}/close`).then(r => r.data),
  overrideResponse: (slip_id, parent_id, response) =>
    client.put(`/permissions/slips/${slip_id}/responses/${parent_id}`, { response }).then(r => r.data),
};

export const paymentPlans = {
  listPlans: (params) => client.get("/billing/plans", { params }),
  getPlan: (id) => client.get(`/billing/plans/${id}`),
  createPlan: (invoiceId, data) => client.post(`/billing/invoices/${invoiceId}/plan`, data),
  invoicePlan: (invoiceId) => client.get(`/billing/invoices/${invoiceId}/plan`),
  cancelPlan: (planId) => client.post(`/billing/plans/${planId}/cancel`),
  markPaid: (planId, instId) => client.put(`/billing/plans/${planId}/installments/${instId}/pay`),
  waive: (planId, instId) => client.put(`/billing/plans/${planId}/installments/${instId}/waive`),
};

export const reportCards = {
  list: (params) => client.get("/report-cards", { params }).then(r => r.data),
  get: (id) => client.get(`/report-cards/${id}`).then(r => r.data),
  create: (data) => client.post("/report-cards", data).then(r => r.data),
  setSubjects: (id, subjects) => client.put(`/report-cards/${id}/subjects`, { subjects }).then(r => r.data),
  publish: (id) => client.post(`/report-cards/${id}/publish`).then(r => r.data),
  studentHistory: (studentId) => client.get(`/students/${studentId}/report-cards`).then(r => r.data),
  adminAcknowledge: (id, parentId) =>
    client.put(`/report-cards/${id}/deliveries/${parentId}/acknowledge`).then(r => r.data),
};

export const analytics = {
  volume: (params) => client.get("/analytics/volume", { params }),
  responseTime: (params) => client.get("/analytics/response-time", { params }),
  resolutionRate: (params) => client.get("/analytics/resolution-rate", { params }),
  funnel: (params) => client.get("/analytics/funnel", { params }),
  referrals: (params) => client.get("/analytics/referrals", { params }),
  leaderboard: (params) => client.get("/analytics/referrals/leaderboard", { params }),
  ai: (params) => client.get("/analytics/ai", { params }),
  aiTopQueries: (params) => client.get("/analytics/ai/top-queries", { params }),
};
