import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Card,
  Input,
  Button,
  Table,
  Tag,
  Space,
  Modal,
  message,
  Typography,
  Empty,
  Tooltip,
  Checkbox,
  Progress,
  List,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  SearchOutlined,
  ClearOutlined,
  ImportOutlined,
  StopOutlined,
  MinusCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { CheckboxChangeEvent } from 'antd/es/checkbox';
import { useConfigStore } from '../../store/configStore';
import * as configApi from '../../services/configApi';
import { syncMonitorPool } from '../../services/configApi';
import type { MonitorItem } from '../../types';

const { Text, Title } = Typography;
const MONITOR_LIMIT = 50;

const statusConfig: Record<MonitorItem['status'], { color: string; label: string }> = {
  active: { color: 'green', label: '监控中' },
  paused: { color: 'orange', label: '已暂停' },
  error: { color: 'red', label: '异常' },
  suspended: { color: 'default', label: '已停牌' },
};

/** 将后端监控池数据映射为前端 MonitorItem */
function mapMonitorItems(rawList: any[]): MonitorItem[] {
  return rawList.map((item: any) => ({
    code: item.code || '',
    name: item.name || '',
    status: item.is_active === false ? 'error' : 'active',
    addedAt: item.created_at || new Date().toISOString(),
  }));
}

/** 从后端重新加载监控池 */
async function reloadMonitorPool(setter: (items: MonitorItem[]) => void) {
  try {
    const res: any = await configApi.fetchMonitorPool();
    const list = Array.isArray(res) ? res : (res?.data ?? []);
    setter(mapMonitorItems(list));
  } catch {
    // 加载失败，保留现有数据
  }
}

