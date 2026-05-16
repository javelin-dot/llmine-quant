export interface MockData {
  meta: { product: string; subtitle: string }
  system: { healthScore: number; healthStatusLabel: string; healthBarHeights: number[]; autopilot: boolean; riskGateLabel: string }
  modals: Record<string, { title: string; body: string; primary: string }>
  dashboard: {
    meta: { product: string; subtitle: string }
    system: { healthScore: number; healthStatusLabel: string; healthBarHeights: number[]; autopilot: boolean; riskGateLabel: string }
    modals: Record<string, { title: string; body: string; primary: string }>
    marketIndices: { name: string; symbol: string; price: number; change: number; volume: string }[]
    portfolioMetrics: {
      totalReturn: number
      annualReturn: number
      maxDrawdown: number
      sharpeRatio: number
      sortinoRatio: number
      benchmark: string
      benchmarkReturn: number
    }
    equityCurve: { date: string; value: number; benchmark: number }[]
    agents: {
      avatar: string
      name: string
      detail: string
      metric: string
      status: 'active' | 'waiting' | 'attention' | 'idle'
    }[]
    alerts: {
      id: string
      type: 'approval' | 'risk' | 'system'
      title: string
      time: string
      severity: 'high' | 'medium' | 'low'
      target?: string
    }[]
    strategies: {
      id: string
      name: string
      type: string
      return: number
      status: 'live' | 'paper' | 'backtest' | 'draft'
      sparkline: number[]
      lastSignalTime: string
    }[]
    pendingApprovals: number
  }
  agentWorkflow: {
    presets: {
      id: string
      name: string
      description: string
      steps: {
        id: string
        avatar: string
        roleKey: string
        displayName: string
        objective: string
        downstreamHint: string
        autonomy: 'autonomous' | 'supervised' | 'human_gate'
        gates: string[]
      }[]
    }[]
  }
  strategy: {
    pipelineStatus: { stage: string; count: number; tone: 'blue' | 'green' | 'yellow' | 'purple' | 'red' }[]
    templates: { id: string; name: string; risk: 'conservative' | 'balanced' | 'aggressive'; market: string; family: string; desc: string }[]
    nlPrompt: string
    feed: { time: string; agent: string; event: string; tone: 'blue' | 'green' | 'yellow' | 'purple' | 'red' }[]
    matrix: {
      id: string
      name: string
      family: string
      annualReturn: number
      maxDd: number
      sharpe: number
      status: 'live' | 'paper' | 'backtest' | 'draft'
      oosScore: number
      sparkline: number[]
      lastUpdate: string
    }[]
    pipelineBoard: {
      lane: string
      tone: 'blue' | 'green' | 'yellow' | 'purple' | 'red'
      tickets: {
        id: string
        title: string
        desc: string
        progress: number
        metrics: { label: string; value: string }[]
        tag: string
        tagClass?: string
      }[]
    }[]
  }
  backtest: {
    kpis: { label: string; value: string; trend: string; tone: 'green' | 'yellow' | 'red' | 'blue' | 'purple' }[]
    equityCurves: {
      label: string
      inSample: { date: string; value: number }[]
      outSample: { date: string; value: number }[]
      drawdown: { date: string; value: number }[]
    }
    confidence: {
      score: number
      label: string
      features: { title: string; desc: string; score: string; tone: 'green' | 'yellow' | 'red' }[]
    }
    walkForward: {
      folds: { period: string; isReturn: number; oosReturn: number }[]
    }
    comparison: {
      id: string
      name: string
      family: string
      annualReturn: number
      maxDd: number
      sharpe: number
      oosScore: number
      overfit: 'low' | 'medium' | 'high'
      status: 'live' | 'paper' | 'backtest' | 'draft'
      sparkline: number[]
    }[]
    scenarios: {
      id: string
      name: string
      severity: 'high' | 'medium' | 'low'
      loss: string
      maxDd: string
      fuse: string
      fuseTone: 'green' | 'yellow' | 'red'
      suggestion: string
      human: string
    }[]
    parameterHeatmap: {
      xLabel: string
      yLabel: string
      xTicks: string[]
      yTicks: string[]
      cells: number[][]
      bestX: number
      bestY: number
    }
  }
  explain: {
    signalHeader: {
      strategy: string
      action: 'BUY' | 'SELL' | 'HOLD'
      target: string
      size: string
      confidence: number
      riskGrade: string
      traceId: string
      timestamp: string
      status: string
      statusTone: 'green' | 'yellow' | 'red' | 'blue'
    }
    attribution: {
      base: number
      items: { name: string; value: number; desc: string }[]
      final: number
      decision: string
      decisionTone: 'green' | 'yellow' | 'red'
    }
    confidenceRadar: {
      axes: { name: string; score: number; desc: string }[]
      avg: number
    }
    decisionChain: {
      step: number
      title: string
      desc: string
      detail: string
      tag: string
      tone: 'green' | 'yellow' | 'red' | 'blue' | 'purple'
    }[]
    lineage: {
      step: string
      version: string
      hash: string
      permission: string
      permissionTone: 'green' | 'yellow' | 'red'
      detail: string
    }[]
    biasGate: {
      check: string
      status: 'pass' | 'watch' | 'fail' | 'enforced'
      desc: string
    }[]
    similarHistory: {
      summary: string
      winRate: number
      avgReturn: number
      cases: {
        id: string
        date: string
        action: string
        ret: number
        days: number
        success: boolean
        note: string
      }[]
    }
  }
  portfolio: {
    nav: {
      total: number
      currency: string
      todayPnl: number
      todayPct: number
      mtdPct: number
      ytdPct: number
      cashPct: number
      leverage: number
      netExposure: number
      varDaily: number
      varPct: number
    }
    riskBudget: {
      label: string
      pct: number
      limit: number
      tone: 'green' | 'yellow' | 'red' | 'blue' | 'purple'
      desc: string
    }[]
    allocation: {
      strategies: {
        name: string
        family: string
        weight: number
        pnl: number
        pnlPct: number
        risk: string
        status: 'live' | 'paper' | 'backtest' | 'draft'
        statusTone: 'green' | 'yellow' | 'red' | 'blue' | 'purple'
        contribution: number
        sparkline: number[]
      }[]
    }
    correlation: {
      labels: string[]
      matrix: number[][]
    }
    concentration: {
      sectors: { name: string; weight: number; change: number }[]
      holdings: { symbol: string; name: string; weight: number; change: number }[]
      factors: { name: string; exposure: number; tone: 'green' | 'yellow' | 'red' | 'blue' | 'purple' }[]
    }
    rebalance: {
      id: string
      type: 'reduce' | 'add' | 'rotate' | 'hedge'
      from: string
      to: string
      delta: string
      reason: string
      impact: string
      urgency: 'high' | 'medium' | 'low'
      urgencyTone: 'green' | 'yellow' | 'red'
    }[]
  }
  execution: {
    summary: {
      pending: number
      urgent: number
      blocked: number
      approved24h: number
      avgLatencySec: number
      successRate: number
    }
    approvals: {
      id: string
      type: 'live' | 'paper' | 'reduce' | 'add' | 'rotate' | 'hedge' | 'pause'
      typeTone: 'red' | 'green' | 'yellow' | 'blue' | 'purple'
      symbol: string
      name: string
      side: 'BUY' | 'SELL' | 'PAUSE'
      qty: string
      notional: string
      notionalPct: number
      limitPrice: string
      stopLoss: string
      confidence: number
      riskGrade: string
      reason: string
      impact: string
      expireSec: number
      urgency: 'high' | 'medium' | 'low'
      urgencyTone: 'red' | 'yellow' | 'green'
      strategy: string
    }[]
    preTradeChecks: {
      name: string
      current: number
      limit: number
      status: 'pass' | 'watch' | 'fail'
      statusTone: 'green' | 'yellow' | 'red'
      note: string
    }[]
    orderBook: {
      time: string
      symbol: string
      side: 'BUY' | 'SELL'
      qty: string
      limit: string
      filled: string
      status: 'filled' | 'partial' | 'rejected' | 'canceled' | 'working'
      statusTone: 'green' | 'yellow' | 'red' | 'gray' | 'blue'
      slippageBps: number
      pnl: number | null
    }[]
    metrics: {
      slippage: {
        avgBps: number
        p50Bps: number
        p95Bps: number
        buckets: { range: string; count: number }[]
      }
      fillRate: {
        total: number
        filled: number
        partial: number
        rejected: number
        canceled: number
      }
      rejectReasons: { reason: string; count: number; tone: 'red' | 'yellow' | 'blue' | 'purple' }[]
    }
    agentTrace: {
      time: string
      agent: string
      action: string
      detail: string
      tone: 'green' | 'yellow' | 'red' | 'blue' | 'purple'
      icon: string
    }[]
  }
  risk: {
    header: {
      healthScore: number
      healthStatus: string
      healthStatusTone: 'green' | 'yellow' | 'red' | 'blue'
      killSwitchArmed: boolean
      lastIncident: string
      autoBlocks24h: number
      pendingApprovals: number
      activeBreaches: number
    }
    kpis: {
      label: string
      value: string
      trend: string
      tone: 'green' | 'yellow' | 'red' | 'blue' | 'purple'
    }[]
    budgets: {
      name: string
      used: number
      limit: number
      unit: string
      tone: 'green' | 'yellow' | 'red'
      desc: string
    }[]
    var: {
      daily: number
      dailyPct: number
      weekly: number
      weeklyPct: number
      confidence: number
      currency: string
      history: { date: string; value: number }[]
      decomposition: {
        strategy: string
        contribution: number
        pct: number
        tone: 'green' | 'yellow' | 'red'
      }[]
    }
    circuits: {
      level: 'L1' | 'L2' | 'L3' | 'L4'
      name: string
      status: 'armed' | 'triggered' | 'cooldown' | 'disabled'
      statusTone: 'green' | 'yellow' | 'red' | 'gray'
      trigger: string
      action: string
      triggers24h: number
      lastTrigger: string
    }[]
    policyStream: {
      time: string
      agent: string
      request: string
      decision: 'allowed' | 'denied' | 'approval_required' | 'modified'
      decisionTone: 'green' | 'yellow' | 'red' | 'blue'
      reason: string
      durationMs: number
    }[]
    breaches: {
      time: string
      severity: 'critical' | 'high' | 'medium' | 'low'
      severityTone: 'red' | 'yellow' | 'blue'
      title: string
      detail: string
      resolution: string
      status: 'resolved' | 'ongoing' | 'review'
      statusTone: 'green' | 'yellow' | 'red'
    }[]
    complianceGates: {
      title: string
      desc: string
      status: 'pass' | 'watch' | 'fail' | 'enforced'
      statusTone: 'green' | 'yellow' | 'red' | 'blue'
      lastCheck: string
      note: string
    }[]
  }
  data: {
    header: {
      totalSources: number
      activeSources: number
      erroredSources: number
      avgLatencyMs: number
      p95LatencyMs: number
      missingRate: number
      incidents24h: number
      healthScore: number
      healthStatus: string
      healthStatusTone: 'green' | 'yellow' | 'red' | 'blue'
      /** KPIs aligned with `/data/symbols/stats` + feature catalog (overview). */
      totalBars?: number
      totalSymbols?: number
      featureCount?: number
      latestTradeDate?: string | null
    }
    tiers: {
      tier: 'research' | 'paper' | 'live'
      label: string
      count: number
      active: number
      avgLatencyMs: number
      license: string
      tone: 'blue' | 'yellow' | 'red'
      desc: string
    }[]
    kpis: {
      label: string
      value: string
      trend: string
      tone: 'green' | 'yellow' | 'red' | 'blue' | 'purple'
    }[]
    sources: {
      id: string
      name: string
      provider: string
      tier: 'research' | 'paper' | 'live'
      tierTone: 'blue' | 'yellow' | 'red'
      type: string
      coverage: string
      latencyMs: number
      latencyP95: number
      missingPct: number
      driftScore: number
      license: string
      status: 'healthy' | 'warning' | 'error' | 'maintenance'
      statusTone: 'green' | 'yellow' | 'red' | 'gray' | 'blue'
      lastUpdate: string
    }[]
    latencyTrend: {
      times: string[]
      research: number[]
      paper: number[]
      live: number[]
      slaMs: number
    }
    /** Daily bar row counts by trade_date (local DB ingest footprint). */
    ingestTrend: {
      dates: string[]
      bars: number[]
    }
    lineage: {
      nodes: {
        id: string
        label: string
        tier: string
        tone: 'blue' | 'yellow' | 'red' | 'green' | 'purple' | 'gray'
        version: string
        permission: string
      }[]
      edges: { from: string; to: string }[]
    }
    incidents: {
      time: string
      source: string
      type: 'latency' | 'missing' | 'drift' | 'license' | 'outage' | 'schema'
      typeTone: 'red' | 'yellow' | 'blue' | 'purple'
      severity: 'critical' | 'high' | 'medium' | 'low'
      severityTone: 'red' | 'yellow' | 'blue'
      title: string
      detail: string
      resolution: string
      status: 'resolved' | 'ongoing' | 'review'
      statusTone: 'green' | 'yellow' | 'red'
    }[]
  }
  security: {
    header: {
      healthScore: number
      healthStatus: string
      healthStatusTone: 'green' | 'yellow' | 'red' | 'blue'
      vaultArmed: boolean
      withdrawalEnabled: boolean
      lastRotation: string
      nextRotation: string
      keyExpiringIn: string
      plaintextLeaks: number
      aiViolations24h: number
    }
    kpis: {
      label: string
      value: string
      trend: string
      tone: 'green' | 'yellow' | 'red' | 'blue' | 'purple'
    }[]
    accounts: {
      id: string
      name: string
      role: 'custody' | 'live-main' | 'live-small' | 'paper' | 'sandbox'
      roleLabel: string
      roleTone: 'green' | 'yellow' | 'red' | 'blue' | 'purple'
      balance: string
      balanceUsd: string
      cap: string
      capPct: number
      aiPermissions: { label: string; tone: 'green' | 'yellow' | 'red' | 'blue' | 'gray' }[]
      withdrawalEnabled: boolean
      desc: string
    }[]
    vault: {
      totalKeys: number
      apiKeys: number
      walletKeys: number
      rotated30d: number
      expiringSoon: number
      expired: number
      plaintextLeaks: number
      keys: {
        id: string
        label: string
        type: 'api' | 'wallet' | 'ssh' | 'webhook' | 'db'
        typeTone: 'blue' | 'yellow' | 'red' | 'purple' | 'green'
        provider: string
        rotated: string
        expires: string
        daysToExpiry: number
        status: 'active' | 'rotating' | 'expiring' | 'expired'
        statusTone: 'green' | 'yellow' | 'red' | 'gray'
        scope: string
      }[]
    }
    aiPermissions: {
      category: string
      allowed: { api: string; desc: string }[]
      blocked: { api: string; desc: string; reason: string }[]
    }[]
    withdrawal: {
      enabled: boolean
      whitelistAddresses: number
      pendingApprovals: number
      blocks24h: number
      lastBlock: string
      rules: {
        name: string
        desc: string
        status: 'enforced' | 'enabled' | 'disabled'
        statusTone: 'green' | 'yellow' | 'red'
      }[]
    }
    events: {
      time: string
      type: 'rotation' | 'block' | 'access' | 'violation' | 'audit'
      typeTone: 'green' | 'yellow' | 'red' | 'blue' | 'purple'
      severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
      severityTone: 'red' | 'yellow' | 'blue' | 'green'
      title: string
      actor: string
      detail: string
      resolution: string
      status: 'resolved' | 'ongoing' | 'review'
      statusTone: 'green' | 'yellow' | 'red'
    }[]
  }
  collaboration: {
    kpis: { label: string; value: string; trend: string; tone: 'green' | 'yellow' | 'red' | 'blue' | 'purple' }[]
    activeReviews: {
      id: string
      strategy: string
      fromVer: string
      toVer: string
      status: 'pending' | 'in_review' | 'approved' | 'rejected'
      statusTone: 'green' | 'yellow' | 'red' | 'blue'
      reviewers: { role: string; decision: 'approve' | 'request_changes' | 'pending'; tone: 'green' | 'yellow' | 'red' | 'gray' }[]
      createdAt: string
      priority: 'high' | 'medium' | 'low'
      priorityTone: 'green' | 'yellow' | 'red'
    }[]
    diff: {
      header: string
      rows: { field: string; from: string; to: string; impact: string }[]
    }
    reviewThread: { role: string; text: string; tag: string; tagClass?: string }[]
    abTests: {
      id: string
      name: string
      control: string
      variant: string
      status: 'running' | 'completed' | 'pending'
      statusTone: 'green' | 'yellow' | 'blue'
      duration: string
      samples: number
      improvement: number
      sparkline: number[]
    }[]
    approvalFlow: {
      stage: string
      tone: 'green' | 'yellow' | 'red' | 'blue' | 'purple' | 'gray'
      required: boolean
      completed: boolean
      assignee: string
      note: string
    }[]
    footerCards: { title: string; desc: string; tag: string; tagClass?: string }[]
  }
  audit: {
    kpis: { label: string; value: string; trend: string; tone: 'green' | 'yellow' | 'red' | 'blue' | 'purple' }[]
    rows: {
      time: string
      actor: string
      actorType: 'human' | 'agent' | 'system'
      action: string
      resource: string
      result: string
      resultTone: 'green' | 'yellow' | 'red' | 'blue'
      confidence: number
      detail: string
      traceId: string
    }[]
    actorStats: { actor: string; count: number; tone: 'green' | 'yellow' | 'red' | 'blue' | 'purple' }[]
    toolRegistry: { name: string; level: string; levelTone: 'green' | 'yellow' | 'red' | 'blue' | 'purple'; desc: string; agents: string[] }[]
    hitlRules: { rule: string; desc: string; status: 'auto' | 'review' | 'approval'; statusTone: 'green' | 'yellow' | 'red' }[]
  }
}

export interface StrategyTaskOut {
  id: string
  prompt: string
  market: string
  riskProfile: string
  status: string
  statusTone: string
  progress: number
  stage: string | null
  strategyId: string | null
  agentTaskId: string | null
  result: string | null
  error: string | null
  createdAt: string
  updatedAt: string
}

export interface PipelineEventOut {
  id: string
  strategyId: string
  stage: string
  event: string
  progress: number
  detail: string | null
  createdAt: string
}
