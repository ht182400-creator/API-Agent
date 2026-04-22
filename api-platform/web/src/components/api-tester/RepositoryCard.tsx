/**
 * 仓库卡片组件
 * @description 显示单个仓库信息
 */

import React from 'react';
import { Repository } from '../../types/api-tester';
import styles from './RepositoryCard.module.css';

interface Props {
  repository: Repository;
  selected: boolean;
  onClick: () => void;
}

/** 图标映射表 */
const iconMap: Record<string, string> = {
  'cloud': '☁️',
  'car': '🚚',
  'message': '💬',
  'credit-card': '💳',
  'scan': '📷',
  'map': '🗺️',
  'mail': '📧',
  'default': '📦'
};

/** 获取图标 */
const getIcon = (icon: string): string => iconMap[icon] || iconMap['default'];

export const RepositoryCard: React.FC<Props> = ({ repository, selected, onClick }) => {
  const isThirdParty = repository.category === 'third_party';

  return (
    <div
      onClick={onClick}
      className={`${styles.card} ${selected ? styles.cardSelected : ''}`}
    >
      <div className={styles.content}>
        {/* 图标 */}
        <div className={styles.iconWrapper}>
          <span className={styles.icon}>{getIcon(repository.icon)}</span>
        </div>

        {/* 信息 */}
        <div className={styles.info}>
          <div className={styles.nameRow}>
            <h3 className={styles.name}>{repository.name}</h3>
            {isThirdParty && (
              <span className={styles.thirdPartyBadge}>第三方</span>
            )}
          </div>
          <p className={styles.description}>{repository.description}</p>
          <div className={styles.meta}>
            <span className={styles.metaItem}>
              <span>🔗</span>
              {repository.endpoints.length} 接口
            </span>
            {repository.version && (
              <span className={styles.metaItem}>
                <span>v</span>
                {repository.version}
              </span>
            )}
          </div>
        </div>

        {/* 选中指示器 */}
        {selected && (
          <div className={styles.checkmark}>
            <span>✓</span>
          </div>
        )}
      </div>
    </div>
  );
};
