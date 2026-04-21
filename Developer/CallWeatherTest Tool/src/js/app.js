/**
 * Weather API 测试工具 - 核心逻辑
 * @author Developer
 * @version 1.0.0
 */

// ==================== 常量定义 ====================

/** API 端点配置（完整路径，含 /api/v1 前缀） */
const API_ENDPOINTS = {
  current: '/api/v1/weather/current',
  forecast: '/api/v1/weather/forecast',
  aqi: '/api/v1/weather/aqi',
  alerts: '/api/v1/weather/alerts'
};

/** LocalStorage Key */
const STORAGE_KEYS = {
  apiKey: 'weather_api_key',
  apiUrl: 'weather_api_url',
  history: 'weather_call_history'
};

/** 最大历史记录数 */
const MAX_HISTORY = 10;

// ==================== 状态管理 ====================

/** 当前选中的 Tab */
let currentTab = 'current';

/** 上一次请求的响应数据 */
let lastResponse = null;

/** 上一次请求的 curl 命令 */
let lastCurlCommand = null;

/** 请求开始时间 */
let requestStartTime = null;

// ==================== 初始化 ====================

/**
 * 页面加载完成后初始化
 */
document.addEventListener('DOMContentLoaded', () => {
  loadConfig();
  loadHistory();
  setupKeyboardShortcuts();
});

/**
 * 设置快捷键
 */
function setupKeyboardShortcuts() {
  document.addEventListener('keydown', (e) => {
    // Ctrl + Enter: 发送请求
    if (e.ctrlKey && e.key === 'Enter') {
      e.preventDefault();
      sendRequest(currentTab);
    }
    // Escape: 关闭弹窗
    if (e.key === 'Escape') {
      closeHelp();
      closeAbout();
    }
  });
}

// ==================== 配置管理 ====================

/**
 * 加载已保存的配置
 */
function loadConfig() {
  const savedKey = localStorage.getItem(STORAGE_KEYS.apiKey);
  const savedUrl = localStorage.getItem(STORAGE_KEYS.apiUrl);

  if (savedKey) {
    document.getElementById('apiKey').value = savedKey;
  }

  if (savedUrl) {
    document.getElementById('apiUrl').value = savedUrl;
  }
}

/**
 * 保存配置
 */
function saveConfig() {
  const apiKey = document.getElementById('apiKey').value.trim();
  const apiUrl = document.getElementById('apiUrl').value.trim();

  if (!apiKey) {
    showToast('请输入 API Key', 'error');
    return;
  }

  if (!apiUrl) {
    showToast('请输入 API 地址', 'error');
    return;
  }

  // 验证 URL 格式
  try {
    new URL(apiUrl);
  } catch (e) {
    showToast('API 地址格式不正确', 'error');
    return;
  }

  localStorage.setItem(STORAGE_KEYS.apiKey, apiKey);
  localStorage.setItem(STORAGE_KEYS.apiUrl, apiUrl);

  // 显示保存成功提示
  const toast = document.getElementById('saveToast');
  toast.classList.remove('hidden');
  setTimeout(() => {
    toast.classList.add('hidden');
  }, 2000);
}

/**
 * 切换 API Key 显示/隐藏
 */
function toggleApiKeyVisibility() {
  const input = document.getElementById('apiKey');
  const eyeIcon = document.getElementById('eyeIcon');

  if (input.type === 'password') {
    input.type = 'text';
    eyeIcon.innerHTML = `
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"></path>
    `;
  } else {
    input.type = 'password';
    eyeIcon.innerHTML = `
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
    `;
  }
}

// ==================== Tab 切换 ====================

/**
 * 切换 Tab
 * @param {string} tab - Tab 名称
 */
function switchTab(tab) {
  currentTab = tab;

  // 隐藏所有面板
  document.querySelectorAll('.api-panel').forEach(panel => {
    panel.classList.add('hidden');
  });

  // 取消所有 Tab 激活状态
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.remove('tab-active');
    btn.classList.add('border-transparent');
  });

  // 显示选中的面板和 Tab
  document.getElementById(`panel-${tab}`).classList.remove('hidden');
  document.getElementById(`tab-${tab}`).classList.add('tab-active');
}

