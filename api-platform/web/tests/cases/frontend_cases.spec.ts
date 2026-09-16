/**
 * 用例库（frontend_cases.json）自检
 *
 * 为什么需要它：
 *   该 JSON 是"前端覆盖全景的唯一清单"，但**此前没有任何测试消费它** ——
 *   实测它曾因两处未转义英文双引号而整体损坏（`require()` 直接 SyntaxError），
 *   却没有任何警报。把它纳入测试后：JSON 损坏 / 结构漂移 / 登记与现实脱节，
 *   都会在 `npm run test:unit` 里直接变红。
 */
import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs'
import { join, dirname, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const webRoot = join(here, '..', '..')
const raw = readFileSync(join(here, 'frontend_cases.json'), 'utf8')
const doc = JSON.parse(raw)

interface CaseEntry {
  id: string
  name: string
  status?: string
}
interface Suite {
  id: string
  level?: string
  file?: string
  status?: string
  specFile?: string
  cases?: CaseEntry[]
}

const suites: Suite[] = doc.suites ?? []

/** 递归收集 src 下的 *.spec.ts / *.spec.tsx（与 vitest 默认 include 对齐） */
function collectSpecFiles(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name)
    if (statSync(full).isDirectory()) collectSpecFiles(full, out)
    else if (/\.spec\.tsx?$/.test(name)) out.push(full)
  }
  return out
}

describe('用例库 frontend_cases.json 自检', () => {
  it('TC-FE-CASES-001: JSON 必须可解析（曾因未转义引号损坏且无任何警报）', () => {
    expect(() => JSON.parse(raw)).not.toThrow()
  })

  it('TC-FE-CASES-002: 顶层结构完整（meta / suites / knownDefects，suites 非空）', () => {
    expect(doc.meta).toBeTruthy()
    expect(Array.isArray(doc.suites)).toBe(true)
    expect(suites.length).toBeGreaterThan(0)
    expect(Array.isArray(doc.knownDefects)).toBe(true)
  })

  it('TC-FE-CASES-003: 每个 suite 的必填字段齐全、status 合法', () => {
    const LEGAL = new Set(['covered', 'partial', 'planned', 'skipped'])
    for (const s of suites) {
      expect(s.id, 'suite 缺 id').toBeTruthy()
      // ⚠️ file 允许缺失：聚合型 suite（如 FE-ADMIN-MISC 覆盖 21 个页面骨架）没有单一被测文件；
      //    一旦给了 file，就由 CASES-005 校验其真实存在。
      expect(LEGAL.has(s.status ?? ''), `suite ${s.id} 非法 status: ${s.status}`).toBe(true)
    }
  })

  it('TC-FE-CASES-004: 全库用例 id 唯一（跨 suite 不得重号）', () => {
    const seen = new Map<string, number>()
    for (const s of suites) {
      for (const c of s.cases ?? []) {
        seen.set(c.id, (seen.get(c.id) ?? 0) + 1)
      }
    }
    const dupes = [...seen.entries()].filter(([, n]) => n > 1)
    expect(dupes, `重复用例 id: ${dupes.map(([id]) => id).join(', ')}`).toEqual([])
  })

  it('TC-FE-CASES-005: suite.file 指向的被测文件必须真实存在（防止改名后清单失真）', () => {
    const missing = suites
      .map((s) => s.file ?? '')
      .filter((f) => f.length > 0 && !existsSync(join(webRoot, f)))
    expect(missing, `清单中不存在于磁盘的被测文件: ${missing.join(', ')}`).toEqual([])
  })

  it('TC-FE-CASES-006: covered/partial 的 specFile 必须存在（支持逗号分隔多个）', () => {
    const missing: string[] = []
    for (const s of suites) {
      if ((s.status === 'covered' || s.status === 'partial') && s.specFile) {
        // ⚠️ 一个 suite 可由多个 spec 覆盖（如 FE-SHARED-UI：App.spec + SharedComponents.spec）
        for (const f of s.specFile.split(',').map((x) => x.trim())) {
          if (f && !existsSync(join(webRoot, f))) missing.push(`${s.id}: ${f}`)
        }
      }
    }
    expect(missing, `登记了 specFile 但文件不存在: ${missing.join(', ')}`).toEqual([])
  })

  it('TC-FE-CASES-007: meta.stats.specFiles 与磁盘上的 spec 数一致（登记与现实同步）', () => {
    const stats = doc.meta?.stats
    expect(stats?.specFiles).toBeTruthy()
    const actual = collectSpecFiles(join(webRoot, 'src')).length
    expect(
      stats.specFiles,
      `用例库登记 ${stats.specFiles} 个 spec，磁盘实际 ${actual} 个 —— ` +
        `新增/删除 spec 后请同步 meta.stats（文件: ${collectSpecFiles(join(webRoot, 'src')).map((f) => relative(join(webRoot, 'src'), f)).join(', ')}）`
    ).toBe(actual)
  })
})
