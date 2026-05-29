/**
 * M05 智能分析模块 API
 */
import apiClient from './api';
import type { ApiResponse } from '../types';

// ========== Types ==========

export interface ReviewRequest {
  date: string;            // YYYY-MM-DD
  stocks?: string[];       // 最多10只股票代码（前端用）
  watch_stocks?: string[]; // 后端API字段名
  use_template?: boolean;
}

export interface StockAnalysisRequest {
  code: string;
  use_template?: boolean;
}

export interface BatchAnalysisRequest {
  codes: string[];         // 最多10只
  template?: string;       // 模板ID
  use_template?: boolean;
}

export interface AnalysisReportSection {
  title: string;
  level?: 1 | 2 | 3;       // heading level
  content: string;
  type?: 'text' | 'table' | 'list';
  tableHeaders?: string[];
  tableRows?: string[][];
  listItems?: string[];
  icon?: string;           // color icon: 'red' | 'green' | 'yellow' | 'blue' | 'gray'
  /** @deprecated use tableHeaders */
  headers?: string[];
  /** @deprecated use tableRows */
  rows?: string[][];
}

export interface AnalysisReport {
  id: string;
  title: string;
  type: 'review' | 'stock' | 'batch';
  createdAt: string;
  sections: AnalysisReportSection[];
}

export interface BatchAnalysisReport {
  id: string;
  title: string;
  createdAt: string;
  summary: string;
  stockAnalyses: AnalysisReport[];
  commonalities: string[];
  differences: string[];
  batchAdvice: string;
}

export interface AnalysisResponse {
  id: string;
  report: AnalysisReport | BatchAnalysisReport;
  status: 'completed' | 'pending' | 'failed';
  message?: string;
}

// ========== Market Review ==========

export async function postReview(
  data: ReviewRequest
): Promise<ApiResponse<AnalysisResponse>> {
  return apiClient.post('/analysis/review', data);
}

// ========== Stock Analysis ==========

export async function stockAnalysis(
  code: string,
  use_template: boolean = true
): Promise<ApiResponse<AnalysisResponse>> {
  return apiClient.post('/analysis/stock', { code, use_template });
}

// ========== Batch Analysis ==========

export async function batchAnalysis(
  data: BatchAnalysisRequest
): Promise<ApiResponse<AnalysisResponse>> {
  return apiClient.post('/analysis/batch', data);
}

// ========== Download ==========

export async function downloadReport(
  reportId: string,
  format: 'txt' | 'markdown'
): Promise<Blob> {
  const response = await apiClient.get(`/analysis/download/${reportId}`, {
    params: { format },
    responseType: 'blob',
  });
  return response as unknown as Blob;
}