const MonitorPoolTab: React.FC = () => {
  const {
    monitorPool,
    watchlist,
    addMonitorItem,
    removeMonitorItem,
    updateMonitorStatus,
    clearMonitorPool,
    batchRemoveMonitor,
    setMonitorPool,
  } = useConfigStore();
  const [codeInput, setCodeInput] = useState('');
  const [nameInput, setNameInput] = useState('');
  const [searchText, setSearchText] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 10;
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [importFromWatchlistOpen, setImportFromWatchlistOpen] = useState(false);
  const [selectedWatchlistCodes, setSelectedWatchlistCodes] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  // 从后端加载
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const res: any = await configApi.fetchMonitorPool();
      const list = Array.isArray(res) ? res : (res?.data ?? []);
      setMonitorPool(mapMonitorItems(list));
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [setMonitorPool]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Progress bar
  const progressPercent = Math.round((monitorPool.length / MONITOR_LIMIT) * 100);
  const progressColor =
    monitorPool.length >= 48 ? '#ff4d4f' :
    monitorPool.length >= 45 ? '#faad14' :
    '#52c41a';
  const isAtLimit = monitorPool.length >= MONITOR_LIMIT;
  const isSuspended = (item: MonitorItem) => item.status === 'suspended';

  // ── 添加 ──
  const handleAdd = async () => {
    const code = codeInput.trim().toUpperCase();
    if (!code) { message.warning('请输入股票代码'); return; }
    if (isAtLimit) { message.warning(`已达监控池上限（${MONITOR_LIMIT}只）`); return; }
    if (monitorPool.some((i) => i.code === code)) { message.warning(`${code} 已在监控池中`); return; }

    const name = nameInput.trim() || code;
    try {
      // 先调后端持久化
      await configApi.addMonitorItem(code, name);
      // 成功后更新本地状态
      addMonitorItem({ code, name, status: 'active', addedAt: new Date().toISOString() });
      message.success(`已将 ${code} 加入监控池`);
      setCodeInput('');
      setNameInput('');
    } catch (err: any) {
      message.error(err?.response?.data?.detail || `添加 ${code} 失败`);
    }
  };

  // ── 删除单个 ──
  const handleDelete = async (code: string) => {
    try {
      await configApi.removeMonitorItem(code);
      removeMonitorItem(code);
      setSelectedRowKeys((prev) => prev.filter((k) => k !== code));
      message.success(`${code} 已从监控池移除`);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || `移除 ${code} 失败`);
    }
  };

  // ── 清空全部（用 sync 接口一次搞定）──
  const handleClearAll = () => {
    if (monitorPool.length === 0) return;
    Modal.confirm({
      title: '确认清空监控池',
      content: `确定清空全部 ${monitorPool.length} 个监控标的？此操作不可撤销。`,
      okText: '确认清空',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await syncMonitorPool([]);
          clearMonitorPool();
          setSelectedRowKeys([]);
          message.success('已清空监控池');
        } catch {
          // sync 失败则逐个删除降级
          for (const item of monitorPool) {
            try { await configApi.removeMonitorItem(item.code); } catch { /* skip */ }
          }
          clearMonitorPool();
          setSelectedRowKeys([]);
          message.success('已清空监控池');
        }
      },
    });
  };

  // ── 批量取消监控 ──
  const handleBatchRemove = () => {
    if (selectedRowKeys.length === 0) return;
    Modal.confirm({
      title: '确认批量取消监控',
      content: `确定取消选中的 ${selectedRowKeys.length} 只股票的监控？`,
      onOk: async () => {
        for (const code of selectedRowKeys) {
          try { await configApi.removeMonitorItem(code); } catch { /* skip */ }
        }
        batchRemoveMonitor(selectedRowKeys);
        setSelectedRowKeys([]);
        message.success(`已取消 ${selectedRowKeys.length} 只股票的监控`);
      },
    });
  };

  // ── 暂停/恢复 ──
  const handleTogglePause = async (item: MonitorItem) => {
    if (isSuspended(item)) { message.info(`${item.code} 已停牌，不可操作`); return; }
    const newActive = item.status === 'active' ? false : true;
    try {
      await configApi.updateMonitorItem(item.code, { is_active: newActive });
      updateMonitorStatus(item.code, newActive ? 'active' : 'paused');
      if (newActive) {
        message.success(`${item.code} 监控已恢复`);
      } else {
        message.info(`${item.code} 监控已暂停`);
      }
    } catch {
      message.error(`${item.code} 操作失败`);
    }
  };

  // ── 从自选股导入 ──
  const handleImportFromWatchlist = () => {
    const poolCodes = new Set(monitorPool.map((i) => i.code));
    const available = watchlist.filter((i) => !poolCodes.has(i.code));
    if (available.length === 0) { message.info('所有自选股已在监控池中'); return; }
    setSelectedWatchlistCodes([]);
    setImportFromWatchlistOpen(true);
  };

  const handleConfirmImportFromWatchlist = async () => {
    if (selectedWatchlistCodes.length === 0) { message.warning('请选择至少一只股票'); return; }
    const remaining = MONITOR_LIMIT - monitorPool.length;
    if (remaining <= 0) { message.warning('监控池已满'); return; }

    const toAdd = selectedWatchlistCodes.slice(0, remaining);
    const skipped = selectedWatchlistCodes.length - toAdd.length;
    let added = 0;

    for (const code of toAdd) {
      const wlItem = watchlist.find((i) => i.code === code);
      const name = wlItem?.name || code;
      try {
        await configApi.addMonitorItem(code, name);
        addMonitorItem({ code, name, status: 'active', addedAt: new Date().toISOString() });
        added++;
      } catch {
        // 单个失败继续下一个
      }
    }

    const failCount = toAdd.length - added;
    message.success(
      `成功导入 ${added} 只股票到监控池` +
      (skipped > 0 ? `，${skipped} 只因已达上限被跳过` : '') +
      (failCount > 0 ? `，${failCount} 只导入失败` : '')
    );
    setImportFromWatchlistOpen(false);
    setSelectedWatchlistCodes([]);
  };

  // 自选股中可用的列表
  const availableForMonitor = useMemo(() => {
    const poolCodes = new Set(monitorPool.map((i) => i.code));
    return watchlist.filter((i) => !poolCodes.has(i.code));
  }, [watchlist, monitorPool]);

  // 筛选 + 分页
  const filteredList = monitorPool.filter(
    (item) =>
      item.code.includes(searchText.toUpperCase()) ||
      item.name.includes(searchText)
  );
  const paginatedList = filteredList.slice(
    (page - 1) * pageSize,
    page * pageSize
  );

  const columns: ColumnsType<MonitorItem> = [
    {
      title: (
        <Checkbox
          checked={selectedRowKeys.length === filteredList.length && filteredList.length > 0}
          indeterminate={selectedRowKeys.length > 0 && selectedRowKeys.length < filteredList.length}
          onChange={(e) => {
            setSelectedRowKeys(e.target.checked ? filteredList.map((i) => i.code) : []);
          }}
        />
      ),
      key: 'selection',
      width: 40,
      render: (_, record) => (
        <Checkbox
          disabled={isSuspended(record)}
          checked={selectedRowKeys.includes(record.code)}
          onChange={(e: CheckboxChangeEvent) => {
            setSelectedRowKeys((prev) =>
              e.target.checked ? [...prev, record.code] : prev.filter((k) => k !== record.code)
            );
          }}
        />
      ),
    },
    { title: '股票代码', dataIndex: 'code', key: 'code', width: 140, render: (c: string) => <Text code>{c}</Text> },
    { title: '股票名称', dataIndex: 'name', key: 'name' },
    {
      title: '监控状态', dataIndex: 'status', key: 'status', width: 120,
      render: (s: MonitorItem['status']) => <Tag color={statusConfig[s]?.color}>{statusConfig[s]?.label}</Tag>,
    },
    {
      title: '添加时间', dataIndex: 'addedAt', key: 'addedAt', width: 180,
      render: (d: string) => new Date(d).toLocaleString('zh-CN'),
    },
    {
      title: '操作', key: 'action', width: 180,
      render: (_, record) => {
        if (isSuspended(record)) {
          return (
            <Space>
              <Tag icon={<StopOutlined />} color="default">已停牌</Tag>
              <Button type="link" danger size="small" icon={<DeleteOutlined />} onClick={() => handleDelete(record.code)}>移除</Button>
            </Space>
          );
        }
        return (
          <Space>
            <Tooltip title={record.status === 'paused' ? '恢复监控' : '暂停监控'}>
              <Button type="link" size="small" icon={record.status === 'paused' ? <PlayCircleOutlined /> : <PauseCircleOutlined />} onClick={() => handleTogglePause(record)}>
                {record.status === 'paused' ? '恢复' : '暂停'}
              </Button>
            </Tooltip>
            <Button type="link" danger size="small" icon={<DeleteOutlined />} onClick={() => handleDelete(record.code)}>移除</Button>
          </Space>
        );
      },
    },
  ];

  return (
    <Card
      title={<Space><span>监控池管理</span><Tag>{monitorPool.length}/{MONITOR_LIMIT}</Tag></Space>}
      extra={
        <Space wrap>
          <Button icon={<ReloadOutlined />} size="small" onClick={loadData} loading={loading}>刷新</Button>
          <Tag color="green">监控中: {monitorPool.filter((i) => i.status === 'active').length}</Tag>
          <Tag color="orange">已暂停: {monitorPool.filter((i) => i.status === 'paused').length}</Tag>
          <Tag color="red">异常: {monitorPool.filter((i) => i.status === 'error').length}</Tag>
          <Tag>已停牌: {monitorPool.filter((i) => i.status === 'suspended').length}</Tag>
        </Space>
      }
    >
      {/* 进度条 */}
      <div style={{ marginBottom: 16 }}>
        <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 4 }}>
          <Text strong>监控池容量</Text>
          <Text type={progressPercent >= 90 ? 'danger' : 'secondary'} strong={progressPercent >= 90}>
            {monitorPool.length} / {MONITOR_LIMIT}{isAtLimit && ' (已满)'}
          </Text>
        </Space>
        <Progress percent={progressPercent} strokeColor={progressColor} showInfo={false} size="small" />
      </div>

      {/* 添加区 */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
        <Input placeholder="输入股票代码，如 600519" value={codeInput} onChange={(e) => setCodeInput(e.target.value)} onPressEnter={handleAdd} style={{ flex: '1 1 180px', minWidth: 120 }} prefix={<SearchOutlined />} disabled={isAtLimit} />
        <Input placeholder="股票名称（可选）" value={nameInput} onChange={(e) => setNameInput(e.target.value)} onPressEnter={handleAdd} style={{ flex: '1 1 150px', minWidth: 120 }} disabled={isAtLimit} />
        <Tooltip title={isAtLimit ? `已达监控池上限（${MONITOR_LIMIT}只）` : ''}>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd} disabled={isAtLimit}>{isAtLimit ? '已达上限' : '添加标的'}</Button>
        </Tooltip>
      </div>

      {/* 操作栏 */}
      <div style={{ marginBottom: 16, display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
        <Input.Search placeholder="搜索监控标的..." allowClear value={searchText} onChange={(e) => { setSearchText(e.target.value); setPage(1); }} style={{ width: 280, maxWidth: '100%' }} />
        <Button icon={<ImportOutlined />} onClick={handleImportFromWatchlist} disabled={isAtLimit || availableForMonitor.length === 0}>从自选股导入</Button>
        {selectedRowKeys.length > 0 && (
          <>
            <Button danger icon={<MinusCircleOutlined />} onClick={handleBatchRemove}>批量取消监控 ({selectedRowKeys.length})</Button>
            <Button onClick={() => setSelectedRowKeys([])}>取消选择</Button>
          </>
        )}
        <Button danger icon={<ClearOutlined />} onClick={handleClearAll} disabled={monitorPool.length === 0}>清空监控池</Button>
      </div>

      {/* 表格 */}
      {monitorPool.length === 0 ? (
        <Empty description="暂无监控标的，请在上方添加" />
      ) : (
        <div className="config-table-wrap">
        <Table
          columns={columns}
          dataSource={paginatedList}
          rowKey="code"
          scroll={{ x: 'max-content' }}
          pagination={{
            current: page,
            pageSize,
            total: filteredList.length,
            onChange: (p) => setPage(p),
            showTotal: (total) => `共 ${total} 个监控标的`,
            showSizeChanger: false,
          }}
          size="small"
          loading={loading}
        />
        </div>
      )}

      {/* 从自选股导入弹窗 */}
      <Modal
        title="从自选股导入到监控池"
        open={importFromWatchlistOpen}
        onOk={handleConfirmImportFromWatchlist}
        onCancel={() => { setImportFromWatchlistOpen(false); setSelectedWatchlistCodes([]); }}
        okText="导入选中"
        cancelText="取消"
        okButtonProps={{ disabled: selectedWatchlistCodes.length === 0 }}
        width={520}
        style={{ top: 20 }}
      >
        {availableForMonitor.length === 0 ? (
          <Empty description="所有自选股已经在监控池中" />
        ) : (
          <>
            <div style={{ marginBottom: 12 }}>
              <Text>
                共 {availableForMonitor.length} 只自选股可导入
                {isAtLimit && <Text type="danger">（监控池已满）</Text>}
                {!isAtLimit && MONITOR_LIMIT - monitorPool.length < availableForMonitor.length && (
                  <Text type="warning">（剩余容量 {MONITOR_LIMIT - monitorPool.length} 只）</Text>
                )}
              </Text>
            </div>
            <div style={{ marginBottom: 8 }}>
              <Checkbox
                checked={selectedWatchlistCodes.length === Math.min(availableForMonitor.length, MONITOR_LIMIT - monitorPool.length) && selectedWatchlistCodes.length > 0}
                indeterminate={selectedWatchlistCodes.length > 0 && selectedWatchlistCodes.length < Math.min(availableForMonitor.length, MONITOR_LIMIT - monitorPool.length)}
                onChange={(e) => {
                  if (e.target.checked) {
                    const remaining = MONITOR_LIMIT - monitorPool.length;
                    setSelectedWatchlistCodes(availableForMonitor.slice(0, remaining).map((i) => i.code));
                  } else {
                    setSelectedWatchlistCodes([]);
                  }
                }}
              >
                全选（最多 {MONITOR_LIMIT - monitorPool.length} 只）
              </Checkbox>
            </div>
            <List
              style={{ maxHeight: 360, overflow: 'auto' }}
              dataSource={availableForMonitor}
              renderItem={(item) => {
                const remaining = MONITOR_LIMIT - monitorPool.length;
                const canCheck = selectedWatchlistCodes.length < remaining;
                const checked = selectedWatchlistCodes.includes(item.code);
                return (
                  // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions
                  <div style={{ padding: '6px 0', cursor: 'pointer' }} onClick={() => {
                    if (checked) {
                      setSelectedWatchlistCodes((prev) => prev.filter((c) => c !== item.code));
                    } else if (canCheck) {
                      setSelectedWatchlistCodes((prev) => [...prev, item.code]);
                    } else {
                      message.warning(`监控池已达容量上限（${MONITOR_LIMIT}只）`);
                    }
                  }}>
                    <Checkbox checked={checked} disabled={!checked && !canCheck}>
                      <Text code>{item.code}</Text> {item.name}
                    </Checkbox>
                  </div>
                );
              }}
            />
          </>
        )}
      </Modal>
    </Card>
  );
};

export default MonitorPoolTab;
