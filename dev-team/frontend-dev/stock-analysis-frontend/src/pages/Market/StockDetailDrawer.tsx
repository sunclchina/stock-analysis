import React, { useMemo } from 'react';
import {
  Drawer,
  Spin,
  Typography,
  Tag,
  Descriptions,
  Divider,
  Tabs,
  Row,
  Col,
  Statistic,
  Empty,
  Space,
} from 'antd';
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  MinusOutlined,
  ReloadOutlined,
  BarChartOutlined,
  LineChartOutlined,
  DashboardOutlined,
} from '@ant-design/icons';
import ReactEChartsCore from 'echarts-for-react';
import type {
  StockQuote,
  KLineData,
  TimeShareData,
  TechnicalIndicators,
} from '../../types/market';

const { Text } = Typography;

interface StockDetailDrawerProps {
  open: boolean;
  loading: boolean;
  quote: StockQuote | null;
  kline: KLineData | null;
  timeshare: TimeShareData | null;
  indicators: TechnicalIndicators | null;
  onClose: () => void;
  onRefresh: () => void;
}

function changeColor(val: number): string {
  if (val > 0) return '#cf1322';
  if (val < 0) return '#389e0d';
  return '#8c8c8c';
}

/** 格式化 */
function formatVolume(v: number): string {
  if (v == null || isNaN(v)) return '—';
  if (v >= 100000000) return (v / 100000000).toFixed(2) + '亿';
  if (v >= 10000) return (v / 10000).toFixed(2) + '万';
  return v.toFixed(0);
}

/** K线图配置 */
function getKlineOption(data: KLineData | null): Record<string, unknown> {
  if (!data || !data.dataPoints || data.dataPoints.length === 0) {
    return {};
  }

  const dates = data.dataPoints.map((p) => p.date);
  const ohlc = data.dataPoints.map((p) => [p.open, p.close, p.low, p.high]);
  const volumes = data.dataPoints.map((p) => p.volume);

  // Determine up/down colors
  const upColors = ohlc.map(([open, close]) => (close >= open ? 1 : -1));

  const series: Record<string, unknown>[] = [
    {
      name: 'K线',
      type: 'candlestick',
      data: ohlc,
      itemStyle: {
        color: '#cf1322',
        color0: '#389e0d',
        borderColor: '#cf1322',
        borderColor0: '#389e0d',
      },
    },
  ];

  // Add MA lines if available
  if (data.ma5 && data.ma5.length > 0) {
    series.push({
      name: 'MA5',
      type: 'line',
      data: data.ma5,
      smooth: true,
      lineStyle: { width: 1, color: '#1677ff' },
      symbol: 'none',
    });
  }
  if (data.ma10 && data.ma10.length > 0) {
    series.push({
      name: 'MA10',
      type: 'line',
      data: data.ma10,
      smooth: true,
      lineStyle: { width: 1, color: '#faad14' },
      symbol: 'none',
    });
  }
  if (data.ma20 && data.ma20.length > 0) {
    series.push({
      name: 'MA20',
      type: 'line',
      data: data.ma20,
      smooth: true,
      lineStyle: { width: 1, color: '#eb2f96' },
      symbol: 'none',
    });
  }

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
    },
    grid: [
      { left: '8%', right: '8%', top: 60, height: 180 },
      { left: '8%', right: '8%', top: 280, height: 60 },
    ],
    xAxis: [
      {
        type: 'category',
        data: dates,
        axisLine: { onZero: false },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { fontSize: 10, rotate: 30 },
        gridIndex: 0,
      },
      {
        type: 'category',
        data: dates,
        axisTick: { show: false },
        axisLine: { show: false },
        axisLabel: { show: false },
        gridIndex: 1,
      },
    ],
    yAxis: [
      {
        scale: true,
        gridIndex: 0,
        splitArea: { show: true, areaStyle: { color: ['rgba(0,0,0,0.01)', 'rgba(0,0,0,0.02)'] } },
        axisLabel: { fontSize: 10 },
      },
      {
        scale: true,
        gridIndex: 1,
        splitNumber: 2,
        axisLabel: { show: false },
        axisLine: { show: false },
      },
    ],
    series: [
      ...series,
      {
        name: '成交量',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumes.map((v, i) => ({
          value: v,
          itemStyle: {
            color: upColors[i] > 0 ? '#cf1322' : '#389e0d',
          },
        })),
      },
    ],
  };
}

