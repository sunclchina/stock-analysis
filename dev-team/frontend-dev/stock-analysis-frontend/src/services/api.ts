import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add JWT auth token
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = 'Bearer ' + token;
    }
    // Add API key if available
    const apiKey = localStorage.getItem('stock-analysis-api-key');
    if (apiKey) {
      config.headers['X-API-Key'] = apiKey;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response;
      switch (status) {
        case 401:
          console.error('API authentication failed');
          break;
        case 404:
          console.error('API endpoint not found');
          break;
        case 500:
          console.error('API server error:', data?.message || 'Unknown error');
          break;
        default:
          console.error(`API error (${status}):`, data?.message || 'Unknown error');
      }
    } else if (error.request) {
      console.error('Network error: no response from server');
    }
    return Promise.reject(error);
  }
);

export default apiClient;
