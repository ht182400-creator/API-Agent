/**
 * API 测试工具
 * @description 统一的API测试工具，支持多仓库、多端点、动态表单
 */

import React, { useState, useMemo, useCallback } from 'react';
import '../../styles/cyber-theme.css';
import { repositories, selfRepositories, thirdPartyRepositories, repositoryStats } from '../../config/repositories.config';
import { Repository, Endpoint, RequestHistory, HttpMethod } from '../../types/api-tester';
import { RepositoryCard } from '../../components/api-tester/RepositoryCard';
import { EndpointList } from '../../components/api-tester/EndpointList';
import { DynamicForm } from '../../components/api-tester/DynamicForm';
import { ResponsePanel } from '../../components/api-tester/ResponsePanel';
import { useApiKeyStore } from '../../stores/apiKey';
import { useAuthStore } from '../../stores/auth';
import styles from './ApiTester.module.css';

type CategoryFilter = 'all' | 'self' | 'third_party';

export const ApiTester: React.FC = () => {
  // 状态
  const [category, setCategory] = useState<CategoryFilter>('all');
  const [selectedRepo, setSelectedRepo] = useState<Repository | null>(null);
  const [selectedEndpoint, setSelectedEndpoint] = useState<Endpoint | null>(null);
  const [paramValues, setParamValues] = useState<Record<string, any>>({});
  const [response, setResponse] = useState<any>(null);
  const [status, setStatus] = useState<number>(0);
  const [duration, setDuration] = useState<number>(0);
  const [curlCommand, setCurlCommand] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<RequestHistory[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [showKeyConfig, setShowKeyConfig] = useState(false);
  const [tempApiKey, setTempApiKey] = useState('');

  // 获取 API Key 和用户信息
  const { apiKey, setApiKey, clearApiKey } = useApiKeyStore();
  const { user } = useAuthStore();

  // 根据分类筛选仓库
  const filteredRepos = useMemo(() => {
    switch (category) {
      case 'self': return selfRepositories;
      case 'third_party': return thirdPartyRepositories;
      default: return repositories;
    }
  }, [category]);

  // 处理参数变化
  const handleParamChange = useCallback((name: string, value: any) => {
    setParamValues(prev => ({ ...prev, [name]: value }));
  }, []);

  // 选择仓库
  const handleSelectRepo = useCallback((repo: Repository) => {
    setSelectedRepo(repo);
    setSelectedEndpoint(null);
    setParamValues({});
    setResponse(null);
  }, []);

  // 选择端点
  const handleSelectEndpoint = useCallback((endpoint: Endpoint) => {
    setSelectedEndpoint(endpoint);
    setParamValues({});
    setResponse(null);
  }, []);

  // 构建URL - 通过后端 proxy 接口
  const buildUrl = useCallback((repo: Repository, endpoint: Endpoint): string => {
    let path = endpoint.path;
    
    // 替换路径参数
    endpoint.params?.filter(p => p.in === 'path').forEach(p => {
      const value = paramValues[p.name];
      if (value) {
        path = path.replace(`{${p.name}}`, value);
      }
    });

    // 构建查询参数
    const queryParams = endpoint.params?.filter(p => p.in === 'query') || [];
    const queryString = queryParams
      .filter(p => paramValues[p.name])
      .map(p => `${encodeURIComponent(p.name)}=${encodeURIComponent(paramValues[p.name])}`)
      .join('&');

    // 通过 API Platform 后端 proxy 接口调用：/api/v1/repositories/{repo_slug}/{path}
    return `/api/v1/repositories/${repo.slug}${path}${queryString ? '?' + queryString : ''}`;
  }, [paramValues]);

  // 生成curl命令 - 通过 API Platform 后端 proxy 接口
  const generateCurlCommand = useCallback((repo: Repository, url: string, method: HttpMethod): string => {
    const apiUrl = 'http://localhost:8000';
    const fullUrl = `${apiUrl}${url}`;
    const headers = [`-H "X-Access-Key: <YOUR_API_KEY>"`, `-H "Content-Type: application/json"`];
    
    let command = `curl -X ${method} "${fullUrl}"`;
    if (method !== 'GET') {
      const bodyParams = selectedEndpoint?.requestBody || [];
      if (bodyParams.length > 0) {
        const body: Record<string, any> = {};
        bodyParams.forEach(p => {
          if (paramValues[p.name]) {
            body[p.name] = paramValues[p.name];
          }
        });
        if (Object.keys(body).length > 0) {
          command += ` -d '${JSON.stringify(body)}'`;
        }
      }
    }
    
    return command + '\n' + headers.map(h => `  ${h}`).join(' \\\n');
  }, [selectedEndpoint, paramValues]);

  // 发送请求 - 通过 API Platform 后端 proxy 接口
  const handleSendRequest = async () => {
    if (!selectedRepo || !selectedEndpoint) return;

    // 始终通过 API Platform 后端（端口 8000）调用，proxy 接口会自动记录日志
    const apiUrl = 'http://localhost:8000';
    const url = buildUrl(selectedRepo, selectedEndpoint);
    const fullUrl = `${apiUrl}${url}`;
    const curl = generateCurlCommand(selectedRepo, url, selectedEndpoint.method);

    setLoading(true);
    setResponse(null);
    const startTime = Date.now();

    try {
      const options: RequestInit = {
        method: selectedEndpoint.method,
        headers: {
          'X-Access-Key': apiKey || 'YOUR_API_KEY',
          'Content-Type': 'application/json'
        }
      };

      if (['POST', 'PUT', 'PATCH'].includes(selectedEndpoint.method)) {
        const bodyParams = selectedEndpoint.requestBody || [];
        const body: Record<string, any> = {};
        bodyParams.forEach(p => {
          if (paramValues[p.name]) {
            body[p.name] = paramValues[p.name];
          }
        });
        if (Object.keys(body).length > 0) {
          options.body = JSON.stringify(body);
        }
      }

      setCurlCommand(curl);

      const res = await fetch(fullUrl, options);
      const data = await res.json();
      const elapsed = Date.now() - startTime;

      setResponse(data);
      setStatus(res.status);
      setDuration(elapsed);

      const record: RequestHistory = {
        id: `req_${Date.now()}`,
        timestamp: new Date().toISOString(),
        tester: user?.username || user?.name || user?.email || '未知用户',
        repository: selectedRepo.name,
        repositoryId: selectedRepo.id,
        endpoint: selectedEndpoint.name,
        endpointId: selectedEndpoint.id,
        method: selectedEndpoint.method,
        params: { ...paramValues },
        requestBody: selectedEndpoint.requestBody?.length ? { ...paramValues } : undefined,
        status: res.status,
        duration: elapsed,
        response: data
      };
      setHistory(prev => [record, ...prev].slice(0, 50));

    } catch (error: any) {
      const elapsed = Date.now() - startTime;
      setResponse({ error: true, message: error.message || '网络请求失败' });
      setStatus(0);
      setDuration(elapsed);
      setCurlCommand(curl);

      const record: RequestHistory = {
        id: `req_${Date.now()}`,
        timestamp: new Date().toISOString(),
        tester: user?.username || user?.name || user?.email || '未知用户',
        repository: selectedRepo.name,
        repositoryId: selectedRepo.id,
        endpoint: selectedEndpoint.name,
        endpointId: selectedEndpoint.id,
        method: selectedEndpoint.method,
        params: { ...paramValues },
        requestBody: selectedEndpoint.requestBody?.length ? { ...paramValues } : undefined,
        status: 0,
        duration: elapsed,
        response: null,
        error: error.message
      };
      setHistory(prev => [record, ...prev].slice(0, 50));
    } finally {
      setLoading(false);
    }
  };

  // 清空响应
  const handleClearResponse = () => {
    setResponse(null);
    setStatus(0);
    setDuration(0);
    setCurlCommand('');
  };

  // 获取方法样式
  const getMethodStyle = (method: HttpMethod) => {
    const colors: Record<HttpMethod, { bg: string; text: string }> = {
      GET: { bg: 'bg-emerald-100', text: 'text-emerald-700' },
      POST: { bg: 'bg-blue-100', text: 'text-blue-700' },
      PUT: { bg: 'bg-amber-100', text: 'text-amber-700' },
      DELETE: { bg: 'bg-rose-100', text: 'text-rose-700' },
      PATCH: { bg: 'bg-violet-100', text: 'text-violet-700' }
    };
    return colors[method];
  };

  return (
    <div className={`${styles.container} bamboo-bg-pattern`}>
      {/* 加载遮罩 */}
      {loading && (
        <div className={styles.loadingOverlay}>
          <div className={styles.loadingBox}>
            <div className={styles.spinner}></div>
            <span>请求中...</span>
          </div>
        </div>
      )}

      {/* 头部 */}
      <div className={styles.header}>
        <div className={styles.titleRow}>
          <h1 className={styles.title}>
            <span>🧪</span>
            <span>API 测试工具</span>
          </h1>
          <div className={styles.stats}>
            <span className={styles.statBadge}>
              <span className={styles.statIcon}>📦</span>
              {repositoryStats.total} 个仓库
            </span>
            <span className={styles.statBadge}>
              <span className={styles.statIcon}>🔗</span>
              {repositories.reduce((acc, r) => acc + r.endpoints.length, 0)} 个接口
            </span>
          </div>
        </div>
      </div>

      {/* 工具栏 */}
      <div className={styles.toolbar}>
        <div className={styles.categoryTabs}>
          <button
            className={`${styles.categoryBtn} ${category === 'all' ? styles.categoryBtnActive : ''}`}
            onClick={() => setCategory('all')}
          >
            全部
          </button>
          <button
            className={`${styles.categoryBtn} ${category === 'self' ? styles.categoryBtnActive : ''}`}
            onClick={() => setCategory('self')}
          >
            🏠 自研
          </button>
          <button
            className={`${styles.categoryBtn} ${category === 'third_party' ? styles.categoryBtnActive : ''}`}
            onClick={() => setCategory('third_party')}
          >
            🌐 第三方
          </button>
        </div>
        
        <button
          className={styles.historyBtn}
          onClick={() => setShowHistory(!showHistory)}
        >
          <span>📜</span>
          <span>历史 ({history.length})</span>
        </button>
        
        <button
          className={`${styles.configBtn} ${apiKey ? styles.configBtnSuccess : ''}`}
          onClick={() => {
            setTempApiKey(apiKey || '');
            setShowKeyConfig(!showKeyConfig);
          }}
        >
          <span>{apiKey ? '🔑' : '⚠️'}</span>
          <span>{apiKey ? '已配置' : '配置Key'}</span>
        </button>
      </div>

      {/* API Key 配置面板 */}
      {showKeyConfig && (
        <div className={styles.configPanel}>
          <div className={styles.configPanelHeader}>
            <span>🔑 API Key 配置</span>
            <button className={styles.configCloseBtn} onClick={() => setShowKeyConfig(false)}>×</button>
          </div>
          <div className={styles.configPanelBody}>
            <div className={styles.configForm}>
              <div className={styles.configFormGroup}>
                <label htmlFor="apiKeyInput">访问密钥 (X-Access-Key)</label>
                <div className={styles.configInputWrapper}>
                  <input
                    id="apiKeyInput"
                    type="password"
                    className={styles.configInput}
                    placeholder="请输入 API Key"
                    value={tempApiKey}
                    onChange={(e) => setTempApiKey(e.target.value)}
                    autoFocus
                  />
                  <button
                    className={styles.configToggleBtn}
                    onClick={() => {
                      const input = document.getElementById('apiKeyInput') as HTMLInputElement;
                      input.type = input.type === 'password' ? 'text' : 'password';
                    }}
                  >
                    👁️
                  </button>
                </div>
                <p className={styles.configHelp}>
                  请输入 Owner Server 的访问密钥，用于调用受保护的 API 接口。
                </p>
              </div>
              <div className={styles.configActions}>
                <button
                  className={styles.configSaveBtn}
                  onClick={() => {
                    setApiKey(tempApiKey.trim());
                    setShowKeyConfig(false);
                  }}
                >
                  💾 保存
                </button>
                {apiKey && (
                  <button
                    className={styles.configClearBtn}
                    onClick={() => {
                      clearApiKey();
                      setTempApiKey('');
                    }}
                  >
                    🗑️ 清除
                  </button>
                )}
                <button
                  className={styles.configCancelBtn}
                  onClick={() => setShowKeyConfig(false)}
                >
                  取消
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 历史记录面板 */}
      {showHistory && history.length > 0 && (
        <div className={styles.historyPanel}>
          <div className={styles.historyPanelHeader}>
            <span>📜 最近请求</span>
            <button className={styles.historyCloseBtn} onClick={() => setShowHistory(false)}>×</button>
          </div>
          <div className={styles.historyList}>
            {history.slice(0, 10).map(record => (
              <div
                key={record.id}
                className={styles.historyItem}
                onClick={() => {
                  const repo = repositories.find(r => r.name === record.repository);
                  if (repo) {
                    setSelectedRepo(repo);
                    const endpoint = repo.endpoints.find(e => e.name === record.endpoint);
                    if (endpoint) {
                      setSelectedEndpoint(endpoint);
                      setParamValues(record.params);
                      setResponse(record.response);
                      setStatus(record.status);
                      setDuration(record.duration);
                    }
                  }
                  setShowHistory(false);
                }}
              >
                <span className={`${styles.historyStatus} ${record.status >= 200 && record.status < 300 ? styles.statusSuccess : styles.statusError}`}>
                  {record.status || 'Err'}
                </span>
                <span className={styles.historyTime}>
                  {new Date(record.timestamp).toLocaleTimeString()}
                </span>
                <span className={styles.historyRepo}>{record.repository}</span>
                <span className={styles.historyEndpoint}>{record.endpoint}</span>
                <span className={styles.historyTester}>{record.tester}</span>
                <span className={styles.historyDuration}>{record.duration}ms</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 主内容区 */}
      <div className={styles.mainGrid}>
        {/* 仓库列表 */}
        <div className={styles.leftPanel}>
          <div className={styles.panel}>
            <div className={styles.panelHeader}>
              <span>仓库</span>
              <span className={styles.panelHeaderCount}>{filteredRepos.length}</span>
            </div>
            <div className={styles.panelBody}>
              {filteredRepos.length === 0 ? (
                <div className={styles.empty}>
                  <span>📭</span>
                  <p>暂无仓库</p>
                </div>
              ) : (
                <div className={styles.repoList}>
                  {filteredRepos.map(repo => (
                    <RepositoryCard
                      key={repo.id}
                      repository={repo}
                      selected={selectedRepo?.id === repo.id}
                      onClick={() => handleSelectRepo(repo)}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 端点列表 */}
        <div className={styles.middlePanel}>
          <div className={styles.panel}>
            <div className={styles.panelHeader}>
              <span>API 端点</span>
              {selectedRepo && (
                <span className={styles.panelHeaderSub}>{selectedRepo.name}</span>
              )}
            </div>
            <div className={styles.panelBody}>
              {!selectedRepo ? (
                <div className={styles.empty}>
                  <span>👈</span>
                  <p>请先选择一个仓库</p>
                </div>
              ) : (
                <EndpointList
                  endpoints={selectedRepo.endpoints}
                  selected={selectedEndpoint}
                  onSelect={handleSelectEndpoint}
                />
              )}
            </div>
          </div>
        </div>

        {/* 请求配置和响应 */}
        <div className={styles.rightPanel}>
          {/* 请求栏 */}
          <div className={styles.requestCard}>
            {!selectedEndpoint ? (
              <div className={styles.empty}>
                <span>🔧</span>
                <p>请选择一个端点进行测试</p>
              </div>
            ) : (
              <>
                {/* 端点信息 */}
                <div className={styles.endpointInfo}>
                  <span className={`${styles.methodBadge} ${getMethodStyle(selectedEndpoint.method).bg} ${getMethodStyle(selectedEndpoint.method).text}`}>
                    {selectedEndpoint.method}
                  </span>
                  <code className={styles.endpointPath}>
                    {selectedRepo?.baseUrl}{selectedEndpoint.path}
                  </code>
                </div>

                {/* 描述 */}
                {selectedEndpoint.description && (
                  <p className={styles.endpointDesc}>
                    {selectedEndpoint.description}
                  </p>
                )}

                {/* 动态表单 */}
                <DynamicForm
                  params={selectedEndpoint.params || []}
                  values={paramValues}
                  onChange={handleParamChange}
                  disabled={loading}
                />

                {/* 请求体 */}
                {selectedEndpoint.requestBody && selectedEndpoint.requestBody.length > 0 && (
                  <div className={styles.requestBodySection}>
                    <h4 className={styles.sectionTitle}>📝 请求体</h4>
                    <DynamicForm
                      params={selectedEndpoint.requestBody}
                      values={paramValues}
                      onChange={handleParamChange}
                      disabled={loading}
                    />
                  </div>
                )}

                {/* 操作按钮 */}
                <div className={styles.actionBar}>
                  <button
                    className={styles.sendBtn}
                    onClick={handleSendRequest}
                    disabled={loading || !selectedEndpoint}
                  >
                    <span>🚀</span>
                    <span>发送请求</span>
                  </button>
                  <button
                    className={styles.clearBtn}
                    onClick={handleClearResponse}
                  >
                    清空
                  </button>
                  {!apiKey && (
                    <span className={styles.warning}>
                      ⚠️ 未配置API Key
                    </span>
                  )}
                </div>
              </>
            )}
          </div>

          {/* 响应面板 */}
          {response && (
            <ResponsePanel
              response={response}
              status={status}
              duration={duration}
              curlCommand={curlCommand}
            />
          )}

          {/* 响应示例 */}
          {!response && selectedEndpoint?.responseExample && (
            <div className={`${styles.panel} ${styles.responseExample}`}>
              <div className={styles.panelHeader}>
                💡 响应示例
              </div>
              <div className={styles.panelBody}>
                <pre className={styles.jsonPreview}>
                  {JSON.stringify(selectedEndpoint.responseExample, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ApiTester;
