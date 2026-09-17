#!/usr/bin/env node
/**
 * 修复有效性验证（Mutation Check）—— 用来证明"测试不是虚拟的"
 *
 * ## 为什么需要它
 *
 * "用例通过"本身**不能证明**它真的在测目标行为：
 *   - 断言可能太弱（随便什么都过）；
 *   - 可能测错了对象（测的是 mock 而不是代码）；
 *   - 也可能压根没跑到那段代码。
 *
 * 因此用**变异检验**：把已修复的代码**改回缺陷形态**，再跑对应用例 ——
 *
 *   - 用例**变红** ✅ → 说明它确实锁住了这个行为（有效测试）；
 *   - 用例**仍然绿** ❌ → 说明它是"为了通过而通过"的**空测试**，必须重写。
 *
 * 每个变异结束后都会**自动还原源码**，并再跑一次确认恢复为绿。
 *
 * 用法：
 *   node scripts/dev/verify-fixes.mjs                # 全部变异
 *   node scripts/dev/verify-fixes.mjs --only FIX-2    # 只跑某一个
 *   node scripts/dev/verify-fixes.mjs --log out.json  # 另外输出 JSON 日志
 */
import { spawnSync } from 'node:child_process'
import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve, relative } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const root = resolve(join(here, '..', '..'))
const vitestBin = join(root, 'node_modules', 'vitest', 'vitest.mjs')

/**
 * 变异规则：`find` → `replace`，即"把修复改回缺陷"。
 * ⚠️ find 必须在目标文件中**唯一**（脚本会校验），否则拒绝执行，避免误伤。
 */
