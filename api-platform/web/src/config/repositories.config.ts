/**
 * 仓库配置中心
 * @description 统一导出所有API仓库配置，支持分类筛选
 * 
 * 使用说明：
 * - 自研仓库：src/config/repos/ 目录下
 * - 第三方仓库：src/config/repos/third-party/ 目录下
 * - 添加新仓库：只需导入并添加到 repositories 数组中
 */

import { Repository } from '../types/api-tester';

// 自研仓库
import { weatherRepository } from './repos/weather.config';
import { logisticsRepository } from './repos/logistics.config';

// 第三方仓库
import { smsRepository } from './repos/third-party/sms.config';
import { paymentRepository } from './repos/third-party/payment.config';

/**
 * 所有仓库列表
 * @description 按添加顺序排列
 */
export const repositories: Repository[] = [
  weatherRepository,
  logisticsRepository,
  smsRepository,
  paymentRepository,
  // 未来新增仓库只需在这里添加...
];

/**
 * 自研仓库列表
 */
export const selfRepositories = repositories.filter(r => r.category === 'self');

/**
 * 第三方仓库列表
 */
export const thirdPartyRepositories = repositories.filter(r => r.category === 'third_party');

/**
 * 已启用的仓库列表
 */
export const enabledRepositories = repositories.filter(r => r.enabled !== false);

/**
 * 根据 slug 获取仓库
 * @param slug 仓库标识
 */
export const getRepositoryBySlug = (slug: string): Repository | undefined => 
  repositories.find(r => r.slug === slug);

/**
 * 根据 ID 获取仓库
 * @param id 仓库ID
 */
export const getRepositoryById = (id: string): Repository | undefined => 
  repositories.find(r => r.id === id);

/**
 * 仓库统计数据
 */
export const repositoryStats = {
  total: repositories.length,
  self: selfRepositories.length,
  thirdParty: thirdPartyRepositories.length,
  enabled: enabledRepositories.length
};
