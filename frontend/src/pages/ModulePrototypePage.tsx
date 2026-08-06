import { Link } from '@tanstack/react-router'

import { workflowModules, type WorkflowModule } from '../app/workflowModules'
import { DefinitionGrid, PageHeader, Section, StatusLabel } from '../ui/UiPatterns'

export function ModulePrototypePage({ module }: { module: WorkflowModule }) {
  const moduleIndex = workflowModules.findIndex((candidate) => candidate.id === module.id)
  const previousModule = workflowModules[moduleIndex - 1]
  const nextModule = workflowModules[moduleIndex + 1]

  return (
    <div className="ui-pattern-stack module-prototype">
      <PageHeader
        eyebrow={`${module.phase.toUpperCase()} / ROUTE PROTOTYPE`}
        title={module.label}
        description={module.description}
      />

      <div className="module-prototype__notice" role="status">
        <StatusLabel tone="warning">Phase 0 假資料原型</StatusLabel>
        <span>目前只驗證頁面名稱、模組責任與流程導覽；尚未連接 API、資料庫或公司正式資料。</span>
      </div>

      <div className="ui-two-column">
        <Section title="此模組未來負責" description="正式功能將依對應 Phase 小切片逐步實作。">
          <ul className="check-list">
            {module.responsibilities.map((responsibility) => <li key={responsibility}>{responsibility}</li>)}
          </ul>
        </Section>
        <Section title="流程交接" description="這裡只描述資料流向，不預先決定尚未簽認的業務規則。">
          <DefinitionGrid
            items={[
              { label: '預定階段', value: module.phase },
              { label: '主要輸入', value: module.input },
              { label: '主要輸出', value: module.output },
              { label: '需求編號', value: module.requirementIds.join('、') },
            ]}
          />
        </Section>
      </div>

      <Section title="公司主流程" description="可由客戶開始，依序檢查到收款；報價為可選分支。">
        <nav className="module-flow" aria-label="公司主流程">
          {workflowModules.map((workflowModule, index) => (
            <Link
              activeProps={{ className: 'is-active' }}
              className="module-flow__link"
              key={workflowModule.id}
              to={workflowModule.path}
            >
              <span>{index + 1}</span>
              <strong>{workflowModule.label}</strong>
            </Link>
          ))}
        </nav>
      </Section>

      <nav className="module-adjacent" aria-label="相鄰流程">
        {previousModule ? (
          <Link className="ui-button ui-button--secondary" to={previousModule.path}>上一站：{previousModule.label}</Link>
        ) : <span />}
        {nextModule ? (
          <Link className="ui-button ui-button--primary" to={nextModule.path}>下一站：{nextModule.label}</Link>
        ) : <Link className="ui-button ui-button--secondary" to="/">回到首頁</Link>}
      </nav>
    </div>
  )
}