const MUTATIONS = [
  {
    id: 'FIX-1',
    title: '支付日志异常不再中断下单（sendPaymentLog）',
    // 两条都要跑：009 覆盖"同步抛错"，016 覆盖"返回 undefined"（原缺陷的真实形态）
    caseId: 'TC-FE-RECHARGE-009|TC-FE-RECHARGE-016',
    spec: 'src/pages/developer/Recharge.spec.tsx',
    file: 'src/pages/developer/recharge/rechargeLogger.ts',
    // ⚠️ 必须**同时**去掉两条防线：`try/catch` 与 `Promise.resolve` 互为冗余，
    //    只去掉其中一条时另一条仍能兜住（实测表现为"变异后仍通过"，容易被误判为空测试）。
    find: '  try {\n    Promise.resolve(paymentApi.clientLog(step, level, logData)).catch(() => {})\n  } catch {\n    /* 日志上报失败不影响业务 */\n  }',
    replace: '  paymentApi.clientLog(step, level, logData).catch(() => {})',
    note: '同时去掉 try/catch 与 Promise.resolve → 回到原始缺陷形态（返回 undefined 时 .catch 抛错并中断下单）',
  },
  {
    id: 'FIX-2',
    title: '取消订单后扫码轮询真正停止（qrcodePollingRef）',
    caseId: 'TC-FE-RECHARGE-013',
    spec: 'src/pages/developer/Recharge.spec.tsx',
    // ⚠️ P1-4 拆分（B3 轮）后 stopQrcodePolling 已搬到这里 —— 变异规则必须**跟着代码搬**：
    //    留在旧路径的话 find 命中 0 次，脚本会打印「❌ 跳过」但**退出码仍为 0**，
    //    很容易让人以为"还在验证"，实际这一条早就没验了。
    file: 'src/pages/developer/recharge/useQrcodePolling.ts',
    // ⚠️ 必须带函数头上下文唯一定位 stopQrcodePolling：
    //    "ref=false + setQrcodePolling(false)" 的组合在轮询成功/超时分支也各有一份
    //    （后续实现演化所致），不带上下文会命中多次而被安全跳过（实测）。
    find: '  const stopQrcodePolling = () => {\n    // ⚠️ 先把 ref 置 false（循环随即退出），再同步 UI 状态\n    qrcodePollingRef.current = false\n    setQrcodePolling(false)\n  }',
    replace: '  const stopQrcodePolling = () => {\n    // ⚠️ 先把 ref 置 false（循环随即退出），再同步 UI 状态\n    setQrcodePolling(false)\n  }',
    note: 'stopQrcodePolling 不再置 ref → 循环条件恒为 true（回到缺陷形态）',
  },
  {
    id: 'FIX-3',
    title: '组件卸载时统一清理轮询定时器',
    caseId: 'TC-FE-RECHARGE-014',
    spec: 'src/pages/developer/Recharge.spec.tsx',
    file: 'src/pages/developer/Recharge.tsx',
    find: '      qrcodePollingRef.current = false\n      if (paymentPollIntervalRef.current) {',
    replace: '      if (false && paymentPollIntervalRef.current) {',
    note: 'cleanup 不再置 ref → 卸载后轮询继续请求后端',
  },
  {
    id: 'FIX-4',
    title: '自定义模式赠送比例按百分比显示',
    caseId: 'TC-FE-RECHARGE-015',
    spec: 'src/pages/developer/Recharge.spec.tsx',
    file: 'src/pages/developer/recharge/components/PaymentSummary.tsx',
    find: '<Text type="warning">+{customRatio * 100}%</Text>',
    replace: '<Text type="warning">+{(customAmount || 0) * customRatio}%</Text>',
    note: '回到"拿金额冒充百分比"的缺陷形态',
  },
  {
    id: 'FIX-5',
    title: '账单首屏不再重复请求（fetchBills 只由一个 effect 驱动）',
    caseId: 'TC-FE-BILLING-001',
    spec: 'src/pages/developer/Billing.spec.tsx',
    file: 'src/pages/developer/Billing.tsx',
    find: '      setBalanceHistory(historyData)\n    } catch (error: any) {\n      showError(error, () => fetchData())',
    replace:
      '      setBalanceHistory(historyData)\n      fetchBills()\n    } catch (error: any) {\n      showError(error, () => fetchData())',
    note: '把 fetchBills() 放回 fetchData → 回到"挂载时 fetchData 与 effect 各拉一次账单"的缺陷形态（实测首屏 2 次）',
  },
  {
    id: 'FIX-6',
    title: '负数金额的符号在货币符号之前（-¥12.50 而不是 ¥-12.50）',
    caseId: 'TC-FE-BILLING-001',
    spec: 'src/pages/developer/Billing.spec.tsx',
    file: 'src/pages/developer/Billing.tsx',
    // ⚠️ 不带行首缩进，靠 `bill.` 前缀区分：移动端卡片那行是 `{bill.amount >= 0 ? ...}`
    find: "{amount >= 0 ? '+' : '-'}¥{Math.abs(amount).toFixed(2)}",
    replace: "{amount >= 0 ? '+' : ''}¥{amount.toFixed(2)}",
    note: '回到"符号夹在货币符号之后"的缺陷形态（负数渲染成 ¥-12.50）',
  },
  {
    id: 'FIX-7',
    title: '一次性明文密钥关闭后真正从 DOM 移除（destroyOnHidden）',
    caseId: 'TC-FE-KEYS-002',
    spec: 'src/pages/developer/Keys.spec.tsx',
    file: 'src/pages/developer/Keys.tsx',
    // ⚠️ `destroyOnHidden` 在文件中出现两次（创建成功弹窗 + 查看弹窗），必须带上注释上下文才能唯一命中；
    //    只写 `okText="我已保存"` 之后的 prop 也不行 —— 该 prop 所属 Modal 与查看弹窗结构相似。
    find: '        okText="我已保存"\n        // ⚠️ 一次性密钥（文案自己写着"仅显示一次"）：关闭后必须把内容**从 DOM 中真正移除**。\n        //    antd Modal 默认关闭只做隐藏挂载 → 明文会留在 DOM 里，与"仅显示一次"的语义不符。\n        destroyOnHidden',
    replace:
      '        okText="我已保存"\n        // ⚠️ 一次性密钥（文案自己写着"仅显示一次"）：关闭后必须把内容**从 DOM 中真正移除**。\n        //    antd Modal 默认关闭只做隐藏挂载 → 明文会留在 DOM 里，与"仅显示一次"的语义不符。\n        destroyOnHidden={false}',
    note: '回到"关闭只做隐藏挂载"的缺陷形态 → 点「我已保存」后明文仍留在 DOM 里，与"仅显示一次"冲突',
  },
]

const argv = process.argv.slice(2)
const onlyIdx = argv.indexOf('--only')
const only = onlyIdx >= 0 ? argv[onlyIdx + 1] : null
const logIdx = argv.indexOf('--log')
const logPath = logIdx >= 0 ? argv[logIdx + 1] : null

const abs = (p) => join(root, p)
const enc = { encoding: 'utf8' }

function readFile(p) {
  return readFileSync(abs(p), 'utf8')
}
function writeFile(p, content) {
  writeFileSync(abs(p), content, 'utf8')
}