// ==================== API 请求 ====================

/**
 * 发送 API 请求
 * @param {string} type - 请求类型
 */
async function sendRequest(type) {
  const apiKey = document.getElementById('apiKey').value.trim();
  const apiUrl = document.getElementById('apiUrl').value.trim();

  // 隐藏之前的请求命令显示
  document.getElementById('requestCommand').classList.add('hidden');

  // 验证配置
  if (!apiKey) {
    showError('API Key 未配置', '请先输入并保存 API Key');
    return;
  }

  if (!apiUrl) {
    showError('API 地址未配置', '请先输入并保存 API 地址');
    return;
  }

  // 获取参数
  let params = {};
  const cityInput = document.getElementById(`city-${type}`);
  
  if (cityInput) {
    const city = cityInput.value.trim();
    if (!city) {
      showError('参数缺失', '请输入城市名称');
      cityInput.focus();
      return;
    }
    params.city = city;
  }

  // 天气预报需要天数参数
  if (type === 'forecast') {
    const days = document.getElementById('days-forecast').value;
    params.days = parseInt(days);
  }

  // 显示加载状态
  showLoading(true);
  requestStartTime = Date.now();

  try {
    // 构建请求 URL
    const endpoint = API_ENDPOINTS[type];
    const queryString = new URLSearchParams(params).toString();
    const url = `${apiUrl}${endpoint}${queryString ? '?' + queryString : ''}`;

    // 生成 curl 命令（Windows 兼容，使用 ^ 转义换行）
    lastCurlCommand = `curl -X GET "${url}" ^\n  -H "X-Access-Key: ${apiKey}" ^\n  -H "Content-Type: application/json"`;

    // 调试：输出实际请求 URL
    console.log('实际请求 URL:', url);

    // 发送请求
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'X-Access-Key': apiKey,
        'Content-Type': 'application/json'
      }
    });

    const responseTime = Date.now() - requestStartTime;
    const data = await response.json();

    // 保存响应数据
    lastResponse = data;

    // 显示响应
    displayResponse(data, response.status, responseTime, endpoint, params);

    // 添加到历史记录
    addToHistory({
      id: generateId(),
      timestamp: new Date().toISOString(),
      api: endpoint,
      params: params,
      status: response.status,
      duration: responseTime,
      response: data
    });

  } catch (error) {
    const responseTime = Date.now() - requestStartTime;
    
    // 调试：输出错误和 URL
    console.log('请求失败 - URL:', url);
    console.log('错误详情:', error);
    
    // 网络错误
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      showError('网络错误', `无法连接到服务器，请检查网络连接和 API 地址是否正确\n\n请求URL: ${url}`);
    } else {
      showError('请求失败', `${error.message || '未知错误'}\n\n请求URL: ${url}`);
    }

    // 添加到历史记录（错误）
    addToHistory({
      id: generateId(),
      timestamp: new Date().toISOString(),
      api: API_ENDPOINTS[type],
      params: params,
      status: 0,
      statusText: 'Network Error',
      duration: responseTime,
      error: error.message
    });

  } finally {
    showLoading(false);
  }
}

/**
 * 显示响应结果
 * @param {Object} data - 响应数据
 * @param {number} status - HTTP 状态码
 * @param {number} responseTime - 响应时间(ms)
 * @param {string} endpoint - API 端点
 * @param {Object} params - 请求参数
 */
