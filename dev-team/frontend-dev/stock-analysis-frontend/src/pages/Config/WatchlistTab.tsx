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
  Select,
  Tabs,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  UploadOutlined,
  ReloadOutlined,
  SearchOutlined,
  ClearOutlined,
  ImportOutlined,
  MonitorOutlined,
  CheckCircleOutlined,
  StopOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { CheckboxChangeEvent } from 'antd/es/checkbox';
import { useConfigStore } from '../../store/configStore';
import * as configApi from '../../services/configApi';
import { syncMonitorPool, importTdxWatchlist } from '../../services/configApi';
import type { WatchlistItem } from '../../types';

const { Text, Title } = Typography;

/** 将后端自选股数据映射为前端 WatchlistItem */
function mapWatchlist(rawList: any[]): WatchlistItem[] {
  return rawList.map((item: any) => ({
    code: item.code || '',
    name: item.name || '',
    addedAt: item.created_at || new Date().toISOString(),
  }));
}

/** 将后端监控池数据映射为前端 MonitorItem */
function mapMonitorItems(rawList: any[]): any[] {
  return rawList.map((item: any) => ({
    code: item.code || '',
    name: item.name || '',
    status: item.is_active === false ? 'error' : 'active',
    addedAt: item.created_at || new Date().toISOString(),
  }));
}