/**
 * ⚠️ 源文件在 Windows 上是 CRLF，而变异规则里写的是 `\n` —— 直接字符串匹配会**匹配不到**
 *    （实测表现为"find 出现 0 次"）。故统一转成正则，并把 `\n` 放宽为 `\r?\n`。
 *    同时替换串里的换行要还原成文件实际的换行，避免写入后破坏 eol。
 */
function toRegExp(find) {
  return new RegExp(find.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/\n/g, '\\r?\\n'), 'g')
}
function detectNewline(text) {
  return text.includes('\r\n') ? '\r\n' : '\n'
}

function runCase(spec, caseId) {
  const res = spawnSync(process.execPath, [vitestBin, 'run', spec, '-t', caseId], {
    cwd: root,
    encoding: 'utf8',
    maxBuffer: 64 * 1024 * 1024,
  })
  const output = `${res.stdout || ''}\n${res.stderr || ''}`
  return {
    ok: res.status === 0,
    status: res.status,
    // 提取关键行，便于留痕
    summary: (output.match(/Tests\s+.*/) || ['(无摘要)'])[0],
    firstError: (output.match(/(?:AssertionError|TestingLibraryElementError|Error:)[^\r\n]*/) || [null])[0],
  }
}

const results = []
const list = only ? MUTATIONS.filter((m) => m.id === only) : MUTATIONS

if (!list.length) {
  console.error(`[verify-fixes] 未找到变异：${only}`)
  process.exit(1)
}

console.log('='.repeat(78))
console.log('修复有效性验证（变异检验）')
console.log('判定标准：把修复改回缺陷后，用例必须变红；否则该用例是空测试。')
console.log('='.repeat(78))

for (const m of list) {
  const relFile = relative(root, abs(m.file))
  const original = readFile(m.file)
  const nl = detectNewline(original)
  const findRe = toRegExp(m.find)
  const replaceStr = m.replace.replace(/\n/g, nl)
  const occurrences = (original.match(findRe) || []).length

  console.log(`\n[${m.id}] ${m.title}`)
  console.log(`  用例    : ${m.caseId}`)
  console.log(`  变异文件: ${relFile}`)
  console.log(`  变异说明: ${m.note}`)

  if (occurrences !== 1) {
    console.log(`  ❌ 跳过：find 在文件中出现 ${occurrences} 次（要求恰好 1 次，避免误伤）`)
    results.push({ ...m, verdict: 'SKIPPED', reason: `find 出现 ${occurrences} 次` })
    continue
  }

  // 1) 应用变异（只替换第一处，保持可控）
  writeFile(m.file, original.replace(findRe, () => replaceStr))

  // 2) 期望：用例失败
  const mutated = runCase(m.spec, m.caseId)

  // 3) 还原
  writeFile(m.file, original)

  // 4) 还原后：期望通过
  const restored = runCase(m.spec, m.caseId)

  const caught = !mutated.ok
  const verdict = caught ? (restored.ok ? 'PASS' : 'UNSTABLE') : 'FAIL(空测试)'

  console.log(`  变异后  : ${mutated.ok ? '🟢 仍然通过' : '🔴 失败（符合预期）'} — ${mutated.summary}`)
  if (mutated.firstError) console.log(`            首个错误: ${mutated.firstError.slice(0, 120)}`)
  console.log(`  还原后  : ${restored.ok ? '🟢 通过' : '🔴 失败'} — ${restored.summary}`)
  console.log(`  结论    : ${verdict === 'PASS' ? '✅ 用例有效（确实锁住了该行为）' : verdict}`)

  results.push({
    id: m.id,
    title: m.title,
    caseId: m.caseId,
    file: relFile,
    note: m.note,
    mutatedRun: { passed: mutated.ok, summary: mutated.summary, firstError: mutated.firstError },
    restoredRun: { passed: restored.ok, summary: restored.summary },
    verdict,
  })
}

console.log('\n' + '='.repeat(78))
const passed = results.filter((r) => r.verdict === 'PASS').length
const failed = results.filter((r) => r.verdict === 'FAIL(空测试)').length
console.log(`汇总：${passed} 个有效 / ${failed} 个空测试 / ${results.length - passed - failed} 个其它`)
console.log('='.repeat(78))

if (logPath) {
  writeFileSync(
    logPath,
    `${JSON.stringify({ generatedAt: new Date().toISOString(), root, results }, null, 2)}\n`,
    'utf8'
  )
  console.log(`JSON 日志已写入: ${logPath}`)
}

process.exit(failed > 0 ? 1 : 0)
