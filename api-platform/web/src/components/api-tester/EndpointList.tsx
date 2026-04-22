/**
 * 端点列表组件
 * @description 显示仓库的所有API端点
 */

import React from 'react';
import { Endpoint, HttpMethod } from '../../types/api-tester';
import styles from './EndpointList.module.css';

interface Props {
  endpoints: Endpoint[];
  selected: Endpoint | null;
  onSelect: (endpoint: Endpoint) => void;
}

/** HTTP方法颜色映射 */
const methodColors: Record<HttpMethod, { bg: string; text: string }> = {
  GET: { bg: 'bg-emerald-100', text: 'text-emerald-700' },
  POST: { bg: 'bg-blue-100', text: 'text-blue-700' },
  PUT: { bg: 'bg-amber-100', text: 'text-amber-700' },
  DELETE: { bg: 'bg-rose-100', text: 'text-rose-700' },
  PATCH: { bg: 'bg-violet-100', text: 'text-violet-700' }
};

export const EndpointList: React.FC<Props> = ({ endpoints, selected, onSelect }) => {
  // 按标签分组
  const groupedEndpoints = endpoints.reduce((acc, endpoint) => {
    const tags = endpoint.tags || ['其他'];
    tags.forEach(tag => {
      if (!acc[tag]) acc[tag] = [];
      acc[tag].push(endpoint);
    });
    return acc;
  }, {} as Record<string, Endpoint[]>);

  if (endpoints.length === 0) {
    return (
      <div className={styles.empty}>
        <span>📭</span>
        <p>暂无API端点</p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {Object.entries(groupedEndpoints).map(([tag, tagEndpoints]) => (
        <div key={tag} className={styles.group}>
          {/* 标签标题 */}
          <div className={styles.groupTitle}>
            {tag}
          </div>
          
          {/* 端点列表 */}
          <div className={styles.list}>
            {tagEndpoints.map(endpoint => {
              const isSelected = selected?.id === endpoint.id;
              const methodStyle = methodColors[endpoint.method];

              return (
                <div
                  key={endpoint.id}
                  onClick={() => onSelect(endpoint)}
                  className={`${styles.item} ${isSelected ? styles.itemSelected : ''}`}
                >
                  <div className={styles.itemHeader}>
                    <span className={`${styles.methodBadge} ${methodStyle.bg} ${methodStyle.text}`}>
                      {endpoint.method}
                    </span>
                    <span className={styles.itemName}>
                      {endpoint.name}
                    </span>
                  </div>

                  <div className={styles.itemPath}>
                    {endpoint.path}
                  </div>

                  {endpoint.description && (
                    <p className={styles.itemDesc}>
                      {endpoint.description}
                    </p>
                  )}

                  {isSelected && (
                    <div className={styles.selectedIndicator}>
                      ✓ 已选择
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
};
