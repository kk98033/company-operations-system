import { readdir, readFile } from 'node:fs/promises'
import { basename, resolve } from 'node:path'

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
const formalUiTsxFiles = formalTsxFiles.filter((file) => file.includes('/src/ui/'))

for (const file of formalTsxFiles) {
  const source = await readFile(file, 'utf8')
  const relative = file.slice(projectRoot.length + 1)

  if (/style\s*=\s*\{\{/.test(source)) {
    errors.push(`${relative}: 正式 UI 禁止 inline style，請使用共用 token／元件。`)
  }

  if (/tabIndex\s*=\s*\{\s*[1-9]/.test(source)) {
    errors.push(`${relative}: 禁止正數 tabIndex，鍵盤順序必須跟隨 DOM 與視覺流程。`)
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

for (const file of formalUiTsxFiles) {
  const source = await readFile(file, 'utf8')
  const lineCount = source.trimEnd().split('\n').length
  if (lineCount > 200) {
    errors.push(`${file.slice(projectRoot.length + 1)}: 正式共用 React module 不可超過 200 行，目前 ${lineCount} 行。`)
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
  if (/\.\.\/ui\/(?:FormPatterns|InformationPatterns|PagePatterns|SystemState)/.test(source)) {
    errors.push(`${file.slice(projectRoot.length + 1)}: 正式頁面不得繞過 UiPatterns public boundary。`)
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

  if (file.includes('/src/styles/ui-')) {
    const lineCount = source.trimEnd().split('\n').length
    if (lineCount > 500) {
      errors.push(`${relative}: 正式共用 UI style module 不可超過 500 行，目前 ${lineCount} 行。`)
    }
  }
}

const uiStyleManifest = [
  ['ui-page-patterns.css', ['@media (max-width: 72rem)', '@media (max-width: 58rem)', '@media (max-width: 40rem)']],
  ['ui-form-patterns.css', ['@media (max-width: 72rem)', '@media (max-width: 40rem)']],
  ['ui-information-patterns.css', ['@media (max-width: 72rem)', '@media (max-width: 40rem)']],
  ['ui-system-state.css', ['@media (max-width: 40rem)']],
  ['ui-pattern-gallery.css', ['@media (max-width: 40rem)']],
]
const discoveredUiStyleNames = formalCssFiles
  .filter((file) => file.includes('/src/styles/ui-'))
  .map((file) => basename(file))
  .sort()
const expectedUiStyleNames = uiStyleManifest.map(([fileName]) => fileName).sort()

if (JSON.stringify(discoveredUiStyleNames) !== JSON.stringify(expectedUiStyleNames)) {
  errors.push(`正式共用 UI style manifest 不一致：預期 ${expectedUiStyleNames.join(', ')}；實際 ${discoveredUiStyleNames.join(', ')}。`)
}

for (const [fileName, requiredMarkers] of uiStyleManifest) {
  const source = await readFile(resolve(sourceRoot, 'styles', fileName), 'utf8')
  for (const marker of requiredMarkers) {
    if (!source.includes(marker)) {
      errors.push(`${fileName}: 缺少責任內的 RWD／sticky 基準 ${marker}。`)
    }
  }
}

const informationCss = await readFile(resolve(sourceRoot, 'styles/ui-information-patterns.css'), 'utf8')
const stickyIdentityRule = /\.ui-data-table \.ui-data-table__sticky\s*\{[^}]*position:\s*sticky;[^}]*left:\s*0;/s
if (!stickyIdentityRule.test(informationCss)) {
  errors.push('ui-information-patterns.css: 第一識別欄必須使用指定 sticky selector 與 left: 0。')
}

const mainSource = await readFile(resolve(sourceRoot, 'main.tsx'), 'utf8')
const styleImportOrder = [
  'tokens.css',
  'global.css',
  'layout.css',
  ...uiStyleManifest.map(([fileName]) => fileName),
  'style-preview.css',
]
let previousImportIndex = -1
for (const fileName of styleImportOrder) {
  const importIndex = mainSource.indexOf(`./styles/${fileName}`)
  const isDuplicated = importIndex !== mainSource.lastIndexOf(`./styles/${fileName}`)
  if (importIndex === -1 || importIndex <= previousImportIndex || isDuplicated) {
    errors.push(`main.tsx: 完整 style cascade import 缺少、重複或順序錯誤：${fileName}。`)
  }
  previousImportIndex = importIndex
}

const layoutCss = await readFile(resolve(sourceRoot, 'styles/layout.css'), 'utf8')
const globalCss = await readFile(resolve(sourceRoot, 'styles/global.css'), 'utf8')
const appLayoutSource = await readFile(resolve(sourceRoot, 'app/AppLayout.tsx'), 'utf8')
const requiredRules = [
  [layoutCss, '--sidebar-collapsed-width', '側欄缺少收合寬度規則'],
  [layoutCss, '@media (max-width: 46rem)', '殼層缺少窄視窗導覽規則'],
  [layoutCss, '@media (prefers-reduced-motion: reduce)', '殼層動畫缺少 reduced-motion 降級規則'],
  [globalCss, ':focus-visible', '全域樣式缺少鍵盤可見焦點規則'],
  [globalCss, '.skip-link:focus', '全域樣式缺少跳到主要內容的焦點顯示規則'],
  [appLayoutSource, 'href="#main-content"', 'AppLayout 缺少跳到主要內容連結'],
  [appLayoutSource, 'id="main-content"', 'AppLayout 缺少主要內容焦點目標'],
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
