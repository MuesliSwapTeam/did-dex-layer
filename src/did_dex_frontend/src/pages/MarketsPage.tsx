import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueries, useQuery } from '@tanstack/react-query';
import { Box, Container } from '@mui/material';
import VerifiedIcon from '@mui/icons-material/Verified';
import { api } from '../api';
import { fallbackConfig } from '../configDefaults';
import { formatNumber, formatPrice } from '../format';
import type { PairConfig } from '../types';

function fmt(value: number | null | undefined, maximumFractionDigits = 6) {
  return formatNumber(value, maximumFractionDigits);
}

function toTitleCase(value: string) {
  if (!value) return value;
  return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase();
}

export default function MarketsPage() {
  const navigate = useNavigate();
  const config = useQuery({ queryKey: ['config'], queryFn: api.config });
  const appConfig = config.data ?? fallbackConfig;
  const pairs = appConfig.pairs;
  const [search, setSearch] = useState('');
  const analyticsQueries = useQueries({
    queries: pairs.map((pair) => ({
      queryKey: ['analytics', pair.id],
      queryFn: () => api.analytics(pair.id),
      refetchInterval: 15000
    }))
  });

  const totalVolume = analyticsQueries.reduce((sum, query) => {
    const pairVolume = query.data?.volume24h;
    if (pairVolume !== undefined) return sum + pairVolume;
    const history = query.data?.history ?? [];
    const fallbackVolume = history.reduce((acc, entry) => acc + entry.volume, 0);
    return sum + fallbackVolume;
  }, 0);

  const totalTrades = analyticsQueries.reduce((sum, query) => {
    const pairTrades = query.data?.tradeCount24h;
    if (pairTrades !== undefined) return sum + pairTrades;
    const fills = query.data?.recentFills ?? [];
    return sum + fills.length;
  }, 0);

  const filtered = pairs.filter((pair) => {
    const text = `${pair.base.ticker} ${pair.quote.ticker} ${pair.id}`.toLowerCase();
    return text.includes(search.toLowerCase());
  });

  return (
    <Box className="markets-page">
      <Container maxWidth="lg" disableGutters>
        <div className="markets-stat-bar">
          <div className="stat-card">
            <div className="stat-label">Markets</div>
            <div className="stat-value">{pairs.length}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Network</div>
            <div className="stat-value">{toTitleCase(appConfig.network)}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Volume</div>
            <div className="stat-value">{fmt(totalVolume, 2)}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Number of trades</div>
            <div className="stat-value">{fmt(totalTrades, 0)}</div>
          </div>
        </div>

        <div className="markets-search">
          <input
            type="text"
            placeholder="Search markets..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="markets-table-wrap">
          <table className="markets-table">
            <thead>
              <tr>
                <th>Pair</th>
                <th>Last Price</th>
                <th>24h Change</th>
                <th>Best Bid</th>
                <th>Best Ask</th>
                <th>Spread</th>
                <th style={{ textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((pair: PairConfig) => (
                <PairRow key={pair.id} pair={pair} onClick={() => navigate(`/markets/${pair.id}`)} />
              ))}
              {!filtered.length && (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '40px 16px', color: '#52525b' }}>
                    {search ? 'No markets match your search.' : 'No markets configured.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Container>
    </Box>
  );
}

function PairRow({ pair, onClick }: { pair: PairConfig; onClick: () => void }) {
  const analytics = useQuery({
    queryKey: ['analytics', pair.id],
    queryFn: () => api.analytics(pair.id),
    refetchInterval: 15000
  });

  const data = analytics.data;
  const bids = data?.depth.bids ?? [];
  const asks = data?.depth.asks ?? [];
  const bestBid = bids.length ? Math.max(...bids.map((b) => b.price)) : null;
  const bestAsk = asks.length ? Math.min(...asks.map((a) => a.price)) : null;
  const spread = bestBid !== null && bestAsk !== null ? bestAsk - bestBid : data?.spread ?? null;
  const history = data?.history ?? [];
  const lastPrice = history.length ? history[history.length - 1].price : bestBid && bestAsk ? (bestBid + bestAsk) / 2 : null;
  const firstPrice = history.length >= 2 ? history[0].price : null;
  const change = lastPrice && firstPrice ? ((lastPrice - firstPrice) / firstPrice) * 100 : null;

  return (
    <tr onClick={onClick}>
      <td>
        <div className="pair-name policy-tooltip-anchor">
          <div className="pair-icon">{pair.base.ticker.slice(0, 2)}</div>
          <div className="pair-label">
            <strong>{pair.base.ticker}</strong>
            <span>/ {pair.quote.ticker}</span>
            <small>
              <VerifiedIcon sx={{ fontSize: 10, verticalAlign: 'middle', mr: 0.3, color: '#6366f1' }} />
              DID settlement
            </small>
          </div>
          <div className="policy-tooltip">
            <div className="policy-row">
              <span className="policy-label">{pair.base.ticker}</span>
              <span className="policy-value">{pair.base.policy_id}</span>
            </div>
            <div className="policy-row">
              <span className="policy-label">{pair.quote.ticker}</span>
              <span className="policy-value">{pair.quote.policy_id}</span>
            </div>
          </div>
        </div>
      </td>
      <td style={{ fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>
        {formatPrice(lastPrice)}
      </td>
      <td>
        <span className={change === null ? 'change-neutral' : change >= 0 ? 'change-positive' : 'change-negative'}>
          {change !== null ? `${change >= 0 ? '+' : ''}${change.toFixed(2)}%` : '-'}
        </span>
      </td>
      <td style={{ fontVariantNumeric: 'tabular-nums', color: '#22c55e' }}>
        {formatPrice(bestBid)}
      </td>
      <td style={{ fontVariantNumeric: 'tabular-nums', color: '#ef4444' }}>
        {formatPrice(bestAsk)}
      </td>
      <td style={{ fontVariantNumeric: 'tabular-nums', color: '#71717a' }}>
        {formatPrice(spread)}
      </td>
      <td style={{ textAlign: 'right' }}>
        <button className="trade-btn" onClick={(e) => { e.stopPropagation(); onClick(); }}>
          Trade
        </button>
      </td>
    </tr>
  );
}
