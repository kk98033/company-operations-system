import { readdir, readFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const projectRoot = process.cwd()
const sourceRoot = resolve(projectRoot, 'src')
const errors = []

async function collectFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true })
  const nested = await Promise.all(entries.map(async (entry) => {
    const path = resolve(directory, entry.name)
    return entry.isDirectory() ? collectFiles(path) : [path]
  }))

  return nested.flat()
}

const sourceFiles = await collectFiles(sourceRoot)
const formalTsxFiles = sourceFiles.filter((file) => (
  file.endsWith('.tsx')
  && !file.endsWith('.test.tsx')
  && !file.endsWith('StylePreviewPage.tsx')
))

for (const file of formalTsxFiles) {
  const source = await readFile(file, 'utf8')
  const relative = file.slice(projectRoot.length + 1)

  if (/style\s*=\s*\{\{/.test(source)) {
    errors.push(`${relative}: 正式 UI 禁止 inline style，請使用共用 token／元件。`)
  }

  const classLiterals = [...source.matchAll(/className\s*=\s*["']([^"']+)["']/g)]
    .flatMap((match) => match[1].split(/\s+/))
  const hasLegacyClass = classLiterals.some((className) => (
    className === 'button'
    || className.startsWith('button--')
    || className === 'empty-state'
    || className === 'panel'
    || className.startsWith('panel--')
    || className === 'system-message'
    || className.startsWith('system-message__')
  ))
  if (hasLegacyClass) {
    errors.push(`${relative}: 發現已淘汰的舊版 UI class。`)
  }
}

const formalPages = sourceFiles.filter((file) => (
  /\/pages\/.*Page\.tsx$/.test(file)
  && !file.endsWith('StylePreviewPage.tsx')
  && !file.endsWith('.test.tsx')
))

for (const file of formalPages) {
  const source = await readFile(file, 'utf8')
  if (!source.includes("../ui/UiPatterns")) {
    errors.push(`${file.slice(projectRoot.length + 1)}: 正式頁面必須使用 ADR-010 共用 UI 元件。`)
  }
}

const formalCssFiles = sourceFiles.filter((file) => (
  file.endsWith('.css') && !file.endsWith('style-preview.css')
))

for (const file of formalCssFiles) {
  const source = await readFile(file, 'utf8')
  const relative = file.slice(projectRoot.length + 1)

  if (/backdrop-filter\s*:/.test(source)) {
    errors.push(`${relative}: 正式 UI 禁止玻璃模糊 backdrop-filter。`)
  }

  for (const line of source.split('\n')) {
    if (/box-shadow\s*:/.test(line) && !/box-shadow\s*:\s*(?:none|inset)/.test(line)) {
      errors.push(`${relative}: 正式 UI 禁止浮卡陰影：${line.trim()}`)
    }

    if (/border-radius\s*:/.test(line) && !/var\(--radius-|50%/.test(line)) {
      errors.push(`${relative}: 圓角必須使用 ADR-010 token：${line.trim()}`)
    }
  }
}

const patternsCss = await readFile(resolve(sourceRoot, 'styles/ui-patterns.css'), 'utf8')
const layoutCss = await readFile(resolve(sourceRoot, 'styles/layout.css'), 'utf8')
const requiredRules = [
  [patternsCss, '@media (max-width: 72rem)', '缺少桌面縮排 breakpoint'],
  [patternsCss, '@media (max-width: 58rem)', '缺少雙欄轉單欄 breakpoint'],
  [patternsCss, '@media (max-width: 40rem)', '缺少窄視窗 breakpoint'],
  [patternsCss, 'position: sticky', '資料表缺少 sticky 識別欄規則'],
  [layoutCss, '--sidebar-collapsed-width', '側欄缺少收合寬度規則'],
  [layoutCss, '@media (max-width: 46rem)', '殼層缺少窄視窗導覽規則'],
]

for (const [source, marker, message] of requiredRules) {
  if (!source.includes(marker)) errors.push(message)
}

if (errors.length > 0) {
  console.error('UI conformance check failed:')
  for (const error of errors) console.error(`- ${error}`)
  process.exitCode = 1
} else {
  console.log(`UI conformance check passed (${formalPages.length} formal pages, ${formalCssFiles.length} style files).`)
}
