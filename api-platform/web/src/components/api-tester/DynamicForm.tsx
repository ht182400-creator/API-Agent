/**
 * 动态表单组件
 * @description 根据参数配置自动渲染表单
 */

import React from 'react';
import { Parameter } from '../../types/api-tester';
import styles from './DynamicForm.module.css';

interface Props {
  params: Parameter[];
  values: Record<string, any>;
  onChange: (name: string, value: any) => void;
  disabled?: boolean;
}

export const DynamicForm: React.FC<Props> = ({ params, values, onChange, disabled = false }) => {
  // 按位置分组参数
  const queryParams = params.filter(p => p.in === 'query');
  const pathParams = params.filter(p => p.in === 'path');
  const headerParams = params.filter(p => p.in === 'header');
  const bodyParams = params.filter(p => p.in === 'body');

  /**
   * 渲染单个字段
   */
  const renderField = (param: Parameter) => {
    const value = values[param.name] ?? param.defaultValue ?? '';
    const hasError = param.required && !value && value !== 0;

    const inputClass = `${styles.input} ${disabled ? styles.inputDisabled : ''} ${hasError ? styles.inputError : ''}`;

    switch (param.type) {
      case 'select':
        return (
          <select
            value={value}
            onChange={(e) => onChange(param.name, e.target.value)}
            disabled={disabled}
            className={inputClass}
          >
            <option value="">请选择</option>
            {param.options?.map(opt => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        );

      case 'number':
        return (
          <input
            type="number"
            value={value}
            placeholder={param.placeholder || param.description}
            onChange={(e) => onChange(param.name, e.target.value ? Number(e.target.value) : '')}
            disabled={disabled}
            min={param.validation?.min}
            max={param.validation?.max}
            className={inputClass}
          />
        );

      case 'boolean':
        return (
          <label className={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={!!value}
              onChange={(e) => onChange(param.name, e.target.checked)}
              disabled={disabled}
              className={styles.checkbox}
            />
            <span className={styles.checkboxText}>{param.description}</span>
          </label>
        );

      case 'string':
      default:
        return (
          <input
            type="text"
            value={value}
            placeholder={param.placeholder || param.description}
            onChange={(e) => onChange(param.name, e.target.value)}
            disabled={disabled}
            minLength={param.validation?.minLength}
            maxLength={param.validation?.maxLength}
            className={inputClass}
          />
        );
    }
  };

  /**
   * 渲染参数组
   */
  const renderParamGroup = (groupParams: Parameter[], title: string, icon: string) => {
    if (groupParams.length === 0) return null;

    return (
      <div className={styles.paramGroup}>
        <h4 className={styles.groupTitle}>
          <span>{icon}</span>
          <span>{title}</span>
          <span className={styles.groupCount}>({groupParams.length})</span>
        </h4>
        <div className={styles.groupContent}>
          {groupParams.map(param => (
            <div key={param.name} className={styles.fieldWrapper}>
              <label className={styles.fieldLabel}>
                <span className={styles.fieldName}>{param.name}</span>
                {param.required && <span className={styles.required}>*</span>}
              </label>
              {renderField(param)}
              {param.description && (
                <p className={styles.fieldDesc}>{param.description}</p>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  // 检查是否有任何参数
  const hasAnyParams = queryParams.length > 0 || pathParams.length > 0 || 
                       headerParams.length > 0 || bodyParams.length > 0;

  if (!hasAnyParams) {
    return (
      <div className={styles.empty}>
        <span>🎯</span>
        <p>此接口无需参数</p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {renderParamGroup(queryParams, '查询参数', '🔍')}
      {renderParamGroup(pathParams, '路径参数', '📁')}
      {renderParamGroup(headerParams, '请求头', '📋')}
      {renderParamGroup(bodyParams, '请求体', '📝')}
    </div>
  );
};