function displayResponse(data, status, responseTime, endpoint, params) {
  const statusEl = document.getElementById('responseStatus');
  const statusIcon = document.getElementById('statusIcon');
  const statusText = document.getElementById('statusText');
  const statusDetail = document.getElementById('statusDetail');
  const statusCode = document.getElementById('statusCode');
  const responseTimeEl = document.getElementById('responseTime');
  const jsonEl = document.getElementById('responseJson');
  const requestCommandEl = document.getElementById('requestCommand');

  // 显示状态区域
  statusEl.classList.remove('hidden', 'bg-green-100', 'bg-yellow-100', 'bg-red-100');
  statusCode.textContent = status;
  responseTimeEl.textContent = `${responseTime}ms`;

  if (status >= 200 && status < 300) {
    // 成功
    statusEl.classList.add('bg-green-100');
    statusIcon.textContent = '✅';
    statusText.textContent = '请求成功';
    statusText.className = 'font-medium text-green-800';
    statusDetail.textContent = data.message || 'success';
    statusCode.className = 'text-lg font-bold text-green-600';
  } else if (status >= 300 && status < 400) {
    // 重定向
    statusEl.classList.add('bg-blue-100');
    statusIcon.textContent = '🔄';
    statusText.textContent = '重定向';
    statusText.className = 'font-medium text-blue-800';
    statusDetail.textContent = data.message || 'Redirect';
    statusCode.className = 'text-lg font-bold text-blue-600';
  } else if (status >= 400 && status < 500) {
    // 客户端错误
    statusEl.classList.add('bg-yellow-100');
    statusIcon.textContent = '⚠️';
    statusText.textContent = '客户端错误';
    statusText.className = 'font-medium text-yellow-800';
    statusDetail.textContent = data.message || 'Client Error';
    statusCode.className = 'text-lg font-bold text-yellow-600';
  } else {
    // 服务器错误
    statusEl.classList.add('bg-red-100');
    statusIcon.textContent = '❌';
    statusText.textContent = '服务器错误';
    statusText.className = 'font-medium text-red-800';
    statusDetail.textContent = data.message || 'Server Error';
    statusCode.className = 'text-lg font-bold text-red-600';
  }

  // 显示 JSON 内容
  jsonEl.textContent = JSON.stringify(data, null, 2);

  // 启用复制按钮
  document.getElementById('copyBtn').disabled = false;

  // 显示 curl 命令
  if (lastCurlCommand) {
    requestCommandEl.classList.remove('hidden');
    document.getElementById('curlCommand').textContent = lastCurlCommand;
  }
}

/**
 * 显示错误信息
 * @param {string} title - 错误标题
 * @param {string} message - 错误详情
 */
function showError(title, message) {
  lastResponse = null;

  const statusEl = document.getElementById('responseStatus');
  const statusIcon = document.getElementById('statusIcon');
  const statusText = document.getElementById('statusText');
  const statusDetail = document.getElementById('statusDetail');
  const statusCode = document.getElementById('statusCode');
  const responseTimeEl = document.getElementById('responseTime');
  const jsonEl = document.getElementById('responseJson');
  const requestCommandEl = document.getElementById('requestCommand');

  statusEl.classList.remove('hidden', 'bg-green-100', 'bg-yellow-100', 'bg-blue-100');
  statusEl.classList.add('bg-red-100');
  
  statusIcon.textContent = '❌';
  statusText.textContent = title;
  statusText.className = 'font-medium text-red-800';
  statusDetail.textContent = message;
  statusCode.textContent = 'Error';
  statusCode.className = 'text-lg font-bold text-red-600';
  
  const elapsed = requestStartTime ? Date.now() - requestStartTime : 0;
  responseTimeEl.textContent = `${elapsed}ms`;

  jsonEl.textContent = JSON.stringify({
    error: title,
    message: message,
    timestamp: new Date().toISOString()
  }, null, 2);

  // 显示 curl 命令（如果有的话）
  if (lastCurlCommand) {
    requestCommandEl.classList.remove('hidden');
    document.getElementById('curlCommand').textContent = lastCurlCommand;
  }
}

// ==================== 历史记录 ====================

/**
 * 从 LocalStorage 加载历史记录
 */
function loadHistory() {
  const history = getHistory();
  renderHistory(history);
}

