import axios from 'axios';

// Get token from local storage
const getToken = () => localStorage.getItem('token');

const API = axios.create({
    baseURL: 'http://localhost:8000/api', // Changed from render URL to local for dev
    timeout: 120000,
});

// Intercept requests to attach token
API.interceptors.request.use((config) => {
    const token = getToken();
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

export async function login(username, password) {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    
    const res = await API.post('/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
    return res.data;
}

export async function getMe() {
    const res = await API.get('/me');
    return res.data;
}

export async function analyzeFile(file, onProgress) {
    const form = new FormData();
    form.append('file', file);
    
    const token = getToken();
    const endpoint = token ? '/analyze' : '/analyze/public';

    const res = await API.post(endpoint, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
            if (onProgress && e.total) {
                onProgress(Math.round((e.loaded / e.total) * 50));
            }
        },
    });

    return res.data;
}

export async function checkHealth() {
    const res = await API.get('/health');
    return res.data;
}
