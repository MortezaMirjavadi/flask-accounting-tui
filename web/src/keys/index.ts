export const queryKeys = {
  auth: {
    all: ["auth"] as const,
    me: () => [...queryKeys.auth.all, "me"] as const,
  },

  categories: {
    all: ["categories"] as const,
    list: (filters?: Record<string, string>) =>
      [...queryKeys.categories.all, "list", filters] as const,
    detail: (id: number) =>
      [...queryKeys.categories.all, "detail", id] as const,
  },

  wallets: {
    all: ["wallets"] as const,
    list: (filters?: Record<string, string>) =>
      [...queryKeys.wallets.all, "list", filters] as const,
    detail: (id: number) => [...queryKeys.wallets.all, "detail", id] as const,
    balance: (id: number) =>
      [...queryKeys.wallets.all, "balance", id] as const,
    transfers: (id: number) =>
      [...queryKeys.wallets.all, "transfers", id] as const,
    members: (id: number) =>
      [...queryKeys.wallets.all, "members", id] as const,
    activity: (id: number) =>
      [...queryKeys.wallets.all, "activity", id] as const,
    invitations: () =>
      [...queryKeys.wallets.all, "invitations"] as const,
    consolidated: () =>
      [...queryKeys.wallets.all, "consolidated"] as const,
    accounts: (walletId: number) =>
      [...queryKeys.wallets.all, "accounts", walletId] as const,
    accountDetail: (walletId: number, accountId: number) =>
      [...queryKeys.wallets.all, "account", walletId, accountId] as const,
  },

  transactions: {
    all: ["transactions"] as const,
    list: (filters?: Record<string, string>) =>
      [...queryKeys.transactions.all, "list", filters] as const,
    detail: (id: number) =>
      [...queryKeys.transactions.all, "detail", id] as const,
    items: (txId: number) =>
      [...queryKeys.transactions.all, "items", txId] as const,
    mostPurchased: (filters?: Record<string, string>) =>
      [...queryKeys.transactions.all, "most-purchased", filters] as const,
    searchItems: (query: string) =>
      [...queryKeys.transactions.all, "search", query] as const,
    itemStats: (filters?: Record<string, string>) =>
      [...queryKeys.transactions.all, "item-stats", filters] as const,
  },

  transfers: {
    all: ["transfers"] as const,
    list: (filters?: Record<string, string>) =>
      [...queryKeys.transfers.all, "list", filters] as const,
    detail: (id: number) =>
      [...queryKeys.transfers.all, "detail", id] as const,
  },

  calendar: {
    all: ["calendar"] as const,
    events: (filters?: Record<string, string>) =>
      [...queryKeys.calendar.all, "events", filters] as const,
    eventDetail: (id: number) =>
      [...queryKeys.calendar.all, "event", id] as const,
    instances: (filters?: Record<string, string>) =>
      [...queryKeys.calendar.all, "instances", filters] as const,
  },

  users: {
    all: ["users"] as const,
    list: (filters?: Record<string, string>) =>
      [...queryKeys.users.all, "list", filters] as const,
    detail: (id: number) =>
      [...queryKeys.users.all, "detail", id] as const,
  },

  forecast: {
    all: ["forecast"] as const,
    byPeriod: (periodDays: number) =>
      [...queryKeys.forecast.all, periodDays] as const,
  },

  alerts: {
    all: ["alerts"] as const,
  },

  budget: {
    all: ["budget"] as const,
    periods: () => [...queryKeys.budget.all, "periods"] as const,
    periodsWithItems: () =>
      [...queryKeys.budget.all, "periods-with-items"] as const,
    periodDetail: (id: number) =>
      [...queryKeys.budget.all, "period", id] as const,
    items: (periodId: number) =>
      [...queryKeys.budget.all, "items", periodId] as const,
    itemDetail: (id: number) =>
      [...queryKeys.budget.all, "item", id] as const,
  },

  reports: {
    all: ["reports"] as const,
    daily: (date?: string, walletId?: number) =>
      [...queryKeys.reports.all, "daily", date, walletId] as const,
    weekly: (date?: string, walletId?: number) =>
      [...queryKeys.reports.all, "weekly", date, walletId] as const,
    monthly: (year?: number, month?: number, walletId?: number) =>
      [...queryKeys.reports.all, "monthly", year, month, walletId] as const,
    summary: (filters?: Record<string, string>) =>
      [...queryKeys.reports.all, "summary", filters] as const,
    byCategory: (filters?: Record<string, string>) =>
      [...queryKeys.reports.all, "by-category", filters] as const,
    byMonth: (filters?: Record<string, string>) =>
      [...queryKeys.reports.all, "by-month", filters] as const,
    categoryChart: (filters?: Record<string, string>) =>
      [...queryKeys.reports.all, "category-chart", filters] as const,
    budget: (filters?: Record<string, string>) =>
      [...queryKeys.reports.all, "budget", filters] as const,
    itemsTop: (filters?: Record<string, string>) =>
      [...queryKeys.reports.all, "items-top", filters] as const,
    itemsPriceHistory: (name: string) =>
      [...queryKeys.reports.all, "items-price-history", name] as const,
    itemsMonthlyBasket: (filters?: Record<string, string>) =>
      [...queryKeys.reports.all, "items-monthly-basket", filters] as const,
    itemsByCategory: (filters?: Record<string, string>) =>
      [...queryKeys.reports.all, "items-by-category", filters] as const,
    itemsVelocity: (filters?: Record<string, string>) =>
      [...queryKeys.reports.all, "items-velocity", filters] as const,
    itemsPriceComparison: (name: string) =>
      [...queryKeys.reports.all, "items-price-comparison", name] as const,
    inflationPersonal: (filters?: Record<string, string>) =>
      [...queryKeys.reports.all, "inflation-personal", filters] as const,
    inflationSpikes: (filters?: Record<string, string>) =>
      [...queryKeys.reports.all, "inflation-spikes", filters] as const,
    itemsBestStores: (filters?: Record<string, string>) =>
      [...queryKeys.reports.all, "items-best-stores", filters] as const,
  },

  installments: {
    all: ["installments"] as const,
    plans: (walletId?: number) => [...queryKeys.installments.all, "plans", walletId] as const,
    planDetail: (id: number) =>
      [...queryKeys.installments.all, "plan", id] as const,
    upcoming: () => [...queryKeys.installments.all, "upcoming"] as const,
    overdue: () => [...queryKeys.installments.all, "overdue"] as const,
    debt: () => [...queryKeys.installments.all, "debt"] as const,
  },

  checks: {
    all: ["checks"] as const,
    list: (filters?: Record<string, string>) =>
      [...queryKeys.checks.all, "list", filters] as const,
    detail: (id: number) => [...queryKeys.checks.all, "detail", id] as const,
    upcoming: () => [...queryKeys.checks.all, "upcoming"] as const,
  },

  debts: {
    all: ["debts"] as const,
    list: (filters?: Record<string, string>) =>
      [...queryKeys.debts.all, "list", filters] as const,
    detail: (id: number) => [...queryKeys.debts.all, "detail", id] as const,
    payments: (id: number) =>
      [...queryKeys.debts.all, "payments", id] as const,
    history: (id: number) =>
      [...queryKeys.debts.all, "history", id] as const,
    summary: (filters?: Record<string, string>) => [...queryKeys.debts.all, "summary", filters] as const,
    overdue: (filters?: Record<string, string>) => [...queryKeys.debts.all, "overdue", filters] as const,
    dueSoon: (filters?: Record<string, string>) => [...queryKeys.debts.all, "due-soon", filters] as const,
    counterparty: (name: string) =>
      [...queryKeys.debts.all, "counterparty", name] as const,
    aging: () => [...queryKeys.debts.all, "aging"] as const,
    monthlyRepayments: () =>
      [...queryKeys.debts.all, "monthly-repayments"] as const,
    topCounterparties: () =>
      [...queryKeys.debts.all, "top-counterparties"] as const,
  },

  exchangeRates: {
    all: ["exchange-rates"] as const,
    list: () => [...queryKeys.exchangeRates.all, "list"] as const,
    currencies: () => [...queryKeys.exchangeRates.all, "currencies"] as const,
  },

  metadata: {
    all: ["metadata"] as const,
    contacts: () => [...queryKeys.metadata.all, "contacts"] as const,
    contactDetail: (id: number) =>
      [...queryKeys.metadata.all, "contact", id] as const,
    tags: () => [...queryKeys.metadata.all, "tags"] as const,
    tagDetail: (id: number) =>
      [...queryKeys.metadata.all, "tag", id] as const,
    transactionTags: (txId: number) =>
      [...queryKeys.metadata.all, "tx-tags", txId] as const,
    labels: () => [...queryKeys.metadata.all, "labels"] as const,
    labelDetail: (id: number) =>
      [...queryKeys.metadata.all, "label", id] as const,
    transactionLabels: (txId: number) =>
      [...queryKeys.metadata.all, "tx-labels", txId] as const,
    walletLabels: (walletId: number) =>
      [...queryKeys.metadata.all, "wallet-labels", walletId] as const,
    sourceLabels: (sourceId: number) =>
      [...queryKeys.metadata.all, "source-labels", sourceId] as const,
  },
} as const;
