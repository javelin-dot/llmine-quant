import { useSecurity } from '../../contexts/SecurityContext'

export default function AIPermissionMatrix() {
  const data = useSecurity()
  const categories = data.aiPermissions
  const totalAllowed = categories.reduce((sum, c) => sum + c.allowed.length, 0)
  const totalBlocked = categories.reduce((sum, c) => sum + c.blocked.length, 0)

  return (
    <div className="security-perms">
      <div className="sp-head">
        <div>
          <h4 className="sp-title">AI 权限矩阵 · License Gate</h4>
          <span className="sp-sub">
            {totalAllowed} 允许 · <em className="warn">{totalBlocked}</em> 物理禁止
          </span>
        </div>
        <button className="sp-btn">查看 Tool Registry</button>
      </div>

      <div className="sp-grid">
        {categories.map((c, i) => (
          <section className="sp-cat" key={i}>
            <header className="sp-cat-head">
              <h5>{c.category}</h5>
              <div className="sp-cat-meta">
                <span className="sp-cat-allowed">{c.allowed.length} 允许</span>
                <span className="sp-cat-blocked">{c.blocked.length} 禁止</span>
              </div>
            </header>

            <div className="sp-cat-body">
              <div className="sp-col allowed">
                <h6><i />允许调用</h6>
                <ul>
                  {c.allowed.map((p, j) => (
                    <li key={j}>
                      <code>{p.api}</code>
                      <span>{p.desc}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="sp-col blocked">
                <h6><i />物理禁止</h6>
                <ul>
                  {c.blocked.map((p, j) => (
                    <li key={j}>
                      <code>{p.api}</code>
                      <span>{p.desc}</span>
                      <em>因: {p.reason}</em>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </section>
        ))}
      </div>
    </div>
  )
}