const WatchlistTab: React.FC = () => {
  const {
    watchlist,
    monitorPool,
    addWatchlistItem,
    removeWatchlistItem,
    clearWatchlist,
    batchRemoveWatchlist,
    addMonitorItem,
    removeMonitorItem,
    setWatchlist,
    setMonitorPool,
  } = useConfigStore();

  // 从后端加载数据
  const loadData = useCallback(async () => {
    try {
      const [wlRes, mpRes] = await Promise.all([
        configApi.fetchWatchlist(),
        configApi.fetchMonitorPool(),
      ]);
      const wlList = Array.isArray(wlRes) ? wlRes : ((wlRes as any)?.data ?? []);
      setWatchlist(mapWatchlist(wlList));
      const mpList = Array.isArray(mpRes) ? mpRes : ((mpRes as any)?.data ?? []);
      setMonitorPool(mapMonitorItems(mpList));
    } catch {
      // 加载失败则保留现有数据
    }
  }, [setWatchlist, setMonitorPool]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const [codeInput, setCodeInput] = useState('');
  const [nameInput, setNameInput] = useState('');
  const [searchText, setSearchText] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [importTab, setImportTab] = useState<string>('batch');
  const [batchCodes, setBatchCodes] = useState('');
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [industryFilter, setIndustryFilter] = useState<string | undefined>(undefined);
  const [monitorFilter, setMonitorFilter] = useState<string | undefined>(undefined);
  const [loading, setLoading] = useState(false);

  // Derive monitor status per watchlist item
  const monitorMap = useMemo(() => {
    const map = new Map<string, boolean>();
    monitorPool.forEach((item) => map.set(item.code, true));
    return map;
  }, [monitorPool]);

  const isInMonitor = (code: string) => monitorMap.has(code);

  // Extract unique industries from watchlist
  const industries = useMemo(() => {
    const set = new Set<string>();
    watchlist.forEach((item) => {
      if (item.industry) set.add(item.industry);
    });
    return Array.from(set).sort();
  }, [watchlist]);

  const handleAdd = async () => {
    if (!codeInput.trim()) { message.warning('请输入股票代码'); return; }
    const code = codeInput.trim().toUpperCase();
    const name = nameInput.trim() || code;
    if (watchlist.some((item) => item.code === code)) { message.warning(`股票 ${code} 已在自选股中`); return; }

    try {
      await configApi.addWatchlistItem(code, name);
      addWatchlistItem({ code, name, addedAt: new Date().toISOString() });
      message.success(`已添加 ${code}`);
      setCodeInput('');
      setNameInput('');
    } catch (err: any) {
      message.error(err?.response?.data?.detail || `添加 ${code} 失败`);
    }
  };

  const handleDelete = async (code: string) => {
    try {
      await configApi.removeWatchlistItem(code);
      removeWatchlistItem(code);
      message.success(`已移除 ${code}`);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || `移除 ${code} 失败`);
    }
  };

  const handleClearAll = () => {
    Modal.confirm({
      title: '确认清空全部自选股',
      content: `确定清空全部 ${watchlist.length} 只自选股？此操作不可撤销。`,
      okText: '确认清空',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        const codes = watchlist.map((i) => i.code);
        for (const code of codes) {
          try { await configApi.removeWatchlistItem(code); } catch { /* skip */ }
        }
        clearWatchlist();
        setSelectedRowKeys([]);
        message.success('已清空全部自选股');
      },
    });
  };

  const handleBatchDelete = () => {
    if (selectedRowKeys.length === 0) return;
    Modal.confirm({
      title: '确认批量删除',
      content: `确定删除选中的 ${selectedRowKeys.length} 只自选股？`,
      onOk: async () => {
        const keys = [...selectedRowKeys];
        for (const code of keys) {
          try { await configApi.removeWatchlistItem(code); } catch { /* skip */ }
        }
        batchRemoveWatchlist(selectedRowKeys);
        setSelectedRowKeys([]);
        message.success(`已删除 ${keys.length} 只自选股`);
      },
    });
  };

  const handleToggleMonitor = async (code: string, name: string) => {
    if (isInMonitor(code)) {
      try {
        await configApi.removeMonitorItem(code);
        removeMonitorItem(code);
        message.info(`${code} 已从监控池移除`);
      } catch (err: any) {
        message.error(err?.response?.data?.detail || `移除 ${code} 失败`);
      }
    } else {
      if (monitorPool.length >= 50) { message.warning('监控池已达上限（50只）'); return; }
      try {
        await configApi.addMonitorItem(code, name);
        addMonitorItem({ code, name, status: 'active', addedAt: new Date().toISOString() });
        message.success(`${code} 已加入监控池`);
      } catch (err: any) {
        message.error(err?.response?.data?.detail || `添加 ${code} 失败`);
      }
    }
  };

  const handleTdxImport = async () => {
    setLoading(true);
    try {
      const res: any = await importTdxWatchlist();
      message.success(
        `从通达信成功导入 ${res?.imported?.length || 0} 只股票` +
        (res?.skipped_duplicates ? `，${res.skipped_duplicates} 只已存在已跳过` : '') +
        (res?.skipped_invalid ? `，${res.skipped_invalid} 行格式无效` : '')
      );
      await loadData();
      setImportModalOpen(false);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '导入通达信自选股失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectionImport = () => {
    message.info('请先在智能选股模块中运行选股，然后在此处点击从选股结果导入。');
  };

  const handleBatchImport = () => {
    const codes = batchCodes
      .split(/[\n,，\s]+/)
      .map((s) => s.trim().toUpperCase())
      .filter(Boolean);
    if (codes.length === 0) { message.warning('请输入至少一个股票代码'); return; }

    const existing = new Set(watchlist.map((i) => i.code));
    const newCodes = codes.filter((c) => !existing.has(c));
    if (newCodes.length === 0) { message.warning('所有输入的股票已在自选股中'); return; }

    const skipped = codes.length - newCodes.length;
    let added = 0;

    // 逐个调后端添加
    const promises = newCodes.map(async (code) => {
      try {
        await configApi.addWatchlistItem(code, code);
        addWatchlistItem({ code, name: code, addedAt: new Date().toISOString() });
        added++;
      } catch { /* skip */ }
    });

    Promise.all(promises).then(() => {
      message.success(
        `成功导入 ${added} 只股票${skipped > 0 ? `，${skipped} 只已存在已跳过` : ''}` +
        (added < newCodes.length ? `，${newCodes.length - added} 只导入失败` : '')
      );
      setBatchCodes('');
      setImportModalOpen(false);
    });
  };

  // 筛选后列表
  const filteredList = useMemo(() => {
    let list = watchlist.filter(
      (item) =>
        item.code.includes(searchText.toUpperCase()) ||
        item.name.includes(searchText)
    );
    if (industryFilter) {
      list = list.filter((item) => item.industry === industryFilter);
    }
    if (monitorFilter === 'monitoring') {
      list = list.filter((item) => isInMonitor(item.code));
    } else if (monitorFilter === 'not_monitoring') {
      list = list.filter((item) => !isInMonitor(item.code));
    }
    return list;
  }, [watchlist, searchText, industryFilter, monitorFilter, monitorMap]);

  const paginatedList = filteredList.slice(
    (page - 1) * pageSize,
    page * pageSize
  );

  const columns: ColumnsType<WatchlistItem> = [
    {
      title: <Checkbox checked={selectedRowKeys.length === filteredList.length && filteredList.length > 0} indeterminate={selectedRowKeys.length > 0 && selectedRowKeys.length < filteredList.length} onChange={(e) => { setSelectedRowKeys(e.target.checked ? filteredList.map((i) => i.code) : []); }} />,
      key: 'selection', width: 40,
      render: (_, record) => (
        <Checkbox checked={selectedRowKeys.includes(record.code)} onChange={(e: CheckboxChangeEvent) => { setSelectedRowKeys((prev) => e.target.checked ? [...prev, record.code] : prev.filter((k) => k !== record.code)); }} />
      ),
    },
    { title: '股票代码', dataIndex: 'code', key: 'code', width: 140, render: (code: string) => <Text code>{code}</Text> },
    { title: '股票名称', dataIndex: 'name', key: 'name' },
    {
      title: '行业', dataIndex: 'industry', key: 'industry', width: 120,
      sorter: (a, b) => (a.industry || '').localeCompare(b.industry || ''),
      render: (industry: string | undefined) => industry ? <Tag>{industry}</Tag> : <Text type="secondary">--</Text>,
    },
    {
      title: '监控状态', key: 'monitorStatus', width: 120,
      sorter: (a, b) => (isInMonitor(b.code) ? 1 : 0) - (isInMonitor(a.code) ? 1 : 0),
      render: (_, record) => {
        const monitoring = isInMonitor(record.code);
        return (
          <Tag color={monitoring ? 'green' : 'default'} style={{ cursor: 'pointer' }} onClick={() => handleToggleMonitor(record.code, record.name)}>
            {monitoring ? '监控中' : '未监控'}
          </Tag>
        );
      },
    },
    { title: '添加时间', dataIndex: 'addedAt', key: 'addedAt', width: 180, render: (date: string) => new Date(date).toLocaleString('zh-CN') },
    {
      title: '操作', key: 'action', width: 180,
      render: (_, record) => (
        <Space>
          {isInMonitor(record.code) ? (
            <Tooltip title="已在监控池中，点击可移除">
              <Button type="link" size="small" icon={<CheckCircleOutlined />} onClick={() => handleToggleMonitor(record.code, record.name)}>已在监控</Button>
            </Tooltip>
          ) : (
            <Tooltip title={monitorPool.length >= 50 ? '监控池已达上限' : '加入监控池'}>
              <Button type="link" size="small" icon={<MonitorOutlined />} onClick={() => handleToggleMonitor(record.code, record.name)} disabled={monitorPool.length >= 50}>加入监控</Button>
            </Tooltip>
          )}
          <Button type="link" danger size="small" icon={<DeleteOutlined />} onClick={() => handleDelete(record.code)}>删除</Button>
        </Space>
      ),
    },
  ];

  return (
    <Card
      title="自选股管理"
      extra={
        <Space wrap>
          <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>刷新</Button>
          {monitorPool.length >= 45 && (
            <Tag color={monitorPool.length >= 48 ? 'red' : 'orange'}>监控池容量: {monitorPool.length}/50</Tag>
          )}
          <Button icon={<ImportOutlined />} onClick={() => { setImportTab('tdx'); setImportModalOpen(true); }}>从通达信导入</Button>
          <Button icon={<UploadOutlined />} onClick={() => { setImportTab('selection'); setImportModalOpen(true); }}>从选股结果导入</Button>
          <Button icon={<UploadOutlined />} onClick={() => { setImportTab('batch'); setImportModalOpen(true); }}>批量导入</Button>
        </Space>
      }
    >
      {/* 添加单个 */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
        <Input placeholder="输入股票代码，如 600519" value={codeInput} onChange={(e) => setCodeInput(e.target.value)} onPressEnter={handleAdd} style={{ flex: '1 1 180px', minWidth: 120 }} prefix={<SearchOutlined />} />
        <Input placeholder="股票名称（可选）" value={nameInput} onChange={(e) => setNameInput(e.target.value)} onPressEnter={handleAdd} style={{ flex: '1 1 150px', minWidth: 120 }} />
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>添加</Button>
      </div>

      {/* 搜索 + 筛选 */}
      <div style={{ marginBottom: 16, display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
        <Input.Search placeholder="搜索自选股..." allowClear value={searchText} onChange={(e) => { setSearchText(e.target.value); setPage(1); }} style={{ width: 280, maxWidth: '100%' }} />
        <Select placeholder="按行业筛选" allowClear style={{ minWidth: 140, maxWidth: '100%' }} value={industryFilter} onChange={(val) => { setIndustryFilter(val); setPage(1); }} options={industries.map((ind) => ({ label: ind, value: ind }))} />
        <Select placeholder="按监控状态筛选" allowClear style={{ minWidth: 140, maxWidth: '100%' }} value={monitorFilter} onChange={(val) => { setMonitorFilter(val); setPage(1); }} options={[{ label: '监控中', value: 'monitoring' }, { label: '未监控', value: 'not_monitoring' }]} />
        {selectedRowKeys.length > 0 && (
          <>
            <Button danger icon={<DeleteOutlined />} onClick={handleBatchDelete}>批量删除 ({selectedRowKeys.length})</Button>
            <Button onClick={() => setSelectedRowKeys([])}>取消选择</Button>
          </>
        )}
        <Button danger icon={<ClearOutlined />} onClick={handleClearAll} disabled={watchlist.length === 0}>清空全部</Button>
      </div>

      {watchlist.length === 0 ? (
        <Empty description="暂无自选股，请在上方添加" />
      ) : (
        <>
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
              showTotal: (total) => `共 ${total} 只自选股`,
              showSizeChanger: false,
            }}
            size="small"
            loading={loading}
          />
          </div>
          <Space style={{ marginTop: 8 }}>
            <Text type="secondary">
              共 {watchlist.length} 只自选股{searchText ? '（搜索过滤）' : ''}{industryFilter ? '（行业筛选）' : ''}
            </Text>
            <Tag color="green">监控中: {watchlist.filter((i) => isInMonitor(i.code)).length}</Tag>
            <Tag>未监控: {watchlist.filter((i) => !isInMonitor(i.code)).length}</Tag>
          </Space>
        </>
      )}

      {/* 导入弹窗 */}
      <Modal title="导入自选股" open={importModalOpen} onCancel={() => { setImportModalOpen(false); setBatchCodes(''); }} footer={null} width={560} style={{ top: 20 }}>
        <Tabs activeKey={importTab} onChange={(key) => { setImportTab(key); setBatchCodes(''); }}
          items={[
            {
              key: 'batch', label: '批量导入',
              children: (
                <div>
                  <div style={{ marginBottom: 12 }}><Text>请输入股票代码，多个代码用逗号、换行或空格分隔：</Text></div>
                  <Input.TextArea rows={8} value={batchCodes} onChange={(e) => setBatchCodes(e.target.value)} placeholder={`示例：\n600519\n000858\n300750\n601318, 000333`} />
                  <div style={{ marginTop: 8, marginBottom: 16 }}><Text type="secondary">支持格式：600519、000858、sz000001、SH600519</Text></div>
                  <Button type="primary" onClick={handleBatchImport} icon={<UploadOutlined />}>导入</Button>
                </div>
              ),
            },
            {
              key: 'tdx', label: '从通达信导入',
              children: (
                <div style={{ textAlign: 'center', padding: '24px 0' }}>
                  <ImportOutlined style={{ fontSize: 48, color: '#1890ff', marginBottom: 16 }} />
                  <Title level={5}>导入通达信自选股</Title>
                  <Text type="secondary">将从本地通达信数据源读取自选股列表，一键导入到系统</Text>
                  <div style={{ marginTop: 24 }}><Button type="primary" icon={<ImportOutlined />} onClick={handleTdxImport}>开始导入</Button></div>
                </div>
              ),
            },
            {
              key: 'selection', label: '从选股结果导入',
              children: (
                <div style={{ textAlign: 'center', padding: '24px 0' }}>
                  <UploadOutlined style={{ fontSize: 48, color: '#52c41a', marginBottom: 16 }} />
                  <Title level={5}>导入选股结果</Title>
                  <Text type="secondary">将智能选股模块的选股结果一键添加到自选股列表</Text>
                  <div style={{ marginTop: 24 }}><Button type="primary" icon={<UploadOutlined />} onClick={handleSelectionImport}>导入选股结果</Button></div>
                </div>
              ),
            },
          ]}
        />
      </Modal>
    </Card>
  );
};

export default WatchlistTab;