/** 分时图配置 */
function getTimeshareOption(data: TimeShareData | null): Record<string, unknown> {
  if (!data || !data.points || data.points.length === 0) {
    return {};
  }

  const times = data.points.map((p) => p.time);
  const prices = data.points.map((p) => p.price);
  // 兼容 snake_case (avg_price) 和 camelCase (avgPrice)
  const avgPrices = data.points.map((p) => p.avgPrice ?? p.avg_price);
  const volumes = data.points.map((p) => p.volume ?? 0);

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
    },
    legend: { data: ['价格', '均价', '成交量'], bottom: 0 },
    grid: [
      { left: '8%', right: '8%', top: 10, height: 200 },
      { left: '8%', right: '8%', top: 260, height: 60 },
    ],
    xAxis: [
      {
        type: 'category',
        data: times,
        axisLabel: { fontSize: 10, rotate: 30, interval: Math.max(1, Math.floor(times.length / 8)) },
        gridIndex: 0,
        axisLine: { onZero: false },
      },
      {
        type: 'category',
        data: times,
        axisTick: { show: false },
        axisLine: { show: false },
        axisLabel: { show: false },
        gridIndex: 1,
      },
    ],
    yAxis: [
      { scale: true, gridIndex: 0, axisLabel: { fontSize: 10 } },
      { scale: true, gridIndex: 1, axisLabel: { show: false }, axisLine: { show: false } },
    ],
    series: [
      {
        name: '价格',
        type: 'line',
        data: prices,
        smooth: true,
        lineStyle: { width: 1.5, color: '#1677ff' },
        areaStyle: { color: 'rgba(22,119,255,0.1)' },
        symbol: 'none',
      },
      {
        name: '均价',
        type: 'line',
        data: avgPrices,
        smooth: true,
        lineStyle: { width: 1, color: '#faad14', type: 'dashed' },
        symbol: 'none',
      },
      {
        name: '成交量',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumes,
        itemStyle: { color: 'rgba(22,119,255,0.3)' },
        symbol: 'none',
      },
    ],
  };
}

/** 市值格式 */
function formatMarketCap(val: number): string {
  if (val == null || isNaN(val)) return '—';
  if (val >= 100000000) return (val / 100000000).toFixed(2) + '亿';
  if (val >= 10000) return (val / 10000).toFixed(2) + '万';
  return val.toFixed(0);
}

