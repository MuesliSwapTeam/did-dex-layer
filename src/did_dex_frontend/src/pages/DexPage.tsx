import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Box } from '@mui/material';
import CandlestickChartIcon from '@mui/icons-material/CandlestickChart';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip as ChartTooltip,
  XAxis,
  YAxis
} from 'recharts';
import { api } from '../api';
import { fallbackConfig } from '../configDefaults';
import { formatNumber, formatPrice } from '../format';
import { PREPROD_WALLET_ERROR, signAndSubmit } from '../wallet';
import type { Order, TxBuildResponse, WalletState } from '../types';

function fmt(value: number | null | undefined, maximumFractionDigits = 6) {
  return formatNumber(value, maximumFractionDigits);
}

function compact(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return '-';
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 2,
    notation: Math.abs(value) >= 10000 ? 'compact' : 'standard'
  }).format(value);
}

function decimalInputValue(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return '';
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 12,
    useGrouping: false
  }).format(value);
}

function short(value: string | undefined, start = 10, end = 6) {
  if (!value) return '-';
  if (value.length <= start + end) return value;
  return `${value.slice(0, start)}...${value.slice(-end)}`;
}

export default function DexPage({
  wallet
}: {
  wallet?: WalletState;
  setWallet: (wallet?: WalletState) => void;
}) {
  const queryClient = useQueryClient();
  const { pairId: routePairId } = useParams();
  const config = useQuery({ queryKey: ['config'], queryFn: api.config });
  const appConfig = config.data ?? fallbackConfig;
  const pairId = routePairId ?? appConfig.pairs[0]?.id ?? 'muesli-swap';
  const [ticket, setTicket] = useState({
    side: 'sell_quote' as 'sell_base' | 'sell_quote',
    sellAmount: 100,
    buyAmount: 300,
    allowPartial: true
  });
  const [tradePanelTab, setTradePanelTab] = useState<'place' | 'open' | 'mine'>('place');
  const [lastTxHash, setLastTxHash] = useState<string | null>(null);

  const orders = useQuery({
    queryKey: ['orders', pairId],
    queryFn: () => api.orders(pairId),
    refetchInterval: 10000
  });
  const analytics = useQuery({
    queryKey: ['analytics', pairId],
    queryFn: () => api.analytics(pairId),
    refetchInterval: 10000
  });
  const trades = useQuery({
    queryKey: ['trades', pairId],
    queryFn: () => api.trades(pairId),
    refetchInterval: 10000
  });
  const did = useQuery({
    queryKey: ['did-status', wallet?.address],
    queryFn: () => api.didCheck(wallet!.address),
    enabled: Boolean(wallet),
    refetchInterval: 10000
  });
  const balance = useQuery({
    queryKey: ['token-balance', wallet?.address, pairId],
    queryFn: () => api.tokenCheck(wallet!.address, pairId),
    enabled: Boolean(wallet),
    refetchInterval: 10000
  });

  const pair = appConfig.pairs.find((item) => item.id === pairId) ?? appConfig.pairs[0];
  const baseTicker = pair?.base.ticker ?? 'BASE';
  const quoteTicker = pair?.quote.ticker ?? 'QUOTE';
  const requiredDidPolicyId = appConfig.didPolicyId.toLowerCase();
  const walletDidPolicyId = did.data?.policyId?.toLowerCase();
  const didPolicyMatches = Boolean(walletDidPolicyId && walletDidPolicyId === requiredDidPolicyId);
  const hasRequiredDid = Boolean(wallet && did.data?.hasDid && didPolicyMatches);
  const canTrade = hasRequiredDid;
  const didStatusClass = !wallet || did.isLoading
    ? 'pending'
    : canTrade
      ? 'verified'
      : 'missing';
  const didStatusMessage = !wallet
    ? 'Connect a Preprod wallet to trade.'
    : did.isLoading
      ? 'Checking wallet DID NFT...'
    : canTrade
        ? 'Valid DID NFT policy detected. Trading is enabled.'
        : did.data?.hasDid && !didPolicyMatches
          ? `Wallet DID policy mismatch. Required ${short(appConfig.didPolicyId, 10, 6)}.`
        : did.data?.addressValid === false
          ? did.data.error ?? PREPROD_WALLET_ERROR
        : did.error
          ? did.error instanceof Error
            ? did.error.message
            : 'DID status check failed.'
          : did.data?.chainAvailable === false
            ? `DID status unavailable: ${did.data.error ?? 'chain index is not reachable.'}`
            : 'Trading requires a valid DID NFT in the connected wallet.';
  const allOrders = orders.data?.orders ?? [];
  const recentFills = trades.data?.trades ?? analytics.data?.recentFills ?? [];
  const chartData = analytics.data?.history?.length
    ? analytics.data.history
    : recentFills
      .slice()
      .reverse()
      .map((fill) => ({ time: fill.time, price: fill.price, volume: fill.amount }));
  const myOrders = useMemo(
    () => allOrders.filter((order) => order.ownerAddress === wallet?.address),
    [allOrders, wallet?.address]
  );

  const depth = useMemo(() => {
    const analyticsBids = analytics.data?.depth.bids ?? [];
    const analyticsAsks = analytics.data?.depth.asks ?? [];
    const fallbackBids = allOrders
      .filter((order) => order.side === 'sell_quote')
      .map((order) => ({ price: order.price, amount: order.buyAmount }));
    const fallbackAsks = allOrders
      .filter((order) => order.side === 'sell_base')
      .map((order) => ({ price: order.price, amount: order.sellAmount }));
    const bids = (analyticsBids.length ? analyticsBids : fallbackBids)
      .slice()
      .sort((left, right) => right.price - left.price)
      .slice(0, 12);
    const asks = (analyticsAsks.length ? analyticsAsks : fallbackAsks)
      .slice()
      .sort((left, right) => left.price - right.price)
      .slice(0, 12);
    const maxAmount = Math.max(1, ...bids.map((item) => item.amount), ...asks.map((item) => item.amount));
    return { bids, asks, maxAmount };
  }, [allOrders, analytics.data?.depth.asks, analytics.data?.depth.bids]);

  const bestBid = depth.bids[0]?.price ?? null;
  const bestAsk = depth.asks[0]?.price ?? null;
  const computedSpread = bestBid !== null && bestAsk !== null ? bestAsk - bestBid : null;
  const spread = analytics.data?.spread ?? computedSpread;
  const latestPoint = chartData.length ? chartData[chartData.length - 1] : undefined;
  const lastPrice = latestPoint?.price ?? (bestBid !== null && bestAsk !== null ? (bestBid + bestAsk) / 2 : allOrders[0]?.price);
  const isBuy = ticket.side === 'sell_quote';
  const sellTicker = isBuy ? quoteTicker : baseTicker;
  const buyTicker = isBuy ? baseTicker : quoteTicker;
  const ticketRate = ticket.sellAmount > 0 ? ticket.buyAmount / ticket.sellAmount : null;
  const balanceError = balance.error instanceof Error ? balance.error.message : 'Wallet balance check failed.';
  const baseBalance = balance.data?.base.amount ?? 0;
  const quoteBalance = balance.data?.quote.amount ?? 0;
  const sellBalance = isBuy ? quoteBalance : baseBalance;
  const hasValidTicketAmounts = ticket.sellAmount > 0 && ticket.buyAmount > 0;
  const ticketBalanceLoaded = Boolean(wallet) && balance.isSuccess;
  const ticketHasEnoughBalance = ticketBalanceLoaded && sellBalance >= ticket.sellAmount;
  const ticketBalanceMessage = !wallet
    ? undefined
    : balance.isLoading
      ? 'Checking wallet balance...'
      : balance.isError
        ? balanceError
        : !ticketHasEnoughBalance
          ? `Insufficient ${sellTicker}: available ${fmt(sellBalance)}, required ${fmt(ticket.sellAmount)}.`
          : undefined;
  const placeDisabledReason = !canTrade
    ? didStatusMessage
    : !hasValidTicketAmounts
      ? 'Enter positive sell and buy amounts.'
      : !ticketBalanceLoaded
        ? ticketBalanceMessage ?? 'Checking wallet balance...'
        : !ticketHasEnoughBalance
          ? ticketBalanceMessage
          : undefined;

  const requiredFill = (order: Order) => {
    const ticker = order.side === 'sell_base' ? quoteTicker : baseTicker;
    const available = order.side === 'sell_base' ? quoteBalance : baseBalance;
    return {
      amount: order.buyAmount,
      available,
      ticker,
      hasEnough: balance.isSuccess && available >= order.buyAmount
    };
  };

  const fillDisabledReason = (order: Order) => {
    if (did.isLoading) return 'Checking DID policy...';
    if (!canTrade) return didStatusMessage;
    if (balance.isLoading) return 'Checking wallet balance...';
    if (balance.isError) return balanceError;
    const requirement = requiredFill(order);
    if (!requirement.hasEnough) {
      return `Insufficient ${requirement.ticker}: available ${fmt(requirement.available)}, required ${fmt(requirement.amount)}.`;
    }
    return undefined;
  };

  const submitTx = async (txFactory: () => Promise<TxBuildResponse>) => {
    if (!wallet) throw new Error('Connect a wallet first.');
    if (!hasRequiredDid) throw new Error(didStatusMessage);
    setLastTxHash(null);
    const tx = await txFactory();
    const hash = await signAndSubmit(wallet, tx.cborHex);
    setLastTxHash(hash);
    if (tx.event) {
      await api.confirmTx(wallet.address, hash, tx.event);
    }
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['orders'] }),
      queryClient.invalidateQueries({ queryKey: ['analytics'] }),
      queryClient.invalidateQueries({ queryKey: ['trades'] }),
      queryClient.invalidateQueries({ queryKey: ['did-status'] }),
      queryClient.invalidateQueries({ queryKey: ['token-balance'] })
    ]);
    return hash;
  };

  const placeMutation = useMutation({
    mutationFn: () => {
      if (placeDisabledReason) throw new Error(placeDisabledReason);
      return submitTx(() =>
        api.placeOrder({ walletAddress: wallet!.address, pairId, ...ticket })
      );
    }
  });
  const cancelMutation = useMutation({
    mutationFn: (orderRef: string) => submitTx(() => api.cancelOrder(wallet!.address, orderRef, pairId))
  });
  const fillMutation = useMutation({
    mutationFn: (orderRef: string) => {
      const order = allOrders.find((item) => item.ref === orderRef);
      if (!order) throw new Error('Order not found.');
      const disabledReason = fillDisabledReason(order);
      if (disabledReason) throw new Error(disabledReason);
      return submitTx(() => api.fillOrder(wallet!.address, orderRef, pairId));
    }
  });

  const actionError = placeMutation.error || cancelMutation.error || fillMutation.error;
  const actionPending = placeMutation.isPending || cancelMutation.isPending || fillMutation.isPending;
  const displayedOrders = tradePanelTab === 'mine' ? myOrders : allOrders;

  // Running totals for order book
  const askTotals = useMemo(() => {
    const result: number[] = [];
    let sum = 0;
    for (const item of [...depth.asks].reverse()) {
      sum += item.amount;
      result.unshift(sum);
    }
    return result;
  }, [depth.asks]);

  const bidTotals = useMemo(() => {
    const result: number[] = [];
    let sum = 0;
    for (const item of depth.bids) {
      sum += item.amount;
      result.push(sum);
    }
    return result;
  }, [depth.bids]);

  const totalMax = Math.max(
    1,
    askTotals.length ? askTotals[0] : 0,
    bidTotals.length ? bidTotals[bidTotals.length - 1] : 0
  );

  return (
    <Box className="dex-page">
      {/* Ticker bar */}
      <div className="ticker-bar">
        <div className="ticker-pair policy-tooltip-anchor">
          <div className="ticker-pair-icon">{baseTicker.slice(0, 2)}</div>
          <span className="ticker-pair-name">
            {baseTicker}/{quoteTicker}
          </span>
          <div className="policy-tooltip">
            <div className="policy-row">
              <span className="policy-label">{baseTicker}</span>
              <span className="policy-value">{pair?.base.policy_id ?? '-'}</span>
            </div>
            <div className="policy-row">
              <span className="policy-label">{quoteTicker}</span>
              <span className="policy-value">{pair?.quote.policy_id ?? '-'}</span>
            </div>
          </div>
        </div>
        <div className="ticker-divider" />
        <div className="ticker-stat">
          <div className="t-label">Last Price</div>
          <div className={`t-value ${lastPrice ? 'green' : ''}`}>{formatPrice(lastPrice)}</div>
        </div>
        <div className="ticker-divider" />
        <div className="ticker-stat">
          <div className="t-label">Best Bid</div>
          <div className="t-value green">{formatPrice(bestBid)}</div>
        </div>
        <div className="ticker-stat">
          <div className="t-label">Best Ask</div>
          <div className="t-value red">{formatPrice(bestAsk)}</div>
        </div>
        <div className="ticker-divider" />
        <div className="ticker-stat">
          <div className="t-label">Spread</div>
          <div className="t-value">{formatPrice(spread)}</div>
        </div>
        <div className="ticker-stat">
          <div className="t-label">Open Orders</div>
          <div className="t-value">{allOrders.length}</div>
        </div>
        <div className="ticker-divider" />
        <div className="ticker-stat">
          <div className="t-label">Network</div>
          <div className="t-value">{appConfig.network.toUpperCase()}</div>
        </div>
      </div>

      {/* Three-column trading grid */}
      <div className="trading-grid">
        {/* Left: Order book */}
        <div className="orderbook-panel">
          <div className="orderbook-header">
            <span>Order Book</span>
          </div>
          <div className="orderbook-col-headers">
            <span>Price ({quoteTicker})</span>
            <span>Amount</span>
            <span>Total</span>
          </div>
          <div className="orderbook-asks">
            {depth.asks.map((item, i) => (
              <div className="ob-row ask" key={`ask-${item.price}-${item.amount}`}>
                <div className="ob-fill" style={{ width: `${(askTotals[i] / totalMax) * 100}%` }} />
                <span className="ob-price">{formatPrice(item.price)}</span>
                <span className="ob-amount">{compact(item.amount)}</span>
                <span className="ob-total">{compact(askTotals[i])}</span>
              </div>
            ))}
          </div>
          <div className="orderbook-mid">
            <span className={`mid-val ${lastPrice && bestBid && lastPrice >= bestBid ? 'green' : lastPrice ? 'red' : 'neutral'}`}>
              {formatPrice(lastPrice)}
            </span>
            <span className="mid-label">{quoteTicker}</span>
          </div>
          <div className="orderbook-bids">
            {depth.bids.map((item, i) => (
              <div className="ob-row bid" key={`bid-${item.price}-${item.amount}`}>
                <div className="ob-fill" style={{ width: `${(bidTotals[i] / totalMax) * 100}%` }} />
                <span className="ob-price">{formatPrice(item.price)}</span>
                <span className="ob-amount">{compact(item.amount)}</span>
                <span className="ob-total">{compact(bidTotals[i])}</span>
              </div>
            ))}
          </div>
          {!depth.asks.length && !depth.bids.length && (
            <div className="empty-orders">No orders in the book yet.</div>
          )}
        </div>

        {/* Center: Chart */}
        <div className="chart-panel">
          <div className="chart-toolbar">
            <button className="active">Price</button>
          </div>
          <div className="chart-area">
            <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="priceFill" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                <XAxis dataKey="time" hide />
                <YAxis
                  width={50}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: '#52525b', fontSize: 11 }}
                  domain={['auto', 'auto']}
                />
                <ChartTooltip
                  contentStyle={{
                    background: '#18181b',
                    border: '1px solid #27272a',
                    borderRadius: 6,
                    color: '#fafafa',
                    fontSize: 12
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="price"
                  stroke="#6366f1"
                  strokeWidth={2}
                  fill="url(#priceFill)"
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
            {!chartData.length && (
              <div className="chart-empty">
                <CandlestickChartIcon />
                <div style={{ fontWeight: 500 }}>Waiting for trade history</div>
                <div style={{ fontSize: '0.75rem' }}>Price data will appear after fills are indexed.</div>
              </div>
            )}
          </div>
        </div>

        {/* Right: Last trades */}
        <div className="trades-panel">
          <div className="trades-header">
            <span>Last Trades</span>
          </div>
          <div className="trades-col-headers">
            <span>Price ({quoteTicker})</span>
            <span>Amount ({baseTicker})</span>
            <span>Time</span>
          </div>
          <div className="trades-list">
            {recentFills.map((fill) => (
              <div className="trade-row" key={`${fill.txHash}-${fill.time}`}>
                <span className="trade-price">{formatPrice(fill.price)}</span>
                <span className="trade-amount">{compact(fill.amount)}</span>
                <span className="trade-time">
                  {new Date(fill.time).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit'
                  })}
                </span>
              </div>
            ))}
            {!recentFills.length && (
              <div className="empty-orders">No recent trades yet.</div>
            )}
          </div>
        </div>

        {/* Right: Trading panel */}
        <div className="order-panel">
          <div className="order-panel-header">
            <button
              className={`order-panel-tab ${tradePanelTab === 'place' ? 'active' : ''}`}
              onClick={() => setTradePanelTab('place')}
            >
              Place Order
            </button>
            <button
              className={`order-panel-tab ${tradePanelTab === 'open' ? 'active' : ''}`}
              onClick={() => setTradePanelTab('open')}
            >
              Open Orders
              <span className="tab-count">{allOrders.length}</span>
            </button>
            <button
              className={`order-panel-tab ${tradePanelTab === 'mine' ? 'active' : ''}`}
              onClick={() => setTradePanelTab('mine')}
            >
              My Orders
              <span className="tab-count">{myOrders.length}</span>
            </button>
          </div>
          <div className={`did-status-bar ${didStatusClass}`}>
            {didStatusMessage}
          </div>

          {tradePanelTab === 'place' ? (
            <>
              {/* Buy / Sell toggle */}
              <div className="side-toggle-bar">
                <button
                  className={`side-btn buy ${isBuy ? '' : 'inactive'}`}
                  onClick={() => setTicket({ ...ticket, side: 'sell_quote' })}
                >
                  Buy {baseTicker}
                </button>
                <button
                  className={`side-btn sell ${!isBuy ? '' : 'inactive'}`}
                  onClick={() => setTicket({ ...ticket, side: 'sell_base' })}
                >
                  Sell {baseTicker}
                </button>
              </div>

              <div className="order-form">
                <div className="order-input-group">
                  <label>Price</label>
                  <input
                    type="number"
                    value={decimalInputValue(ticketRate)}
                    onChange={(e) => {
                      const rate = Number(e.target.value);
                      if (rate > 0) {
                        setTicket({ ...ticket, buyAmount: Math.round(ticket.sellAmount * rate * 100) / 100 });
                      }
                    }}
                  />
                  <span className="unit">{buyTicker}/{sellTicker}</span>
                </div>
                <div className="order-input-group">
                  <label>Sell</label>
                  <input
                    type="number"
                    value={ticket.sellAmount}
                    onChange={(e) => setTicket({ ...ticket, sellAmount: Number(e.target.value) })}
                  />
                  <span className="unit">{sellTicker}</span>
                </div>
                <div className="order-input-group">
                  <label>Buy</label>
                  <input
                    type="number"
                    value={ticket.buyAmount}
                    onChange={(e) => setTicket({ ...ticket, buyAmount: Number(e.target.value) })}
                  />
                  <span className="unit">{buyTicker}</span>
                </div>

                <div className="order-preview">
                  <span>Rate</span>
                  <strong>{formatPrice(ticketRate)} {buyTicker}/{sellTicker}</strong>
                </div>
                <div className={`order-preview ${ticketBalanceMessage ? 'balance-warning' : ''}`}>
                  <span>Wallet</span>
                  <strong>{fmt(sellBalance)} {sellTicker}</strong>
                </div>
                {ticketBalanceMessage && (
                  <div className="balance-check-message">{ticketBalanceMessage}</div>
                )}

                <button
                  className={`place-order-btn ${isBuy ? 'buy-btn' : 'sell-btn'}`}
                  disabled={Boolean(placeDisabledReason) || actionPending}
                  title={placeDisabledReason}
                  onClick={() => placeMutation.mutate()}
                >
                  {placeMutation.isPending
                    ? 'Submitting...'
                    : !canTrade
                      ? 'DID NFT Required'
                    : !hasValidTicketAmounts
                      ? 'Enter Amount'
                    : placeDisabledReason
                      ? 'Insufficient Balance'
                    : isBuy
                      ? `Buy ${baseTicker}`
                      : `Sell ${baseTicker}`}
                </button>

                {actionError && (
                  <div className="tx-alert error">
                    {actionError instanceof Error ? actionError.message : 'Transaction failed'}
                  </div>
                )}
                {lastTxHash && (
                  <div className="tx-alert success">
                    Submitted transaction {short(lastTxHash, 12, 8)}
                  </div>
                )}
              </div>
            </>
          ) : (
            <>
              <div className="orders-table-wrap in-order-panel">
                <table className="orders-table">
                  <thead>
                    <tr>
                      <th>Side</th>
                      <th>Price</th>
                      <th>Sell</th>
                      <th>Buy</th>
                      <th>Owner</th>
                      <th style={{ textAlign: 'right' }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {displayedOrders.map((order: Order) => {
                      const isAsk = order.side === 'sell_base';
                      const isMine = order.ownerAddress === wallet?.address;
                      const isCancelling = cancelMutation.isPending && cancelMutation.variables === order.ref;
                      const isFilling = fillMutation.isPending && fillMutation.variables === order.ref;
                      const requirement = requiredFill(order);
                      const disabledReason = fillDisabledReason(order);
                      return (
                        <tr key={order.ref}>
                          <td style={{ color: isAsk ? '#ef4444' : '#22c55e', fontWeight: 500 }}>
                            {isAsk ? 'Ask' : 'Bid'}
                          </td>
                          <td style={{ color: isAsk ? '#ef4444' : '#22c55e', fontVariantNumeric: 'tabular-nums' }}>
                            {formatPrice(order.price)}
                          </td>
                          <td>{fmt(order.sellAmount)} {isAsk ? baseTicker : quoteTicker}</td>
                          <td>{fmt(order.buyAmount)} {isAsk ? quoteTicker : baseTicker}</td>
                          <td className="mono" style={{ color: '#52525b' }}>{short(order.ownerAddress, 10, 6)}</td>
                          <td style={{ textAlign: 'right' }}>
                            {isMine ? (
                              <button
                                className="action-btn cancel-btn"
                                disabled={!canTrade || actionPending}
                                title={!canTrade ? didStatusMessage : undefined}
                                onClick={() => cancelMutation.mutate(order.ref)}
                              >
                                {isCancelling ? 'Cancelling...' : 'Cancel'}
                              </button>
                            ) : (
                              <button
                                className="action-btn fill-btn"
                                disabled={Boolean(disabledReason) || actionPending}
                                title={disabledReason ?? `Requires ${fmt(requirement.amount)} ${requirement.ticker}.`}
                                onClick={() => fillMutation.mutate(order.ref)}
                              >
                                {isFilling
                                  ? 'Filling...'
                                  : !canTrade
                                    ? 'DID NFT Required'
                                    : disabledReason
                                      ? 'No Balance'
                                      : 'Fill'}
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                    {!displayedOrders.length && (
                      <tr>
                        <td colSpan={6} className="empty-orders">
                          {tradePanelTab === 'mine' ? 'You have no open orders.' : 'No open orders for this pair.'}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              {actionError && (
                <div className="tx-alert error">
                  {actionError instanceof Error ? actionError.message : 'Transaction failed'}
                </div>
              )}
              {lastTxHash && (
                <div className="tx-alert success">
                  Submitted transaction {short(lastTxHash, 12, 8)}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </Box>
  );
}
