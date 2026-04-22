/**
 * API 测试工具类型定义
 * @description 定义仓库配置、端点、参数等核心类型
 */

/** 仓库分类 */
export type RepoCategory = 'self' | 'third_party';

/** HTTP 方法 */
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

/** 认证类型 */
export type AuthType = 'api_key' | 'hmac' | 'oauth' | 'bearer';

/** 参数类型 */
export type ParamType = 'string' | 'number' | 'boolean' | 'array' | 'object' | 'select';

/** 参数位置 */
export type ParamLocation = 'query' | 'path' | 'header' | 'body';

/** 参数定义 */
export interface Parameter {
  name: string;
  type: ParamType;
  required: boolean;
  description: string;
  placeholder?: string;
  defaultValue?: string | number | boolean;
  options?: { label: string; value: string }[]; // for select type
  in: ParamLocation;
  validation?: {
    pattern?: string;
    min?: number;
    max?: number;
    minLength?: number;
    maxLength?: number;
  };
}

/** API端点定义 */
export interface Endpoint {
  id: string;
  name: string;
  description?: string;
  path: string;
  method: HttpMethod;
  params?: Parameter[];
  requestBody?: Parameter[];
  responseExample?: object;
  tags?: string[]; // 用于分组
}

/** 仓库定义 */
export interface Repository {
  id: string;
  slug: string;
  name: string;
  description: string;
  icon: string;
  category: RepoCategory;
  /** API 基础地址，如 /api/v1/weather */
  baseUrl: string;
  /** 完整的 API 服务地址，如 http://localhost:8001 */
  apiUrl?: string;
  endpoints: Endpoint[];
  authType: AuthType;
  authHeader?: string;
  enabled?: boolean;
  version?: string;
  contact?: {
    name?: string;
    email?: string;
    url?: string;
  };
}

/** 请求历史记录 */
export interface RequestHistory {
  id: string;
  timestamp: string;
  tester?: string;       // 测试人员
  repository: string;
  repositoryId?: string; // 仓库ID
  endpoint: string;
  endpointId?: string;   // 端点ID
  method: HttpMethod;
  params: Record<string, any>;
  requestBody?: Record<string, any>;  // 请求体参数
  status: number;
  duration: number;
  response: any;
  error?: string;
}

/** API响应 */
export interface ApiResponse {
  code: number;
  message: string;
  data?: any;
  error?: string;
}

/** 组件Props类型 */
export interface DynamicFormProps {
  params: Parameter[];
  values: Record<string, any>;
  onChange: (name: string, value: any) => void;
  disabled?: boolean;
}

export interface RepositoryCardProps {
  repository: Repository;
  selected: boolean;
  onClick: () => void;
}

export interface EndpointItemProps {
  endpoint: Endpoint;
  selected: boolean;
  onClick: () => void;
}

export interface ResponsePanelProps {
  response: any;
  status: number;
  duration: number;
  curlCommand?: string;
}