/** 个股详情弹窗侧栏 */
const StockDetailDrawer: React.FC<StockDetailDrawerProps> = ({
  open,
  loading,
  quote,
  kline,
  timeshare,
  indicators,
  onClose,
  onRefresh,
}) => {
  console.log('[StockDetailDrawer] render:', { open, loading, hasQuote: !!quote, quoteCode: quote?.code });
  const klineOption = useMemo(() => getKlineOption(kline), [kline]);
  const timeshareOption = useMemo(() => getTimeshareOption(timeshare), [timeshare]);

  const renderQuoteSnapshot = () => {
    if (!quote) return <Empty description="暂无行情数据" />;
    return (
      <div>
        <div
          style={{
            textAlign: 'center',
            padding: '16px 0',
            marginBottom: 12,
            borderRadius: 8,
            background: changeColor(quote.changePercent) === '#cf1322' ? '#fff1f0' : changeColor(quote.changePercent) === '#389e0d' ? '#f6ffed' : '#f5f5f5',
          }}
        >
          <div style={{ fontSize: 32, fontWeight: 700, color: changeColor(quote.changePercent) }}>
            {quote.latestPrice != null ? quote.latestPrice.toFixed(2) : '—'}
          </div>
          <Space size={16} style={{ marginTop: 4 }}>
            <Text style={{ fontSize: 14, color: changeColor(quote.changePercent) }}>
              {quote.changePercent != null ? (quote.changePercent > 0 ? '+' : '') + quote.changePercent.toFixed(2) + '%' : '—'}
            </Text>
            <Text style={{ fontSize: 13, color: changeColor(quote.changePercent) }}>
              {quote.change != null ? (quote.change > 0 ? '+' : '') + quote.change.toFixed(2) : '—'}
            </Text>
          </Space>
        </div>

        <div style={{ overflowX: 'auto', width: '100%' }}>
        <Descriptions size="small" column={{ xs: 1, sm: 2 }} bordered>
          <Descriptions.Item label="今开">{quote.openPrice != null ? quote.openPrice.toFixed(2) : '—'}</Descriptions.Item>
          <Descriptions.Item label="昨收">{quote.prevClose != null ? quote.prevClose.toFixed(2) : '—'}</Descriptions.Item>
          <Descriptions.Item label="最高">{quote.high != null ? quote.high.toFixed(2) : '—'}</Descriptions.Item>
          <Descriptions.Item label="最低">{quote.low != null ? quote.low.toFixed(2) : '—'}</Descriptions.Item>
          <Descriptions.Item label="成交量">{quote.volume != null ? formatVolume(quote.volume) : '—'}</Descriptions.Item>
          <Descriptions.Item label="成交额">{quote.amount != null ? formatVolume(quote.amount) : '—'}</Descriptions.Item>
          <Descriptions.Item label="换手率">{quote.turnoverRate != null && quote.turnoverRate > 0 ? quote.turnoverRate.toFixed(2) + '%' : '-'}</Descriptions.Item>
          <Descriptions.Item label="振幅">{quote.amplitude != null && quote.amplitude > 0 ? quote.amplitude.toFixed(2) + '%' : '-'}</Descriptions.Item>
        </Descriptions>
        </div>
      </div>
    );
  };

  const fmt = (v: any, digits = 2) => v !== null && v !== undefined && v !== 0 ? Number(v).toFixed(digits) : '-';

  const renderTechnicalIndicators = () => {
    if (!indicators) return <Empty description="暂无技术指标" />;
    return (
      <Row gutter={[12, 12]}>
        <Col xs={24}>
          <Text strong style={{ fontSize: 13 }}>移动平均线</Text>
          <Descriptions size="small" column={4} style={{ marginTop: 4 }}>
            <Descriptions.Item label="MA5">{fmt(indicators.ma5)}</Descriptions.Item>
            <Descriptions.Item label="MA10">{fmt(indicators.ma10)}</Descriptions.Item>
            <Descriptions.Item label="MA20">{fmt(indicators.ma20)}</Descriptions.Item>
            <Descriptions.Item label="MA60">{fmt(indicators.ma60)}</Descriptions.Item>
          </Descriptions>
        </Col>
        <Col xs={24}>
          <Text strong style={{ fontSize: 13 }}>MACD</Text>
          <Descriptions size="small" column={3} style={{ marginTop: 4 }}>
            <Descriptions.Item label="DIF">{fmt(indicators.macd?.dif, 4)}</Descriptions.Item>
            <Descriptions.Item label="DEA">{fmt(indicators.macd?.dea, 4)}</Descriptions.Item>
            <Descriptions.Item label="MACD">{fmt(indicators.macd?.macd, 4)}</Descriptions.Item>
          </Descriptions>
        </Col>
        <Col xs={24}>
          <Text strong style={{ fontSize: 13 }}>KDJ</Text>
          <Descriptions size="small" column={3} style={{ marginTop: 4 }}>
            <Descriptions.Item label="K">{fmt(indicators.kdj?.k)}</Descriptions.Item>
            <Descriptions.Item label="D">{fmt(indicators.kdj?.d)}</Descriptions.Item>
            <Descriptions.Item label="J">{fmt(indicators.kdj?.j)}</Descriptions.Item>
          </Descriptions>
        </Col>
        <Col xs={12}>
          <Statistic
            title="RSI"
            value={fmt(indicators.rsi)}
            valueStyle={{ fontSize: 20 }}
          />
        </Col>
        <Col xs={12}>
          <Statistic
            title="量比"
            value={fmt(indicators.volumeRatio)}
            valueStyle={{ fontSize: 20 }}
          />
        </Col>
      </Row>
    );
  };

  const tabItems = [
    {
      key: 'snapshot',
      label: (
        <span><DashboardOutlined /> 行情快照</span>
      ),
      children: renderQuoteSnapshot(),
    },
    {
      key: 'kline',
      label: (
        <span><BarChartOutlined /> K线图</span>
      ),
      children: kline && kline.dataPoints?.length > 0 ? (
        <ReactEChartsCore
          option={klineOption}
          style={{ height: 400 }}
          notMerge
        />
      ) : (
        <Empty description="暂无K线数据" />
      ),
    },
    {
      key: 'timeshare',
      label: (
        <span><LineChartOutlined /> 分时图</span>
      ),
      children: timeshare && timeshare.points?.length > 0 ? (
        <ReactEChartsCore
          option={timeshareOption}
          style={{ height: 380 }}
          notMerge
        />
      ) : (
        <Empty description="暂无分时数据" />
      ),
    },
    {
      key: 'indicators',
      label: (
        <span><DashboardOutlined /> 技术指标</span>
      ),
      children: renderTechnicalIndicators(),
    },
  ];

  return (
    <Drawer
      title={
        quote ? (
          <Space>
            <span style={{ fontSize: 16, fontWeight: 600 }}>{quote.name}</span>
            <Text type="secondary" style={{ fontSize: 13 }}>{quote.code}</Text>
            {quote.isWatchlist && (
              <Tag color="gold" style={{ fontSize: 10 }}>自选</Tag>
            )}
            {quote.market && (
              <Tag style={{ fontSize: 10 }}>{quote.market}</Tag>
            )}
          </Space>
        ) : (
          '个股详情'
        )
      }
      open={open}
      onClose={onClose}
      width={typeof window !== 'undefined' && window.innerWidth < 768 ? '100%' : 600}
      zIndex={1050}
      extra={
        <a onClick={onRefresh} style={{ cursor: 'pointer' }}>
          <ReloadOutlined /> 刷新
        </a>
      }
    >
      <Spin spinning={loading}>
        <Tabs items={tabItems} defaultActiveKey="snapshot" size="small" />
      </Spin>
    </Drawer>
  );
};

export default StockDetailDrawer;
