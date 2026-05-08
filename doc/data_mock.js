/**
 * QuantOS AI 高保真原型 — 模拟数据集
 * 与真实系统字段对齐的 JSON 形态，便于后端/API 一比一替换。
 * 在 HTML 中通过 <script src="data_mock.js"> 加载后可用 window.QuantOSMock
 */
(function (global) {
  'use strict';

  global.QuantOSMock = {
    meta: {
      product: 'QuantOS AI',
      subtitle: 'Agentic Trading Platform',
      schemaVersion: '1.1.0',
      generatedAt: '2026-05-09T08:00:00+08:00',
      locale: 'zh-CN'
    },

    system: {
      healthScore: 98.7,
      healthStatusLabel: 'LIVE',
      healthBarHeightsPx: [22, 35, 30, 44, 28, 48, 40, 37, 45, 31, 42, 47],
      autopilot: true,
      riskGateLabel: 'Risk Gate A-'
    },

    modals: {
      global: {
        title: '全局系统概览',
        body: 'AI Autopilot 正常运行。当前 42 个策略版本、318 个 Agent 任务、7 个待审批动作。解释血缘、数据许可、实盘交易均受 Policy Engine、Risk Agent 与 Human Approval Center 约束。',
        primary: '知道了'
      },
      kill: {
        title: '全局 Kill Switch',
        body: '触发后将立即暂停所有新开仓，仅允许减仓与撤单。不可恢复熔断恢复必须经过风控员审批。此原型仅展示交互，不会执行真实交易。',
        primary: '模拟触发熔断'
      },
      create: {
        title: '启动 AI 策略任务',
        body: 'Command Center 将自动拆解任务：选择数据源、清洗数据、生成候选策略、静态安全检查、批量回测、样本外验证、风控评估、生成模拟盘部署计划。涉及实盘交易时会单独请求确认。',
        primary: '启动任务'
      },
      autopilot: {
        title: 'Autopilot 配置',
        body: '建议默认开放 L0-L4 权限：读取、生成草稿、运行回测、模拟盘自动执行、生成实盘提案。L5 实盘自动执行默认关闭，只能通过预授权限额开启。',
        primary: '保存配置'
      },
      approve: {
        title: '交易审批确认',
        body: '该订单已通过账户级、组合级、策略级三层风控。提交后 Execution Agent 将使用幂等键发送订单，并持续监控成交、部分成交、撤单和回报异常。',
        primary: '批准执行'
      },
      pause: {
        title: '暂停策略确认',
        body: '由于行情源冲突和置信度不足，系统建议暂停 SOL 策略新开仓。该动作不涉及实盘买卖，仅冻结新信号并保留已有持仓处理规则。',
        primary: '暂停策略'
      }
    },

    dashboard: {
      liveAgentsLabel: '7 Agents Active',
      kpis: [
        { key: 'strategies', label: 'Active Strategies', value: '42', trend: '+8 本周新增', trendClass: '' },
        { key: 'tasks', label: 'Agent Tasks', value: '318', trend: '91% 自动闭环', trendClass: '' },
        { key: 'pending', label: 'Pending Approvals', value: '7', trend: '3 个实盘订单', trendClass: 'warn' },
        { key: 'risk', label: 'Capital Risk', value: 'A-', trend: '风控稳定', trendClass: '' }
      ],
      agents: [
        { avatar: '研', name: 'Research Agent', detail: '正在扫描 BTC/ETH/SOL 市场结构', metric: '97%' },
        { avatar: '策', name: 'Strategy Agent', detail: '生成 ATR 趋势突破 v19 草案', metric: '84%' },
        { avatar: '测', name: 'Backtest Agent', detail: '样本外验证 2024-2026 数据', metric: 'RUN' },
        { avatar: '险', name: 'Risk Agent', detail: '拦截 1 个高杠杆调仓提案', metric: 'A-' },
        { avatar: '执', name: 'Execution Agent', detail: '等待 3 个实盘订单确认', metric: '3' }
      ],
      timeline: [
        { title: 'Risk Agent 拒绝扩大 ETH 仓位', desc: '原因：样本外收益低于样本内 57%，未达到自动升级阈值。' },
        { title: 'Backtest Agent 完成 64 组参数搜索', desc: 'ATR 趋势突破 v19 在滑点敏感测试中表现稳定。' },
        { title: 'Execution Agent 生成交易草案', desc: '建议 BTC 加仓 2%，ETH 减仓 5%，等待确认。' },
        { title: 'Data Agent 切换备用行情源', desc: '主源延迟超过 2200ms，已切换至备用 WebSocket。' }
      ],
      chart: {
        viewBox: '0 0 900 300',
        linePath:
          'M0,230 C70,215 105,220 150,198 C210,166 242,180 300,148 C360,114 398,138 450,110 C520,74 565,92 620,62 C680,35 742,60 790,40 C836,22 868,30 900,18',
        areaPath:
          'M0,230 C70,215 105,220 150,198 C210,166 242,180 300,148 C360,114 398,138 450,110 C520,74 565,92 620,62 C680,35 742,60 790,40 C836,22 868,30 900,18 L900,300 L0,300 Z'
      },
      chartSubtitle: 'AI managed · paper + live',
      timelineSubtitle: '最近 18 分钟'
    },

    strategy: {
      nlPrompt:
        '创建一个偏激进的 BTC/ETH 趋势策略，目标年化 30%，最大回撤不超过 20%，先跑过去 3 年数据，自动做样本外验证和模拟盘部署计划。',
      previewText:
        'Strategy Agent 已生成 5 个候选版本，其中 2 个通过静态安全检查，1 个通过样本外风控门槛。',
      previewMetrics: [
        { label: 'Best Candidate', value: 'ATR-v19' },
        { label: 'Risk Score', value: 'A-' },
        { label: 'Max DD', value: '16.8%' },
        { label: 'Confidence', value: '0.84' }
      ],
      kanban: [
        {
          lane: 'Draft',
          tickets: [
            { title: 'MACD-Vol-v04', desc: 'AI 生成，等待静态检查。', tag: { text: 'Strategy Agent', variant: 'purple' } },
            { title: 'Grid-Neutral-v11', desc: '参数空间过大，建议收敛。', tag: { text: 'Needs Review', variant: 'yellow' } }
          ]
        },
        {
          lane: 'Backtesting',
          tickets: [
            { title: 'ATR-Trend-v19', desc: '64 组参数，进行滑点敏感性测试。', tag: { text: 'Running', variant: 'green' } },
            { title: 'Donchian-v07', desc: '样本外验证中。', tag: { text: 'Walk Forward', variant: '' } }
          ]
        },
        {
          lane: 'Paper Trading',
          tickets: [
            { title: 'BTC-MA-v12', desc: '模拟盘运行 21 天，等待实盘候选评估。', tag: { text: 'Stable', variant: 'green' } },
            { title: 'ETH-RSI-v05', desc: '最近 7 日表现下降，AI 正在生成 v06。', tag: { text: 'Degrading', variant: 'yellow' } }
          ]
        },
        {
          lane: 'Live Candidate',
          tickets: [
            { title: 'ATR-Trend-v18', desc: '风险评分 A-，等待交易员确认小额实盘。', tag: { text: 'Approval', variant: 'red' } }
          ]
        }
      ]
    },

    backtest: {
      kpis: [
        { label: 'Best Annualized', value: '31.8%', trend: '样本外 24.6%', trendClass: '' },
        { label: 'Max Drawdown', value: '16.8%', trend: '低于 20% 约束', trendClass: 'warn' },
        { label: 'Sharpe', value: '1.74', trend: '稳定', trendClass: '' },
        { label: 'Overfit Risk', value: '中', trend: '需模拟盘验证', trendClass: 'warn' }
      ],
      comparison: [
        { strategy: 'ATR-Trend-v19', annualized: '31.8%', maxDd: '16.8%', oosTag: { text: '通过', variant: 'green' }, overfit: '中', action: '报告', actionKind: 'report' },
        { strategy: 'Donchian-v07', annualized: '28.1%', maxDd: '18.4%', oosTag: { text: '通过', variant: 'green' }, overfit: '低', action: '报告', actionKind: 'report' },
        { strategy: 'MACD-Vol-v04', annualized: '42.7%', maxDd: '34.2%', oosTag: { text: '失败', variant: 'red' }, overfit: '高', action: '解释', actionKind: 'explain' },
        { strategy: 'Grid-Neutral-v11', annualized: '19.3%', maxDd: '12.1%', oosTag: { text: '待观察', variant: 'yellow' }, overfit: '中', action: '报告', actionKind: 'report' }
      ],
      gaugePercent: 84,
      gaugeLabel: '84%',
      trustFeatures: [
        { title: '样本外收益 / 样本内收益', desc: '77.3%，超过 60% 准入线。', tag: { text: 'PASS', variant: 'green' } },
        { title: '滑点敏感性', desc: '滑点增加 2 倍后收益下降 8.4%。', tag: { text: 'WATCH', variant: 'yellow' } },
        { title: 'Scenario Analysis', desc: '流动性枯竭、黑天鹅跳空、交易所故障、延迟冲击均有分场景结果。', tag: { text: 'PASS', variant: 'green' } }
      ],
      scenarios: [
        { scenario: 'Liquidity Crisis', loss: '-3.8%', maxDd: '14.2%', fuse: { text: '只允许减仓', variant: 'yellow' }, suggestion: '降低挂单深度，分批退出', human: '需要' },
        { scenario: 'Black Swan Gap', loss: '-5.6%', maxDd: '18.9%', fuse: { text: '触发组合熔断', variant: 'red' }, suggestion: '暂停新开仓，保留止损', human: '需要' },
        { scenario: 'Exchange Outage', loss: '-1.1%', maxDd: '10.1%', fuse: { text: '切换备用执行', variant: 'yellow' }, suggestion: '撤销未成交订单', human: '不需要' },
        { scenario: 'Correlation Spike', loss: '-2.9%', maxDd: '15.4%', fuse: { text: '收缩风险预算', variant: 'yellow' }, suggestion: '降低 ETH/SOL 联动暴露', human: '需要' },
        { scenario: 'Latency Shock', loss: '-0.7%', maxDd: '9.8%', fuse: { text: '未触发', variant: 'green' }, suggestion: '扩大限价保护，不追价', human: '不需要' }
      ],
      scenarioCardSubtitle: 'ATR-Trend-v19 · portfolio impact'
    },

    explain: {
      headline: 'BTC/USDT 买入信号拆解',
      subcopy:
        '本次建议不是直接给出“买入”，而是展示各因子对信号的正负贡献，便于交易员判断是否接受小仓位试探。',
      factors: [
        { name: '趋势强度', widthPct: 84, contrib: '+0.42', negative: false },
        { name: '波动率过滤', widthPct: 62, contrib: '+0.31', negative: false },
        { name: '成交量确认', widthPct: 36, contrib: '+0.18', negative: false },
        { name: '资金费率风险', widthPct: 24, contrib: '-0.12', negative: true },
        { name: '流动性惩罚', widthPct: 16, contrib: '-0.08', negative: true }
      ],
      confidenceGaugePct: 84,
      confidenceGaugeLabel: '0.84',
      confidenceFeatures: [
        { title: '数据质量', desc: '主源与备用源价差 0.04%，缺失率 0.02%。', tag: '0.92', variant: 'green' },
        { title: '历史相似场景', desc: '过去 27 次相似突破中，17 次在 10 日内盈利。', tag: '0.71', variant: 'yellow' },
        { title: '执行可行性', desc: '订单占 5 档盘口深度 3.6%，建议拆单执行。', tag: '0.86', variant: 'green' }
      ],
      rationale: [
        { title: '信号触发', desc: '4H 收盘价突破 Donchian 上轨，ATR 波动率仍在可交易区间。', tag: 'Hit', variant: 'green' },
        { title: '风险约束', desc: '单策略仓位不超过 2%，组合回撤预算仍有 5.6% 缓冲。', tag: 'Safe', variant: 'green' },
        { title: '负面因素', desc: '资金费率偏高、盘口深度下降，因此不建议一次性重仓。', tag: 'Limit', variant: 'yellow' },
        { title: '最终动作', desc: 'Execution Agent 只生成 2% 小仓位订单草案，进入人工审批。', tag: 'Approval', variant: 'yellow' }
      ],
      explainMatrix: [
        ['规则策略', '规则命中链路', '触发条件、阈值、止损规则'],
        ['多因子策略', '因子贡献 / 暴露', '正负贡献、行业/风格暴露'],
        ['机器学习策略', 'Feature Importance / SHAP', '特征重要性、样本级解释'],
        ['组合策略', '风险贡献', '相关性、风险预算、边际 VaR']
      ],
      lineage: [
        { step: 'Raw Data', detail: 'Binance Public<br/>版本：2026-05-08<br/>Hash: 8fa2' },
        { step: 'Cleaning', detail: '去重 / 缺失填充<br/>异常 K 线 3 条<br/>可复现' },
        { step: 'Feature Store', detail: 'ATR / Donchian / Volume<br/>因子版本 f-219<br/>只读' },
        { step: 'Bias Check', detail: '未来函数：通过<br/>幸存者偏差：通过<br/>泄漏：通过' },
        { step: 'Backtest', detail: 'Walk-forward<br/>成本模型 c-07<br/>样本外通过' },
        { step: 'Live Signal', detail: '主备源一致<br/>延迟 82ms<br/>许可：Paper/Live' },
        { step: 'Order Draft', detail: 'BTC 2%<br/>需人工审批<br/>Trace ID: T-9042' }
      ]
    },

    portfolio: {
      gauges: [
        { pct: 72, label: '72%', title: '风险预算使用率', desc: '距离组合最大回撤预算仍有缓冲。' },
        { pct: 58, label: '58%', title: 'AI 自动化比例', desc: '流程性任务由 Agent 处理，交易仍需审批。' },
        { pct: 89, label: '89%', title: '策略分散度', desc: '多策略相关性处于安全区间。' }
      ],
      allocation: [
        { strategy: 'BTC ATR Trend', weight: '35%', risk: 'A-', statusTag: { text: 'Live', variant: 'green' } },
        { strategy: 'ETH Donchian', weight: '20%', risk: 'B+', statusTag: { text: 'Paper', variant: 'yellow' } },
        { strategy: 'ETF Rotation', weight: '25%', risk: 'A', statusTag: { text: 'Live', variant: 'green' } },
        { strategy: 'Cash Buffer', weight: '20%', risk: 'A+', statusTag: { text: 'Reserve', variant: '' } }
      ],
      correlationCells: [
        '.12',
        '.42',
        '.21',
        '.76',
        '.09',
        '.38',
        '.18',
        '.42',
        '.14',
        '.28',
        '.47',
        '.22',
        '.81',
        '.11',
        '.21',
        '.28',
        '.06',
        '.51',
        '.17',
        '.44',
        '.25',
        '.76',
        '.47',
        '.51',
        '.13',
        '.39',
        '.27',
        '.72'
      ],
      correlationHeat: [
        'cool',
        'mid',
        'cool',
        'hot',
        'cool',
        'mid',
        'cool',
        'mid',
        'cool',
        'cool',
        'mid',
        'cool',
        'hot',
        'cool',
        'cool',
        'cool',
        'cool',
        'mid',
        'cool',
        'mid',
        'cool',
        'hot',
        'mid',
        'mid',
        'cool',
        'mid',
        'cool',
        'hot'
      ]
    },

    execution: {
      cards: [
        {
          tag: { text: '需要确认', variant: 'yellow' },
          title: '买入 BTC/USDT',
          body: '4H 趋势突破，ATR 波动率可接受，策略 v19 触发买入信号。',
          metrics: [
            { label: '金额', value: '资金 2%' },
            { label: '限价', value: '卖一 +0.05%' },
            { label: '止损', value: '-4%' },
            { label: '评分', value: 'A-' }
          ],
          actions: [
            { label: '批准', className: 'btn success', modal: 'approve' },
            { label: '拒绝', className: 'btn secondary', modal: null }
          ]
        },
        {
          tag: { text: '需要确认', variant: 'yellow' },
          title: '卖出 ETH 20%',
          body: 'Risk Agent 检测 ETH 策略近期回撤扩大，建议减仓控制组合暴露。',
          metrics: [
            { label: '金额', value: '仓位 20%' },
            { label: '原因', value: '降风险' },
            { label: '影响', value: 'DD -1.8%' },
            { label: '评分', value: 'B+' }
          ],
          actions: [
            { label: '批准', className: 'btn success', modal: 'approve' },
            { label: '拒绝', className: 'btn secondary', modal: null }
          ]
        },
        {
          tag: { text: '不确定性', variant: 'red' },
          title: 'SOL 策略暂停',
          body: '行情源之间价格偏差超过阈值，AI 无法确认真实成交价格，建议暂停新开仓。',
          metrics: [
            { label: 'Confidence', value: '0.68' },
            { label: '数据质量', value: '82' },
            { label: '动作', value: '暂停' },
            { label: '级别', value: 'P1' }
          ],
          actions: [
            { label: '暂停', className: 'btn danger', modal: 'pause' },
            { label: '转人工', className: 'btn secondary', modal: null }
          ]
        }
      ]
    },

    risk: {
      kpis: [
        { label: '账户级单日亏损', value: '0.8%', trend: '阈值 2%', trendClass: '' },
        { label: '组合最大回撤', value: '9.4%', trend: '预算 15%', trendClass: 'warn' },
        { label: '拒单次数', value: '13', trend: '今日', trendClass: '' },
        { label: '熔断状态', value: '正常', trend: '未触发', trendClass: '' }
      ],
      policies: [
        { title: 'AI 请求：提高 ETH 仓位至 40%', desc: '拒绝：超过激进策略单品种仓位上限 30%。', tag: 'DENIED', variant: 'red' },
        { title: 'AI 请求：运行 180 天回测', desc: '允许：只读数据，不涉及实盘资金。', tag: 'ALLOWED', variant: 'green' },
        { title: 'AI 请求：提交 BTC 小额订单', desc: '需要人工确认：属于实盘交易动作。', tag: 'APPROVAL', variant: 'yellow' }
      ],
      circuitRules: [
        { title: '可恢复熔断', desc: '行情延迟、策略心跳异常、交易所短时超时。', tag: 'AUTO', variant: 'yellow' },
        { title: '不可恢复熔断', desc: '资金异常、重复下单、风控服务不可用。', tag: 'MANUAL', variant: 'red' },
        { title: '恢复审批', desc: '熔断恢复必须经过风控员确认，AI 只能提交恢复申请。', tag: 'HITL', variant: 'purple' }
      ]
    },

    data: {
      sources: [
        { name: 'CCXT Binance Public', usage: 'Research / Paper', latency: '82ms', missing: '0.02%', drift: '0.04%', status: { text: 'OK', variant: 'green' } },
        { name: 'OKX WebSocket', usage: 'Paper / Backup', latency: '110ms', missing: '0.01%', drift: '0.06%', status: { text: 'OK', variant: 'green' } },
        { name: 'AKShare A-share', usage: 'Research', latency: 'EOD', missing: '0.12%', drift: '-', status: { text: '非实时', variant: 'yellow' } },
        { name: 'Broker Licensed Feed', usage: 'Live', latency: '14ms', missing: '0.00%', drift: '0.01%', status: { text: 'Licensed', variant: 'green' } }
      ],
      biasChecks: [
        { title: 'Survivorship Bias 幸存者偏差', desc: 'A 股研究数据必须包含退市标的和历史成分变更。', tag: 'PASS', variant: 'green' },
        { title: 'Look-ahead Bias 未来函数', desc: '特征只能使用信号生成时已经可见的数据时间戳。', tag: 'PASS', variant: 'green' },
        { title: 'Feature Leakage 特征泄漏', desc: '标签、成交结果、未来资金费率不得进入训练特征。', tag: 'WATCH', variant: 'yellow' },
        { title: 'License Scope 数据许可', desc: 'Research Only 数据禁止进入实盘信号和订单草案。', tag: 'ENFORCED', variant: 'red' }
      ],
      lineageSnapshot: [
        { node: 'Raw Tick', version: 'feed-20260508', hash: '8fa2', live: { text: '允许', variant: 'green' } },
        { node: 'Cleaned Bar', version: 'bar-v44', hash: '51bc', live: { text: '允许', variant: 'green' } },
        { node: 'Feature Set', version: 'factor-f219', hash: 'c0a7', live: { text: '允许', variant: 'green' } },
        { node: 'AKShare EOD', version: 'research-031', hash: '19de', live: { text: '禁止', variant: 'red' } }
      ]
    },

    security: {
      kpis: [
        { label: '明文密钥暴露', value: '0', trend: 'Vault 托管', trendClass: '' },
        { label: '提现权限', value: '关闭', trend: '强制规则', trendClass: '' },
        { label: '密钥轮换', value: '30d', trend: '自动提醒', trendClass: '' },
        { label: '资金账户', value: '隔离', trend: '主/子账户', trendClass: '' }
      ],
      segments: [
        { title: '主账户', desc: '资金保管，不运行策略，不开放 AI 操作。', tag: 'Safe', variant: 'green' },
        { title: '小额实盘账户', desc: '仅允许已审批策略运行，交易需确认或预授权。', tag: 'Controlled', variant: 'yellow' },
        { title: '实验账户', desc: 'AI 自动模拟盘、回测、策略验证，不动真钱。', tag: 'Sandbox', variant: 'purple' }
      ],
      aiBlocked: [
        { title: '禁止读取 Secret', desc: 'Agent 无权查看、导出、解密 API Key。', tag: 'Blocked', variant: 'red' },
        { title: '禁止提现/划转', desc: '交易系统不提供提现能力。', tag: 'Blocked', variant: 'red' },
        { title: '禁止关闭风控', desc: '风控规则放宽必须双人审批。', tag: 'Blocked', variant: 'red' }
      ]
    },

    collaboration: {
      kpis: [
        { label: 'Research Threads', value: '18', trend: '6 个活跃讨论', trendClass: '' },
        { label: 'Pending Reviews', value: '5', trend: '2 个需风控补充', trendClass: 'warn' },
        { label: 'A/B Tests', value: '3', trend: '模拟盘运行中', trendClass: '' },
        { label: 'Role Gates', value: '启用', trend: '研究 / 交易 / 风控分权', trendClass: '' }
      ],
      diffHeader: 'ATR-v18 → ATR-v19',
      diffRows: [
        { field: 'ATR Window', from: '14', to: '21', impact: '降低噪声交易' },
        { field: 'Stop Loss', from: '3.5%', to: '4.0%', impact: '降低假突破止损' },
        { field: 'Turnover', from: '4.8x', to: '4.2x', impact: '交易成本下降' },
        { field: 'Max Drawdown', from: '-18.2%', to: '-14.6%', impact: '风险改善' }
      ],
      reviews: [
        { role: 'Researcher', text: 'v19 在样本外表现更稳，建议继续模拟盘 14 天。', tag: '支持', variant: 'green' },
        { role: 'Risk Agent', text: '要求补充 2021-2022 类熊市场和流动性枯竭压测。', tag: '补充', variant: 'yellow' },
        { role: 'Trader', text: '同意进入模拟盘，不进入实盘候选。', tag: 'Paper', variant: 'purple' },
        { role: 'Compliance', text: '当前数据许可允许研究和模拟盘，不允许使用 Research Only 源实盘。', tag: '限制', variant: 'red' }
      ],
      footerCards: [
        { title: 'Code Review', desc: '策略代码、参数空间、交易成本模型和数据依赖变更均需留下评审记录。', tag: 'Required', variant: 'yellow' },
        { title: 'A/B Testing', desc: 'v18 与 v19 可在相同资金预算和行情源下运行模拟盘对照。', tag: 'Running', variant: 'green' },
        { title: 'Approval Flow', desc: '实盘候选必须经过研究、交易、风控三方确认，AI 只能提交建议。', tag: 'HITL', variant: 'red' }
      ]
    },

    audit: {
      rows: [
        { time: '09:42:18', actor: 'Risk Agent', action: '拒绝仓位提升', resource: 'ETH-Trend-v18', result: { text: 'DENIED', variant: 'red' }, confidence: '0.91' },
        { time: '09:38:02', actor: 'Backtest Agent', action: '运行样本外验证', resource: 'ATR-v19', result: { text: 'PASS', variant: 'green' }, confidence: '0.84' },
        { time: '09:36:11', actor: 'Explainability Agent', action: '生成信号归因', resource: 'BTC Buy 2%', result: { text: 'TRACE', variant: 'green' }, confidence: '0.84' },
        { time: '09:34:07', actor: 'Data Agent', action: '校验血缘 Hash', resource: 'factor-f219', result: { text: 'VERIFIED', variant: 'green' }, confidence: '0.93' },
        { time: '09:31:44', actor: 'Data Agent', action: '切换备用行情源', resource: 'BTC/USDT', result: { text: 'AUTO', variant: 'green' }, confidence: '0.96' },
        { time: '09:26:10', actor: 'Execution Agent', action: '创建订单草案', resource: 'BTC Buy 2%', result: { text: 'APPROVAL', variant: 'yellow' }, confidence: '0.88' },
        { time: '09:12:22', actor: 'Human', action: '批准小额实盘', resource: 'BTC-MA-v12', result: { text: 'APPROVED', variant: 'green' }, confidence: '-' }
      ]
    }
  };
})(typeof window !== 'undefined' ? window : this);