/**
 * 获取历史记录
 * @returns {Array} 历史记录数组
 */
function getHistory() {
  try {
    const data = localStorage.getItem(STORAGE_KEYS.history);
    return data ? JSON.parse(data) : [];
  } catch (e) {
    console.error('加载历史记录失败:', e);
    return [];
  }
}

/**
 * 保存历史记录到 LocalStorage
 * @param {Array} history - 历史记录数组
 */
function saveHistory(history) {
  try {
    localStorage.setItem(STORAGE_KEYS.history, JSON.stringify(history));
  } catch (e) {
    console.error('保存历史记录失败:', e);
  }
}

/**
 * 添加到历史记录
 * @param {Object} record - 记录对象
 */
function addToHistory(record) {
  let history = getHistory();
  
  // 添加到开头
  history.unshift(record);
  
  // 限制数量
  if (history.length > MAX_HISTORY) {
    history = history.slice(0, MAX_HISTORY);
  }
  
  saveHistory(history);
  renderHistory(history);
}

/**
 * 渲染历史记录列表
 * @param {Array} history - 历史记录数组
 */
function renderHistory(history) {
  const container = document.getElementById('historyList');
  const clearBtn = document.getElementById('clearHistoryBtn');

  if (!history || history.length === 0) {
    container.innerHTML = '<p class="text-gray-400 text-sm text-center py-4">暂无调用记录</p>';
    clearBtn.disabled = true;
    return;
  }

  clearBtn.disabled = false;

  container.innerHTML = history.map((record, index) => {
    const time = formatTime(record.timestamp);
    const paramsStr = Object.entries(record.params)
      .map(([k, v]) => `${k}=${v}`)
      .join('&');
    const url = `${record.api}${paramsStr ? '?' + paramsStr : ''}`;
    
    let statusHtml = '';
    let statusClass = '';
    
    if (record.status >= 200 && record.status < 300) {
      statusHtml = `<span class="inline-block w-2 h-2 rounded-full bg-green-500 mr-1"></span>${record.status}`;
      statusClass = 'text-green-600';
    } else if (record.status >= 400 && record.status < 500) {
      statusHtml = `<span class="inline-block w-2 h-2 rounded-full bg-yellow-500 mr-1"></span>${record.status}`;
      statusClass = 'text-yellow-600';
    } else if (record.status >= 500) {
      statusHtml = `<span class="inline-block w-2 h-2 rounded-full bg-red-500 mr-1"></span>${record.status}`;
      statusClass = 'text-red-600';
    } else {
      statusHtml = `<span class="inline-block w-2 h-2 rounded-full bg-gray-500 mr-1"></span>Error`;
      statusClass = 'text-gray-500';
    }

    return `
      <div class="flex items-center gap-3 p-3 bg-gray-50 hover:bg-gray-100 rounded-lg cursor-pointer transition" onclick="loadHistoryItem(${index})">
        ${statusHtml}
        <span class="flex-1 text-sm text-gray-600 truncate" title="${url}">${time} ${url}</span>
        <span class="text-xs text-gray-400">${record.duration}ms</span>
      </div>
    `;
  }).join('');
}

/**
 * 加载历史记录项
 * @param {number} index - 历史记录索引
 */
function loadHistoryItem(index) {
  const history = getHistory();
  const record = history[index];
  
  if (!record) return;

  // 切换到对应的 Tab
  const apiType = Object.keys(API_ENDPOINTS).find(
    key => API_ENDPOINTS[key] === record.api
  );
  
  if (apiType) {
    switchTab(apiType);
    
    // 填充参数
    if (record.params.city) {
      const cityInput = document.getElementById(`city-${apiType}`);
      if (cityInput) cityInput.value = record.params.city;
    }
    
    if (apiType === 'forecast' && record.params.days) {
      document.getElementById('days-forecast').value = record.params.days;
    }
  }

  // 显示响应
  if (record.error) {
    showError('历史记录', record.error);
  } else {
    displayResponse(record.response, record.status, record.duration, record.api, record.params);
  }
}

