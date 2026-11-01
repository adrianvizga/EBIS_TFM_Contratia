export const API_ORIGIN =
  import.meta.env.MODE === 'test' ? 'http://localhost:8000' : '';
export const API_BASE_URL = `${API_ORIGIN}/api`;
