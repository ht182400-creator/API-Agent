#!/usr/bin/env node
/**
 * 测试警告预算（Test Warning Budget）
 *
 * ## 为什么需要它
 *
 * 单元测试**只校验断言，不检查 stderr**。于是控制台里的 React / antd 警告可以年复一年堆着：
 * 每次跑测试照样"全绿"，却刷出几百行同样的警告 —— 既掩盖真实问题，也让人逐渐对输出麻木。
 *
 * 更危险的是 `not wrapped in act(...)` 这类：它意味着**状态更新发生在测试视野之外**，
 * 是"静默失效"类缺陷长期潜伏的温床。
 *
 * ## 它做什么
 *
 * 1. 跑一次 `vitest run`，把输出里的警告按**种类**归一化统计（同类合并，如不同的 act 警告算一种）；
 * 2. 与基线 `test-warnings-baseline.json` 比对：
 *    - 出现**基线之外的新种类** → 失败；
 *    - 某类数量超过 `基线 × (1 + 容差)` → 失败。
 *
 * ## 关键：**修好一类，就从基线里删掉它**
 *
 * `--update-baseline` 会把当前统计**整体重写**为基线。因此正确的使用节奏是：
 *
 *   1. 修掉某一类警告（例如把 `destroyOnClose` 全换成 `destroyOnHidden`）；
 *   2. 跑 `npm run test:budget -- --update-baseline` 重新生成基线；
 *   3. 该类从基线中**消失** → 今后它只要再出现一次，就会被判为"新增种类"而失败。
 *
 * 也就是说：**基线只减不增**，警告不会悄悄长回来。
 *
 * 用法：
 *   npm run test:budget                        # 检查（超标则退出码 1）
 *   npm run test:budget -- --update-baseline   # 修好一类后重建基线
 */
import { spawnSync } from 'node:child_process'
import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const root = resolve(join(here, '..', '..')) // <root>/api-platform/web
const baselinePath = join(root, 'test-warnings-baseline.json')

/**
 * 把一行原始输出归一化为"警告种类"。
 * ⚠️ 必须归一化：例如 `An update to DeveloperRecharge ...` 与 `An update to CSSMotion ...`
 *    其实是同一种（act 警告），不合并的话每次新增组件都会"多一种"。
 */
function classify(line) {
  if (/not wrapped in act\(/.test(line)) return 'act: update not wrapped in act'
  if (/\[antd: Modal\].*destroyOnClose/.test(line)) return 'antd: Modal.destroyOnClose deprecated'
  if (/\[antd: Card\].*bordered/.test(line)) return 'antd: Card.bordered deprecated'
  if (/\[antd: Card\].*bodyStyle/.test(line)) return 'antd: Card.bodyStyle deprecated'
  if (/\[antd: Spin\].*tip/.test(line)) return 'antd: Spin.tip misuse'
  if (/\[rc-collapse\]/.test(line)) return 'rc-collapse: children deprecated'
  if (/React Router Future Flag Warning/.test(line)) return 'react-router: future flag'
  if (/getComputedStyle\(\) method: with pseudo-elements/.test(line))
    return 'jsdom: getComputedStyle pseudo-elements'
  if (/same key/.test(line)) return 'react: duplicate keys'
  return null
}

const argv = process.argv.slice(2)
const updateBaseline = argv.includes('--update-baseline')
const passthrough = argv.filter((a) => !a.startsWith('--update'))

// ⚠️ 直接用 node 调 vitest 的 JS 入口，而不是 spawn `npx` / `npx.cmd`：
//    - Windows 下 `.cmd` 是批处理，脱离 shell 无法直接 spawn（实测零输出）；
//    - 用 shell:true 则会被 Node 20+ 判为 DEP0190 且有参数注入风险。
//    走 node <vitest.mjs> 是跨平台且最稳的方式。
const vitestBin = join(root, 'node_modules', 'vitest', 'vitest.mjs')
const res = spawnSync(process.execPath, [vitestBin, 'run', ...passthrough], {
  cwd: root,
  encoding: 'utf8',
  maxBuffer: 64 * 1024 * 1024,
})

if (res.error) {
  console.error(`[warn-budget] 无法启动 vitest（${vitestBin}）：${res.error.message}`)
  process.exit(1)
}

const output = `${res.stdout || ''}\n${res.stderr || ''}`

// ⚠️ 透传 vitest 的测试摘要 —— 只看警告统计无法确认"测试真的跑过且通过"（用户反馈缺失证据）。
if (res.status !== 0) {
  console.error(`[warn-budget] ❌ 单元测试未通过（vitest exit ${res.status}），先修测试再谈警告：`)
  const failLines = output
    .split('\n')
    .filter((l) => /FAIL|×|failed \(/.test(l))
    .slice(0, 20)
  if (failLines.length) console.error(failLines.join('\n'))
  process.exit(1)
}
for (const line of output.split('\n')) {
  if (/^\s*(Test Files|Tests|Duration)\s+/.test(line)) console.log(`[vitest] ${line.trim()}`)
}

const counts = {}
for (const line of output.split('\n')) {
  const kind = classify(line)
  if (kind) counts[kind] = (counts[kind] || 0) + 1
}

const sortedCounts = Object.fromEntries(Object.entries(counts).sort((a, b) => b[1] - a[1]))

if (updateBaseline) {
  writeFileSync(
    baselinePath,
    `${JSON.stringify({ updatedAt: new Date().toISOString(), counts: sortedCounts }, null, 2)}\n`,
    'utf8'
  )
  console.log(`[warn-budget] 基线已重建 -> ${baselinePath}`)
  for (const [k, v] of Object.entries(sortedCounts)) console.log(`  ${String(v).padStart(5)}  ${k}`)
  process.exit(0)
}

if (res.status !== 0) {
  console.error('[warn-budget] ❌ 单元测试未通过（先修测试）')
  process.exit(res.status ?? 1)
}

if (!existsSync(baselinePath)) {
  console.error(`[warn-budget] 缺少基线文件 ${baselinePath}，请先执行 --update-baseline`)
  process.exit(1)
}

const baseline = JSON.parse(readFileSync(baselinePath, 'utf8')).counts
const tolerance = Number(process.env.WARN_BUDGET_TOLERANCE ?? 0.3)

const problems = []
for (const [kind, n] of Object.entries(sortedCounts)) {
  const base = baseline[kind]
  if (base === undefined) {
    problems.push(`新增警告种类：${kind}（${n} 次）—— 基线中已不存在，说明修复被回退或引入了新问题`)
    continue
  }
  const limit = Math.ceil(base * (1 + tolerance))
  if (n > limit) problems.push(`${kind}：${n} 次 > 预算 ${limit}（基线 ${base}）`)
}

if (problems.length) {
  console.error('[warn-budget] ❌ 警告预算超标：')
  for (const p of problems) console.error(`  - ${p}`)
  console.error('\n如确有修复、需下调基线：npm run test:budget -- --update-baseline')
  process.exit(1)
}

console.log('[warn-budget] ✅ 警告在预算内')
for (const [k, v] of Object.entries(sortedCounts)) console.log(`  ${String(v).padStart(5)}  ${k}`)