/**
 * 清空历史记录
 */
function clearHistory() {
  if (!confirm('确定要清空所有历史记录吗？')) return;
  
  localStorage.removeItem(STORAGE_KEYS.history);
  renderHistory([]);
}

// ==================== 响应操作 ====================

/**
 * 复制响应内容
 */
function copyResponse() {
  if (!lastResponse) return;

  const text = JSON.stringify(lastResponse, null, 2);

  navigator.clipboard.writeText(text).then(() => {
    showToast('已复制到剪贴板', 'success');
  }).catch(err => {
    // 降级方案
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    showToast('已复制到剪贴板', 'success');
  });
}

/**
 * 复制 curl 命令
 */
function copyCurlCommand() {
  if (!lastCurlCommand) return;

  navigator.clipboard.writeText(lastCurlCommand).then(() => {
    showToast('curl 命令已复制到剪贴板', 'success');
  }).catch(err => {
    // 降级方案
    const textarea = document.createElement('textarea');
    textarea.value = lastCurlCommand;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    showToast('curl 命令已复制到剪贴板', 'success');
  });
}

/**
 * 清空响应内容
 */
function clearResponse() {
  lastResponse = null;
  lastCurlCommand = null;

  document.getElementById('responseStatus').classList.add('hidden');
  document.getElementById('requestCommand').classList.add('hidden');
  document.getElementById('responseJson').textContent = '响应内容将显示在这里...';
  document.getElementById('copyBtn').disabled = true;
}

// ==================== UI 辅助函数 ====================

/**
 * 显示加载状态
 * @param {boolean} show - 是否显示
 */
function showLoading(show) {
  const overlay = document.getElementById('loadingOverlay');
  if (show) {
    overlay.classList.remove('hidden');
  } else {
    overlay.classList.add('hidden');
  }
}

/**
 * 显示 Toast 提示
 * @param {string} message - 提示内容
 * @param {string} type - 类型：success, error, warning
 */
function showToast(message, type = 'success') {
  // 简单的 alert 实现，可替换为更美观的 Toast 组件
  if (type === 'success') {
    // 创建临时 toast
    const toast = document.createElement('div');
    toast.className = 'fixed bottom-4 right-4 px-4 py-2 bg-green-500 text-white rounded-lg shadow-lg z-50';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2000);
  } else if (type === 'error') {
    alert(message);
  }
}

// ==================== 弹窗操作 ====================

/**
 * 显示帮助弹窗
 */
function showHelp() {
  document.getElementById('helpModal').classList.remove('hidden');
}

/**
 * 关闭帮助弹窗
 */
function closeHelp() {
  document.getElementById('helpModal').classList.add('hidden');
}

/**
 * 显示关于弹窗
 */
function showAbout() {
  document.getElementById('aboutModal').classList.remove('hidden');
}

/**
 * 关闭关于弹窗
 */
function closeAbout() {
  document.getElementById('aboutModal').classList.add('hidden');
}

// ==================== 工具函数 ====================

/**
 * 生成唯一 ID
 * @returns {string} UUID
 */
function generateId() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

/**
 * 格式化时间
 * @param {string} isoString - ISO 时间字符串
 * @returns {string} 格式化后的时间
 */
function formatTime(isoString) {
  const date = new Date(isoString);
  const now = new Date();
  const diff = now - date;
  
  // 1 分钟内
  if (diff < 60000) {
    return '刚刚';
  }
  
  // 1 小时内
  if (diff < 3600000) {
    const mins = Math.floor(diff / 60000);
    return `${mins}分钟前`;
  }
  
  // 24 小时内
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000);
    return `${hours}小时前`;
  }
  
  // 超过 24 小时，显示日期
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const hours = date.getHours().toString().padStart(2, '0');
  const mins = date.getMinutes().toString().padStart(2, '0');
  return `${month}-${day} ${hours}:${mins}`;
}
