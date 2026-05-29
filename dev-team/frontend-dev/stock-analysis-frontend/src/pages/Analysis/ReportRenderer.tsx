/**
 * 分析报告渲染组件 — 完整Markdown渲染
 * 直接显示AI返回的原始Markdown内容，保留所有格式
 */
import React from 'react';
import { Typography, Divider } from 'antd';

const { Text } = Typography;

interface ReportRendererProps {
  sections: { title: string; content: string }[];
  rawContent?: string;
}

/** 渲染Markdown表格（连续的行组成一个表格） */
function renderTable(rows: string[], startIdx: number): React.ReactNode {
  // 过滤掉分隔行（| --- | --- |）和空行
  const dataRows = rows.filter(r => r.includes('|') && !/^\|?\s*:?-+:?\s*\|/.test(r));
  if (dataRows.length < 2) return null;

  // 第一行是表头
  const headerCells = dataRows[0].split('|').filter(c => c.trim()).map(c => c.trim());
  // 其余是数据行
  const bodyRows = dataRows.slice(1).map(row =>
    row.split('|').filter(c => c.trim()).map(c => c.trim())
  ).filter(r => r.length > 0);

  return (
    <div key={startIdx} style={{ overflowX: 'auto', margin: '8px 0' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ background: '#fafafa' }}>
            {headerCells.map((h, i) => (
              <th key={i} style={{ border: '1px solid #e8e8e8', padding: '6px 10px', fontWeight: 600, textAlign: 'left', whiteSpace: 'nowrap' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {bodyRows.map((row, ri) => (
            <tr key={ri} style={{ background: ri % 2 === 0 ? '#fff' : '#fafafa' }}>
              {row.map((cell, ci) => (
                <td key={ci} style={{ border: '1px solid #e8e8e8', padding: '5px 10px', whiteSpace: ci === 0 ? 'nowrap' : 'normal' }}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** 将文本行分组为段落/列表/表格等块 */
function groupIntoBlocks(lines: string[]): React.ReactNode[] {
  const blocks: React.ReactNode[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i].trim();

    // 检测表格块（连续多行以 | 开头或包含 | 且中间有 --- 分隔行）
    if (line.startsWith('|')) {
      const tableRows: string[] = [];
      while (i < lines.length && (lines[i].trim().startsWith('|') || /^\|?\s*:?-+:?\s*\|/.test(lines[i].trim()))) {
        tableRows.push(lines[i]);
        i++;
      }
      blocks.push(renderTable(tableRows, blocks.length));
      continue;
    }

    // 一级标题
    if (line.startsWith('# ')) {
      blocks.push(<h1 key={i} style={{ fontSize: 20, fontWeight: 700, marginTop: 20, marginBottom: 12 }}>{line.slice(2)}</h1>);
      i++;
      continue;
    }
    // 二级标题
    if (line.startsWith('## ')) {
      blocks.push(<h2 key={i} style={{ fontSize: 17, fontWeight: 700, marginTop: 16, marginBottom: 10, color: '#262626' }}>{line.slice(3)}</h2>);
      i++;
      continue;
    }
    // 三级标题
    if (line.startsWith('### ')) {
      blocks.push(<h3 key={i} style={{ fontSize: 15, fontWeight: 600, marginTop: 14, marginBottom: 8, color: '#434343' }}>{line.slice(4)}</h3>);
      i++;
      continue;
    }
    // 四级标题
    if (line.startsWith('#### ')) {
      blocks.push(<h4 key={i} style={{ fontSize: 14, fontWeight: 600, marginTop: 10, marginBottom: 6, color: '#595959' }}>{line.slice(5)}</h4>);
      i++;
      continue;
    }

    // 分割线（但不是表格分隔行）
    if (/^\s*-{3,}\s*$/.test(line)) {
      blocks.push(<Divider key={i} style={{ margin: '12px 0' }} />);
      i++;
      continue;
    }

    // 无序列表
    if (line.startsWith('- ') || line.startsWith('* ')) {
      const content = line.slice(2);
      blocks.push(
        <div key={i} style={{ paddingLeft: 16, marginBottom: 2, lineHeight: 1.8 }}>
          <span style={{ color: '#8c8c8c', marginRight: 6 }}>•</span>
          {renderInline(content)}
        </div>
      );
      i++;
      continue;
    }

    // 有序列表
    const orderedMatch = line.match(/^(\d+)\.\s+/);
    if (orderedMatch) {
      const content = line.slice(orderedMatch[0].length);
      blocks.push(
        <div key={i} style={{ paddingLeft: 16, marginBottom: 2, lineHeight: 1.8 }}>
          <span style={{ color: '#8c8c8c', marginRight: 6 }}>{orderedMatch[1]}.</span>
          {renderInline(content)}
        </div>
      );
      i++;
      continue;
    }

    // 空行
    if (!line) {
      blocks.push(<div key={i} style={{ height: 8 }} />);
      i++;
      continue;
    }

    // 普通段落
    blocks.push(<div key={i} style={{ lineHeight: 1.9, marginBottom: 4, fontSize: 13, color: '#333' }}>{renderInline(line)}</div>);
    i++;
  }
  return blocks;
}

/** 渲染行内内容（处理加粗、颜色标记） */

/** 渲染行内内容（处理加粗、颜色标记） */
function renderInline(text: string): React.ReactNode {
  // 替换 **bold** → <strong>
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

const ReportRenderer: React.FC<ReportRendererProps> = ({ sections, rawContent }) => {
  // 如果有原始Markdown内容，直接渲染（使用新的块分组渲染）
  if (rawContent) {
    const lines = rawContent.split('\n');
    const blocks = groupIntoBlocks(lines);
    return (
      <div style={{ padding: '8px 4px' }}>
        {blocks}
      </div>
    );
  }

  // 兼容旧的sections格式
  if (!sections || sections.length === 0) {
    return <div style={{ textAlign: 'center', padding: 40, color: '#8c8c8c' }}>暂无分析内容</div>;
  }

  // 将sections合并为Markdown文本再渲染
  const rawLines: string[] = [];
  for (const sec of sections) {
    rawLines.push(`### ${sec.title}`);
    rawLines.push('');
    if (sec.content) {
      rawLines.push(sec.content);
      rawLines.push('');
    }
  }
  const blocks = groupIntoBlocks(rawLines);
  return (
    <div style={{ padding: '8px 4px' }}>
      {blocks}
    </div>
  );
};

export default ReportRenderer;
