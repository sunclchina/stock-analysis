/**
 * Warning Monitor Grid
 * NOTE: ASCII-only source to avoid Vite double-encoding bug on Windows.
 * All display text shown to users comes from API response (proper UTF-8).
 */
import React, { useEffect, useState, useCallback } from 'react';
import { Card, Table, Button, Space, Tooltip, Typography, Empty, Spin, Modal } from 'antd';
import { ReloadOutlined, EyeOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { getMonitorPanel, getStockRealtimeWarning } from '../../services/warningApi';
import type { MonitorItem } from '../../services/warningApi';

const { Text } = Typography;

// CSS-based color dots - avoids all unicode/emoji issues
const COLOR_DOT: Record<string, React.CSSProperties> = {
  gray:   { background: '#d9d9d9', borderRadius: '50%', display: 'inline-block', width: 18, height: 18 },
  green:  { background: '#52c41a', borderRadius: '50%', display: 'inline-block', width: 18, height: 18 },
  yellow: { background: '#fadb14', borderRadius: '50%', display: 'inline-block', width: 18, height: 18 },
  red:    { background: '#ff4d4f', borderRadius: '50%', display: 'inline-block', width: 18, height: 18 },
  blue:   { background: '#1677ff', borderRadius: '50%', display: 'inline-block', width: 18, height: 18 },
  orange: { background: '#fa8c16', borderRadius: '50%', display: 'inline-block', width: 18, height: 18 },
  black:  { background: '#262626', borderRadius: '50%', display: 'inline-block', width: 18, height: 18 },
  purple: { background: '#722ed1', borderRadius: '50%', display: 'inline-block', width: 18, height: 18 },
};

function ColorDot({ value }: { value: string }) {
  const style = COLOR_DOT[value];
  if (!style) return <span style={{ fontSize: 14, color: '#8c8c8c', fontStyle: 'italic' }}>--</span>;
  return <span style={style} />;
}

interface WarningMonitorGridProps {
  onOpenDetail?: (code: string) => void;
}

const WarningMonitorGrid: React.FC<WarningMonitorGridProps> = ({ onOpenDetail }) => {
  const [items, setItems] = useState<MonitorItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState('');
  const [sortKey, setSortKey] = useState<'overall' | 'price_warning' | 'trend_warning' | 'risk_level'>('overall');
  const [sortDir, setSortDir] = useState<'ascend' | 'descend'>('descend');
  const [detailVisible, setDetailVisible] = useState(false);
  const [detailItem, setDetailItem] = useState<MonitorItem | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res: any = await getMonitorPanel();
      const data = res?.items ?? res?.data?.items ?? [];
      setItems(data);
      setLastUpdate(res?.timestamp ?? res?.data?.timestamp ?? '');
    } catch (e) {
      console.error('Monitor panel fetch failed:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleViewDetail = useCallback(async (code: string) => {
    setDetailLoading(true);
    setDetailVisible(true);
    try {
      const res: any = await getStockRealtimeWarning(code);
      setDetailItem(res?.data ?? res ?? null);
    } catch (e) {
      console.error('Detail fetch failed:', e);
      setDetailItem(null);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const sorted = [...items].sort((a, b) => {
    const ORDER = ['gray', 'green', 'yellow', 'orange', 'red', 'blue', 'black'];
    const aIdx = ORDER.indexOf(a[sortKey] || 'gray');
    const bIdx = ORDER.indexOf(b[sortKey] || 'gray');
    return sortDir === 'descend' ? bIdx - aIdx : aIdx - bIdx;
  });

  const columns: ColumnsType<MonitorItem> = [
    {
      title: '\u4ee3\u7801', dataIndex: 'code', key: 'code', width: 90,
      render: (code: string) => <Text code style={{ fontSize: 14, fontWeight: 600 }}>{code}</Text>,
    },
    {
      title: '\u540d\u79f0', dataIndex: 'name', key: 'name', width: 90,
      render: (name: string, r) => (
        <a onClick={() => handleViewDetail(r.code)} style={{ fontSize: 14, fontWeight: 600 }}>{name}</a>
      ),
    },
    {
      title: '\u7efc\u5408', dataIndex: 'overall', key: 'overall', width: 60,
      render: (v: string) => <ColorDot value={v} />,
    },
    { title: '\u4ef7\u683c', dataIndex: 'price_warning', key: 'price_warning', width: 55,
      render: (v: string) => <ColorDot value={v} /> },
    { title: '\u6da8\u8dcc', dataIndex: 'updown_warning', key: 'updown_warning', width: 50,
      render: (v: string) => <ColorDot value={v} /> },
    { title: '\u8d8b\u52bf', dataIndex: 'trend_warning', key: 'trend_warning', width: 55,
      render: (v: string) => <ColorDot value={v} /> },
    { title: '\u5171\u632f', dataIndex: 'resonance_warning', key: 'resonance_warning', width: 55,
      render: (v: string) => <ColorDot value={v} /> },
    { title: '\u8d22\u52a1', dataIndex: 'finance_warning', key: 'finance_warning', width: 50,
      render: (v: string) => <ColorDot value={v} /> },
    { title: '\u7a81\u53d1', dataIndex: 'event_warning', key: 'event_warning', width: 50,
      render: (v: string) => <ColorDot value={v} /> },
    { title: '\u98ce\u9669', dataIndex: 'risk_level', key: 'risk_level', width: 50,
      render: (v: string) => <ColorDot value={v} /> },
    {
      title: '\u539f\u56e0', dataIndex: 'reason', key: 'reason',
      ellipsis: true,
      render: (reason: string) => (
        <Tooltip title={reason || '-'}>
          <Text style={{ fontSize: 13, color: reason ? '#595959' : '#bfbfbf' }}>{reason || '-'}</Text>
        </Tooltip>
      ),
    },
    {
      title: '', key: 'action', width: 50, align: 'center',
      render: (_: unknown, r: MonitorItem) => (
        <Tooltip title='\u8be6\u60c5'>
          <Button type='link' size='small' icon={<EyeOutlined style={{ fontSize: 16 }} />}
            onClick={(e) => { e.stopPropagation(); handleViewDetail(r.code); }} />
        </Tooltip>
      ),
    },
  ];

  return (
    <Card
      size='small'
      style={{ borderRadius: 8, marginBottom: 0 }}
      title={
        <Space>
          <span style={{ fontSize: 16, fontWeight: 600 }}>{'\u76d1\u63a7\u9762\u677f'}</span>
          {lastUpdate && (
            <Text type='secondary' style={{ fontSize: 12 }}>{'\u66f4\u65b0'}: {lastUpdate}</Text>
          )}
        </Space>
      }
      extra={
        <Space size='small'>
          <Button size='small' shape='round' icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>
            {'\u5237\u65b0'}
          </Button>
        </Space>
      }
    >
      <Modal
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={640}
        destroyOnClose
      >
        <Spin spinning={detailLoading}>
          {detailItem ? (
            <div style={{ maxHeight: '60vh', overflowY: 'auto', padding: 4 }}>
              <div style={{ marginBottom: 14, padding: 12, borderRadius: 6, background: '#fafafa' }}>
                <Space style={{ marginBottom: 4 }}>
                  <ColorDot value={detailItem.overall} />
                  <Text strong style={{ fontSize: 16 }}>{detailItem.name} ({detailItem.code})</Text>
                </Space>
              </div>

              <div style={{ marginBottom: 14, padding: 12, borderRadius: 6, background: '#fafafa' }}>
                <Space style={{ marginBottom: 4 }}>
                  <ColorDot value={detailItem.price_warning} />
                  <span style={{ fontSize: 14, fontWeight: 600 }}>{'\u4ef7\u683c\u9884\u8b66'}</span>
                </Space>
                <div style={{ fontSize: 13, color: '#595959', lineHeight: 1.8 }}>
                  {'\u6700\u65b0\u4ef7'}: {detailItem.price_data?.price || '-'} |
                  {'\u6628\u6536'}: {detailItem.price_data?.pre_close || '-'} |
                  {'\u6da8\u8dcc\u5e45'}: {detailItem.price_data?.change_pct ?? '-'}%
                </div>
              </div>

              <div style={{ marginBottom: 14, padding: 12, borderRadius: 6, background: '#fafafa' }}>
                <Space style={{ marginBottom: 4 }}>
                  <ColorDot value={detailItem.trend_warning} />
                  <span style={{ fontSize: 14, fontWeight: 600 }}>{'\u8d8b\u52bf\u9884\u8b66'}</span>
                </Space>
                <div style={{ fontSize: 13, color: '#595959', lineHeight: 1.8 }}>
                  MA5: {detailItem.trend_data?.ma5 ?? '-'} |
                  MA10: {detailItem.trend_data?.ma10 ?? '-'} |
                  MA20: {detailItem.trend_data?.ma20 ?? '-'} |
                  {'\u5929\u6570'}: {detailItem.trend_data?.data_points ?? 0}
                </div>
              </div>

              <div style={{ marginBottom: 14, padding: 12, borderRadius: 6, background: '#fafafa' }}>
                <Space style={{ marginBottom: 4 }}>
                  <ColorDot value={detailItem.risk_level} />
                  <span style={{ fontSize: 14, fontWeight: 600 }}>{'\u98ce\u9669\u8bc4\u5206'}</span>
                </Space>
                <div style={{ fontSize: 13, color: '#595959', lineHeight: 1.8 }}>
                  {'\u7efc\u5408\u5f97\u5206'}: {detailItem.risk_data?.score ?? '-'}
                </div>
              </div>

              {detailItem.reason && (
                <div style={{ padding: 12, borderRadius: 6, background: '#fff7e6', border: '1px solid #ffd591' }}>
                  <span style={{ fontSize: 14, fontWeight: 600 }}>{'\u9884\u8b66\u539f\u56e0'}</span>
                  <div style={{ fontSize: 13, color: '#613400', marginTop: 4 }}>{detailItem.reason}</div>
                </div>
              )}

              <div style={{ marginTop: 8, textAlign: 'right' }}>
                <Text type='secondary' style={{ fontSize: 12 }}>{detailItem.timestamp}</Text>
              </div>
            </div>
          ) : (
            <Empty />
          )}
        </Spin>
      </Modal>

      <Spin spinning={loading}>
        {sorted.length > 0 ? (
          <Table<MonitorItem>
            columns={columns}
            dataSource={sorted}
            rowKey='code'
            size='middle'
            scroll={{ x: 1000 }}
            pagination={false}
            locale={{ emptyText: <Empty /> }}
            style={{ marginTop: 4 }}
          />
        ) : (
          <div style={{ padding: 32, textAlign: 'center' }}>
            <Empty description={loading ? '' : ''} />
          </div>
        )}
      </Spin>
    </Card>
  );
};

export default WarningMonitorGrid;
