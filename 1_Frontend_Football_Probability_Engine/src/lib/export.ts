import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

interface ExportColumn {
  header: string;
  accessor: string | ((row: Record<string, unknown>) => string | number);
}

interface ExportOptions {
  filename: string;
  title?: string;
  subtitle?: string;
  columns: ExportColumn[];
  data: Record<string, unknown>[];
}

export function exportToCSV({ filename, columns, data }: ExportOptions) {
  const headers = columns.map(col => col.header);
  const rows = data.map(row =>
    columns.map(col => {
      const value = typeof col.accessor === 'function' 
        ? col.accessor(row) 
        : row[col.accessor];
      // Escape quotes and wrap in quotes if contains comma
      const stringValue = String(value ?? '');
      if (stringValue.includes(',') || stringValue.includes('"')) {
        return `"${stringValue.replace(/"/g, '""')}"`;
      }
      return stringValue;
    })
  );

  const csvContent = [
    headers.join(','),
    ...rows.map(row => row.join(','))
  ].join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${filename}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

export function exportToPDF({ filename, title, subtitle, columns, data }: ExportOptions) {
  const doc = new jsPDF();
  
  // Header
  doc.setFontSize(18);
  doc.setTextColor(33, 37, 41);
  doc.text(title || 'Report', 14, 20);
  
  if (subtitle) {
    doc.setFontSize(11);
    doc.setTextColor(108, 117, 125);
    doc.text(subtitle, 14, 28);
  }

  // Timestamp
  doc.setFontSize(9);
  doc.setTextColor(108, 117, 125);
  const timestamp = new Date().toLocaleString();
  doc.text(`Generated: ${timestamp}`, 14, subtitle ? 36 : 28);

  // Table
  const tableData = data.map(row =>
    columns.map(col => {
      const value = typeof col.accessor === 'function' 
        ? col.accessor(row) 
        : row[col.accessor];
      return String(value ?? '');
    })
  );

  autoTable(doc, {
    head: [columns.map(col => col.header)],
    body: tableData,
    startY: subtitle ? 42 : 34,
    styles: {
      fontSize: 9,
      cellPadding: 3,
    },
    headStyles: {
      fillColor: [55, 65, 81],
      textColor: [255, 255, 255],
      fontStyle: 'bold',
    },
    alternateRowStyles: {
      fillColor: [249, 250, 251],
    },
  });

  // Footer
  const pageCount = doc.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setTextColor(156, 163, 175);
    doc.text(
      `Page ${i} of ${pageCount}`,
      doc.internal.pageSize.width / 2,
      doc.internal.pageSize.height - 10,
      { align: 'center' }
    );
    doc.text(
      'This system estimates probabilities. It does not provide betting advice.',
      doc.internal.pageSize.width / 2,
      doc.internal.pageSize.height - 6,
      { align: 'center' }
    );
  }

  doc.save(`${filename}.pdf`);
}

// Audit-specific export
export interface AuditExportData {
  timestamp: string;
  action: string;
  modelVersion: string;
  probabilitySet: string;
  details: string;
}

export function exportAuditLog(entries: AuditExportData[], format: 'csv' | 'pdf') {
  const options: ExportOptions = {
    filename: `audit-log-${new Date().toISOString().split('T')[0]}`,
    title: 'Audit Trail Report',
    subtitle: 'Football Jackpot Probability Engine',
    columns: [
      { header: 'Timestamp', accessor: 'timestamp' },
      { header: 'Action', accessor: 'action' },
      { header: 'Model Version', accessor: 'modelVersion' },
      { header: 'Probability Set', accessor: 'probabilitySet' },
      { header: 'Details', accessor: 'details' },
    ],
    data: entries as unknown as Record<string, unknown>[],
  };

  if (format === 'csv') {
    exportToCSV(options);
  } else {
    exportToPDF(options);
  }
}

// Probability export
export interface ProbabilityExportData {
  homeTeam: string;
  awayTeam: string;
  homeWinProbability: number;
  drawProbability: number;
  awayWinProbability: number;
}

export function exportProbabilities(
  probabilities: ProbabilityExportData[], 
  setName: string,
  format: 'csv' | 'pdf'
) {
  const options: ExportOptions = {
    filename: `probabilities-${setName.toLowerCase().replace(/\s+/g, '-')}-${new Date().toISOString().split('T')[0]}`,
    title: 'Probability Report',
    subtitle: `${setName} - Football Jackpot Probability Engine`,
    columns: [
      { header: 'Home Team', accessor: 'homeTeam' },
      { header: 'Away Team', accessor: 'awayTeam' },
      { header: 'Home Win %', accessor: (row) => (row.homeWinProbability as number).toFixed(2) },
      { header: 'Draw %', accessor: (row) => (row.drawProbability as number).toFixed(2) },
      { header: 'Away Win %', accessor: (row) => (row.awayWinProbability as number).toFixed(2) },
    ],
    data: probabilities as unknown as Record<string, unknown>[],
  };

  if (format === 'csv') {
    exportToCSV(options);
  } else {
    exportToPDF(options);
  }
}
