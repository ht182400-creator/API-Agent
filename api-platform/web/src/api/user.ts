/**
 * 用户 API - 用户升级与试用功能
 */

import { api } from './client'

/**
 * 用户状态
 */
export interface UserStatus {
  user_id: string
  role: string
  user_type: string
  permissions: string[]
  balance: number
  trial_claimed: boolean
  trial_amount_claimed: number
  is_developer: boolean
}

/**
 * 升级响应
 */
export interface UpgradeResponse {
  role: string
  user_type: string
  permissions: string[]
  message: string
}

/**
 * 领取试用响应
 */
export interface ClaimTrialResponse {
  claimed: boolean
  amount: number
  new_balance: number
  message: string
}

/**
 * 用户 API
 */
export const userApi = {
  /**
   * 获取当前用户状态
   */
  getStatus: () => {
    return api.get<UserStatus>('/user/status')
  },

  /**
   * 升级为开发者
   */
  upgrade: () => {
    return api.post<UpgradeResponse>('/user/upgrade')
  },

  /**
   * 领取试用金额
   */
  claimTrial: () => {
    return api.post<ClaimTrialResponse>('/user/claim-trial')
  },
}
