import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Button, Result, Space, Typography } from 'antd';

const { Text } = Typography;

interface ErrorBoundaryProps {
  children: ReactNode;
  /** 后备 UI 标题 */
  title?: string;
  /** 后备 UI 描述 */
  description?: string;
  /** 自定义降级 UI */
  fallback?: ReactNode;
  /** 错误回调 */
  onError?: (error: Error, info: ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * 通用错误边界
 * - 捕获子组件渲染错误，阻止整页崩溃白屏
 * - 显示优雅降级 UI + 重新加载按钮
 * - 支持自定义降级内容
 */
class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary] caught:', error.message, info.componentStack);
    this.props.onError?.(error, info);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <Result
          status="error"
          title={this.props.title || '页面异常'}
          subTitle={
            <Space direction="vertical" size={4}>
              <Text type="secondary">
                {this.props.description || '该区域发生异常，已阻止崩溃扩散至整个页面。'}
              </Text>
              {this.state.error && (
                <Text type="secondary" style={{ fontSize: 12, fontFamily: 'monospace' }}>
                  {this.state.error.message}
                </Text>
              )}
            </Space>
          }
          extra={
            <Space>
              <Button type="primary" onClick={this.handleReset}>
                重试
              </Button>
              <Button onClick={this.handleReload}>
                刷新页面
              </Button>
            </Space>
          }
        />
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
