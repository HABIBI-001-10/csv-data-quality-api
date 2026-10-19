/**
 * CSV Data Quality Studio - Frontend Controller
 * Handles file uploads, drag-and-drop, API interactions, dynamic DOM rendering,
 * and client-side downloads for CSV profiling, validation, and cleaning.
 */

// Global State
let currentFile = null;
let currentProfile = null;
let currentValidation = null;
let currentCleaningReport = null;

// DOM Elements
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const fileStatusArea = document.getElementById('fileStatusArea');
const fileStatusText = document.getElementById('fileStatusText');
const statusDot = document.getElementById('statusDot');
const resetBtn = document.getElementById('resetBtn');
const loadSampleBtn = document.getElementById('loadSampleBtn');
const workspace = document.getElementById('workspace');
const loadingOverlay = document.getElementById('loadingOverlay');
const loadingMessage = document.getElementById('loadingMessage');
const toastContainer = document.getElementById('toastContainer');

// Navigation Tabs
const tabButtons = document.querySelectorAll('.tab-btn');
const tabPanels = document.querySelectorAll('.tab-panel');
const tabBtnComparison = document.getElementById('tabBtnComparison');

// Action Buttons
const runValidationBtn = document.getElementById('runValidationBtn');
const downloadReportBtn = document.getElementById('downloadReportBtn');
const previewCleaningBtn = document.getElementById('previewCleaningBtn');
const cleanAndDownloadBtn = document.getElementById('cleanAndDownloadBtn');
const downloadCleanedFromComparisonBtn = document.getElementById('downloadCleanedFromComparisonBtn');
const addTypeConversionBtn = document.getElementById('addTypeConversionBtn');
const typeConversionsList = document.getElementById('typeConversionsList');

// Form Selectors & Inputs
const cleanMissingStrategy = document.getElementById('cleanMissingStrategy');
const fillValueContainer = document.getElementById('fillValueContainer');
const cleanFillValue = document.getElementById('cleanFillValue');
const dropColumnsList = document.getElementById('dropColumnsList');
const ruleEmailCols = document.getElementById('ruleEmailCols');
const ruleDateCols = document.getElementById('ruleDateCols');
const ruleRequiredCols = document.getElementById('ruleRequiredCols');
const ruleDateFormat = document.getElementById('ruleDateFormat');

// ---------------------------------------------------------------------------
// Toast & Loading Helpers
// ---------------------------------------------------------------------------

function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.role = 'alert';
  toast.innerHTML = `<span>${escapeHtml(message)}</span><button type="button" aria-label="Close" style="background:none;border:none;cursor:pointer;font-weight:bold;color:inherit;">&times;</button>`;
  
  toast.querySelector('button').addEventListener('click', () => toast.remove());
  toastContainer.appendChild(toast);
  setTimeout(() => { if (toast.parentNode) toast.remove(); }, 5000);
}

function showLoading(msg = 'Processing dataset...') {
  loadingMessage.textContent = msg;
  loadingOverlay.style.display = 'flex';
}

function hideLoading() {
  loadingOverlay.style.display = 'none';
}

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ---------------------------------------------------------------------------
// Tab Switching
// ---------------------------------------------------------------------------

tabButtons.forEach(btn => {
  btn.addEventListener('click', () => {
    const targetPanelId = btn.getAttribute('aria-controls');
    switchTab(btn, targetPanelId);
  });
});

function switchTab(buttonEl, panelId) {
  tabButtons.forEach(b => {
    b.classList.remove('active');
    b.setAttribute('aria-selected', 'false');
  });
  tabPanels.forEach(p => p.classList.remove('active'));

  buttonEl.classList.add('active');
  buttonEl.setAttribute('aria-selected', 'true');
  const panel = document.getElementById(panelId);
  if (panel) panel.classList.add('active');
}

// ---------------------------------------------------------------------------
// File Upload & Drag-and-Drop Handling
// ---------------------------------------------------------------------------

dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
    handleFileSelection(e.dataTransfer.files[0]);
  }
});

fileInput.addEventListener('change', (e) => {
  if (e.target.files && e.target.files.length > 0) {
    handleFileSelection(e.target.files[0]);
  }
});

resetBtn.addEventListener('click', () => {
  currentFile = null;
  currentProfile = null;
  currentValidation = null;
  currentCleaningReport = null;
  fileInput.value = '';
  workspace.style.display = 'none';
  tabBtnComparison.style.display = 'none';
  resetBtn.style.display = 'none';
  statusDot.classList.remove('active');
  fileStatusText.textContent = 'No file uploaded yet.';
  showToast('Dataset cleared.', 'info');
});

// Handle Sample Data Loading
loadSampleBtn.addEventListener('click', async () => {
  showLoading('Loading sample messy dataset...');
  try {
    const sampleCsvContent = `Full Name,User Email!,Age (Years),Registration Date,Account Balance ($),Department
  Alice Johnson  ,alice.johnson@example.com,29,2023-01-15,1450.50,Engineering
Bob Smith,bob.smith-at-domain.com,34,2022-11-05,2300.00,Marketing
Charlie Brown,charlie@brown.org,unknown,2023-02-30,-120.00,Design
Diana Prince,diana.prince@wonder.com,28,2021-08-19,5400.75,Engineering
Diana Prince,diana.prince@wonder.com,28,2021-08-19,5400.75,Engineering
Evan Wright,evan.wright@company,45,2020-04-12,890.20,Sales
Fiona Gallagher,,31,2022-09-10,3100.00,Finance
George Clark,george.clark@business.co.uk,52,not-a-date,4500.10,Operations
Hannah Abbott,hannah@hogwarts.edu,24,2023-03-01,950.00,Engineering
Ian Malcolm,ian.malcolm@jurassic.org,40,2019-06-11,=cmd|' /C calc'!A0,Research
Julia Roberts,julia.roberts@cinema.com,36,2023-05-22,  6700.50  ,
Kevin Bacon,kevin@bacon.net,39,2021-12-01,1200.00,Acting
  Alice Johnson  ,alice.johnson@example.com,29,2023-01-15,1450.50,Engineering`;

    const blob = new Blob([sampleCsvContent], { type: 'text/csv' });
    const sampleFile = new File([blob], 'messy_data.csv', { type: 'text/csv' });
    await handleFileSelection(sampleFile);
    showToast('Loaded messy sample data successfully!', 'success');
  } catch (err) {
    showToast('Failed to load sample dataset: ' + err.message, 'error');
  } finally {
    hideLoading();
  }
});

async function handleFileSelection(file) {
  if (!file) return;

  if (!file.name.toLowerCase().endsWith('.csv')) {
    showToast('Please select a file with .csv extension.', 'error');
    return;
  }

  const maxBytes = 10 * 1024 * 1024;
  if (file.size > maxBytes) {
    showToast('File size exceeds the 10 MB limit.', 'error');
    return;
  }

  currentFile = file;
  fileStatusText.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
  statusDot.classList.add('active');
  resetBtn.style.display = 'inline-flex';

  // Run initial profile and default validation
  await processDataset(file);
}

// ---------------------------------------------------------------------------
// Profiling & Initial Processing Pipeline
// ---------------------------------------------------------------------------

async function processDataset(file) {
  showLoading('Analyzing and profiling CSV dataset...');
  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/profile', {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.message || 'Failed to profile CSV file.');
    }

    currentProfile = await res.json();
    renderProfile(currentProfile);

    // Populate column configuration dropdowns
    populateColumnSelectors(currentProfile.column_names);

    // Trigger initial validation with default rules
    await runValidation();

    workspace.style.display = 'block';
    showToast(`Successfully analyzed ${currentProfile.total_rows} rows.`, 'success');
  } catch (err) {
    showToast(err.message, 'error');
    workspace.style.display = 'none';
  } finally {
    hideLoading();
  }
}

function renderProfile(profile) {
  // Update Overview Cards
  document.getElementById('metricTotalRows').textContent = profile.total_rows.toLocaleString();
  document.getElementById('metricMemory').textContent = `${profile.memory_usage_kb} KB`;
  document.getElementById('metricTotalCols').textContent = profile.total_columns;
  document.getElementById('metricColsBadge').textContent = `${profile.total_columns} columns`;

  const totalMissing = profile.columns.reduce((sum, c) => sum + c.missing_count, 0);
  const totalCells = profile.total_rows * profile.total_columns;
  const missingPct = totalCells > 0 ? ((totalMissing / totalCells) * 100).toFixed(1) : '0';
  document.getElementById('metricMissingCount').textContent = totalMissing.toLocaleString();
  document.getElementById('metricMissingPct').textContent = `${missingPct}% of cells`;

  document.getElementById('metricDuplicateCount').textContent = profile.duplicate_rows.toLocaleString();
  document.getElementById('metricDuplicatePct').textContent = `${profile.duplicate_percentage}% dupes`;

  // Render Preview Table
  const thead = document.getElementById('previewTableHead');
  thead.innerHTML = '';
  profile.column_names.forEach(col => {
    const th = document.createElement('th');
    th.textContent = col;
    thead.appendChild(th);
  });

  const tbody = document.getElementById('previewTableBody');
  tbody.innerHTML = '';
  document.getElementById('previewRowCounter').textContent = `Showing first ${profile.preview.length} of ${profile.total_rows} rows`;

  profile.preview.forEach(row => {
    const tr = document.createElement('tr');
    profile.column_names.forEach(col => {
      const td = document.createElement('td');
      const val = row[col];
      if (val === null || val === undefined) {
        td.innerHTML = '<span class="text-muted" style="font-style: italic;">null</span>';
      } else {
        td.textContent = val;
      }
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  // Render Column Profiles Table
  const colBody = document.getElementById('columnsProfileBody');
  colBody.innerHTML = '';

  profile.columns.forEach(col => {
    const tr = document.createElement('tr');
    
    // Column Name
    const tdName = document.createElement('td');
    tdName.innerHTML = `<strong>${escapeHtml(col.name)}</strong>`;
    tr.appendChild(tdName);

    // Data Type
    const tdType = document.createElement('td');
    tdType.innerHTML = `<span class="badge badge-neutral">${escapeHtml(col.data_type)}</span>`;
    tr.appendChild(tdType);

    // Missing Values
    const tdMissing = document.createElement('td');
    const badgeClass = col.missing_count > 0 ? 'badge-warning' : 'badge-success';
    tdMissing.innerHTML = `<span class="badge ${badgeClass}">${col.missing_count} (${col.missing_percentage}%)</span>`;
    tr.appendChild(tdMissing);

    // Unique Values
    const tdUnique = document.createElement('td');
    tdUnique.textContent = col.unique_count;
    tr.appendChild(tdUnique);

    // Numeric Stats
    const tdStats = document.createElement('td');
    if (col.stats && col.stats.count > 0) {
      tdStats.innerHTML = `<small class="text-muted">Min: ${col.stats.min} | Mean: ${col.stats.mean} | Med: ${col.stats.median} | Max: ${col.stats.max}</small>`;
    } else {
      tdStats.innerHTML = '<span class="text-muted">-</span>';
    }
    tr.appendChild(tdStats);

    // Sample Values
    const tdSamples = document.createElement('td');
    if (col.sample_values && col.sample_values.length > 0) {
      tdSamples.textContent = col.sample_values.join(', ');
    } else {
      tdSamples.innerHTML = '<span class="text-muted">No values</span>';
    }
    tr.appendChild(tdSamples);

    colBody.appendChild(tr);
  });
}

function populateColumnSelectors(columns) {
  // Populate email & date multi-selects
  ruleEmailCols.innerHTML = '';
  ruleDateCols.innerHTML = '';
  columns.forEach(col => {
    const optEmail = new Option(col, col);
    if (/email/i.test(col)) optEmail.selected = true;
    ruleEmailCols.add(optEmail);

    const optDate = new Option(col, col);
    if (/date|time/i.test(col)) optDate.selected = true;
    ruleDateCols.add(optDate);
  });

  // Populate Drop Columns checkboxes
  dropColumnsList.innerHTML = '';
  columns.forEach(col => {
    const label = document.createElement('label');
    label.className = 'checkbox-label';
    label.innerHTML = `<input type="checkbox" name="dropCol" value="${escapeHtml(col)}"> <span>${escapeHtml(col)}</span>`;
    dropColumnsList.appendChild(label);
  });

  // Clear type conversions list
  typeConversionsList.innerHTML = '<p class="form-hint">Cast specific columns to clean types with error coercion:</p>';
}

// ---------------------------------------------------------------------------
// Quality Audit & Validation Pipeline
// ---------------------------------------------------------------------------

runValidationBtn.addEventListener('click', async () => {
  await runValidation();
});

async function runValidation() {
  if (!currentFile) return;

  showLoading('Auditing dataset quality rules...');
  
  // Assemble rules
  const requiredCols = ruleRequiredCols.value
    .split(',')
    .map(s => s.trim())
    .filter(Boolean);

  const selectedEmailCols = Array.from(ruleEmailCols.selectedOptions).map(o => o.value);
  const selectedDateCols = Array.from(ruleDateCols.selectedOptions).map(o => o.value);
  const dateFormat = ruleDateFormat.value.trim() || null;

  const rules = {
    required_columns: requiredCols,
    email_columns: selectedEmailCols,
    date_columns: selectedDateCols,
    date_format: dateFormat,
    check_duplicates: document.getElementById('checkDuplicates').checked,
    check_empty_columns: document.getElementById('checkEmptyCols').checked,
    check_missing_values: document.getElementById('checkMissingVals').checked,
  };

  const formData = new FormData();
  formData.append('file', currentFile);
  formData.append('rules', JSON.stringify(rules));

  try {
    const res = await fetch('/api/validate', {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.message || 'Validation request failed.');
    }

    currentValidation = await res.json();
    renderValidationResults(currentValidation);
    downloadReportBtn.disabled = false;
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    hideLoading();
  }
}

function renderValidationResults(report) {
  const issuesBody = document.getElementById('issuesTableBody');
  issuesBody.innerHTML = '';

  const issueCountBadge = document.getElementById('validationIssueBadge');
  issueCountBadge.textContent = report.summary.total_issues;

  // Overview status
  const statusEl = document.getElementById('metricQualityStatus');
  const countEl = document.getElementById('metricQualityCount');
  statusEl.className = 'status-badge';

  if (report.summary.status === 'errors_found') {
    statusEl.classList.add('errors');
    statusEl.textContent = 'Errors Found';
  } else if (report.summary.status === 'warnings_found') {
    statusEl.classList.add('warnings');
    statusEl.textContent = 'Warnings Found';
  } else {
    statusEl.classList.add('passed');
    statusEl.textContent = 'Passed';
  }
  countEl.textContent = `${report.summary.total_issues} issues (${report.summary.error_count} err, ${report.summary.warning_count} warn)`;

  document.getElementById('validationSubtitle').textContent = 
    `Identified ${report.summary.total_issues} issues across dataset: ${report.summary.error_count} errors, ${report.summary.warning_count} warnings.`;

  if (report.issues.length === 0) {
    issuesBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted" style="padding: 2rem;">No data quality issues detected! The dataset satisfies all rules.</td></tr>';
    return;
  }

  report.issues.forEach(issue => {
    const tr = document.createElement('tr');
    
    // Severity Badge
    const tdSev = document.createElement('td');
    const badgeClass = issue.severity === 'error' ? 'badge-error' : 'badge-warning';
    tdSev.innerHTML = `<span class="badge ${badgeClass}">${issue.severity.toUpperCase()}</span>`;
    tr.appendChild(tdSev);

    // Issue Type
    const tdType = document.createElement('td');
    tdType.innerHTML = `<span class="badge badge-neutral">${escapeHtml(issue.issue_type)}</span>`;
    tr.appendChild(tdType);

    // Column
    const tdCol = document.createElement('td');
    tdCol.textContent = issue.column || '(all columns)';
    tr.appendChild(tdCol);

    // Row Number
    const tdRow = document.createElement('td');
    tdRow.textContent = issue.row ? `Row ${issue.row}` : '-';
    tr.appendChild(tdRow);

    // Description
    const tdDesc = document.createElement('td');
    tdDesc.textContent = issue.message;
    tr.appendChild(tdDesc);

    // Sample Value
    const tdSample = document.createElement('td');
    if (issue.sample_value !== null && issue.sample_value !== undefined) {
      tdSample.innerHTML = `<code>${escapeHtml(issue.sample_value)}</code>`;
    } else {
      tdSample.innerHTML = '<span class="text-muted">-</span>';
    }
    tr.appendChild(tdSample);

    issuesBody.appendChild(tr);
  });
}

// Download JSON Validation Report
downloadReportBtn.addEventListener('click', async () => {
  if (!currentFile) return;

  showLoading('Preparing JSON validation report...');
  const formData = new FormData();
  formData.append('file', currentFile);
  if (currentValidation && currentValidation.rules_applied) {
    formData.append('rules', JSON.stringify(currentValidation.rules_applied));
  }

  try {
    const res = await fetch('/api/report', {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) throw new Error('Failed to generate report file.');

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `validation_report_${currentFile.name.replace(/\.csv$/i, '')}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
    showToast('Downloaded validation report JSON.', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    hideLoading();
  }
});

// ---------------------------------------------------------------------------
// Cleaning Configuration & Execution
// ---------------------------------------------------------------------------

cleanMissingStrategy.addEventListener('change', () => {
  if (cleanMissingStrategy.value === 'fill_value') {
    fillValueContainer.style.display = 'block';
  } else {
    fillValueContainer.style.display = 'none';
  }
});

// Add Dynamic Type Conversion Row
addTypeConversionBtn.addEventListener('click', () => {
  if (!currentProfile) return;

  const row = document.createElement('div');
  row.className = 'type-conversion-row';

  const colSelect = document.createElement('select');
  colSelect.className = 'form-control';
  currentProfile.column_names.forEach(c => colSelect.add(new Option(c, c)));

  const typeSelect = document.createElement('select');
  typeSelect.className = 'form-control';
  ['integer', 'float', 'string', 'date', 'boolean'].forEach(t => typeSelect.add(new Option(t, t)));

  const removeBtn = document.createElement('button');
  removeBtn.type = 'button';
  removeBtn.className = 'btn btn-ghost btn-sm';
  removeBtn.textContent = '✕';
  removeBtn.addEventListener('click', () => row.remove());

  row.appendChild(colSelect);
  row.appendChild(typeSelect);
  row.appendChild(removeBtn);
  typeConversionsList.appendChild(row);
});

function getCleaningConfigFromForm() {
  const dropCols = Array.from(document.querySelectorAll('input[name="dropCol"]:checked')).map(cb => cb.value);

  const conversions = [];
  document.querySelectorAll('.type-conversion-row').forEach(row => {
    const selects = row.querySelectorAll('select');
    if (selects.length >= 2) {
      conversions.push({
        column: selects[0].value,
        target_type: selects[1].value,
        on_error: 'coerce',
      });
    }
  });

  return {
    drop_duplicates: document.getElementById('cleanDropDuplicates').checked,
    trim_whitespace: document.getElementById('cleanTrimWhitespace').checked,
    standardize_column_names: document.getElementById('cleanStandardizeCols').checked,
    sanitize_formulas: document.getElementById('cleanSanitizeFormulas').checked,
    drop_columns: dropCols,
    missing_value_strategy: cleanMissingStrategy.value,
    fill_value: cleanFillValue.value.trim() || null,
    type_conversions: conversions,
  };
}

// Preview Cleaning Changes
previewCleaningBtn.addEventListener('click', async () => {
  if (!currentFile) return;

  showLoading('Generating cleaning preview...');
  const config = getCleaningConfigFromForm();
  const formData = new FormData();
  formData.append('file', currentFile);
  formData.append('config', JSON.stringify(config));

  try {
    const res = await fetch('/api/clean/preview', {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.message || 'Cleaning preview failed.');
    }

    currentCleaningReport = await res.json();
    renderComparison(currentCleaningReport);

    // Reveal comparison tab and switch to it
    tabBtnComparison.style.display = 'inline-flex';
    switchTab(tabBtnComparison, 'tabComparison');
    showToast('Generated cleaning comparison summary!', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    hideLoading();
  }
});

// Clean & Direct Download CSV
cleanAndDownloadBtn.addEventListener('click', async () => {
  await executeCleanAndDownload();
});

downloadCleanedFromComparisonBtn.addEventListener('click', async () => {
  await executeCleanAndDownload();
});

async function executeCleanAndDownload() {
  if (!currentFile) return;

  showLoading('Cleaning dataset and generating export file...');
  const config = getCleaningConfigFromForm();
  const formData = new FormData();
  formData.append('file', currentFile);
  formData.append('config', JSON.stringify(config));

  try {
    const res = await fetch('/api/clean', {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.message || 'Cleaning operation failed.');
    }

    // Trigger file download in browser
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cleaned_${currentFile.name}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    showToast('Cleaned CSV downloaded successfully!', 'success');

    // Also auto-fetch preview to update the comparison tab
    if (!currentCleaningReport) {
      previewCleaningBtn.click();
    }
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    hideLoading();
  }
}

// ---------------------------------------------------------------------------
// Render Comparison Tab
// ---------------------------------------------------------------------------

function renderComparison(report) {
  document.getElementById('diffRowsBefore').textContent = report.rows_before;
  document.getElementById('diffRowsAfter').textContent = report.rows_after;
  document.getElementById('diffRowsRemoved').textContent = `${report.rows_removed} removed`;

  document.getElementById('diffColsBefore').textContent = report.columns_before;
  document.getElementById('diffColsAfter').textContent = report.columns_after;
  document.getElementById('diffColsRemoved').textContent = `${report.columns_removed} removed`;

  document.getElementById('diffMissingBefore').textContent = report.missing_before;
  document.getElementById('diffMissingAfter').textContent = report.missing_after;
  document.getElementById('diffMissingResolved').textContent = `${report.missing_resolved} resolved`;

  document.getElementById('diffDupsBefore').textContent = report.duplicates_before;
  document.getElementById('diffDupsAfter').textContent = report.duplicates_after;
  document.getElementById('diffDupsRemoved').textContent = `${report.duplicates_before - report.duplicates_after} dropped`;

  // Operations Log
  const opList = document.getElementById('operationsAppliedList');
  opList.innerHTML = '';
  if (report.operations_applied && report.operations_applied.length > 0) {
    report.operations_applied.forEach(op => {
      const li = document.createElement('li');
      li.innerHTML = `<strong>${escapeHtml(op.name)}:</strong> ${escapeHtml(op.description)} <span class="badge badge-neutral">${op.affected_count} affected</span>`;
      opList.appendChild(li);
    });
  } else {
    opList.innerHTML = '<li class="text-muted">No transformations were needed or selected.</li>';
  }

  // Render Cleaned Preview Table
  const thead = document.getElementById('cleanedPreviewHead');
  thead.innerHTML = '';
  report.cleaned_column_names.forEach(col => {
    const th = document.createElement('th');
    th.textContent = col;
    thead.appendChild(th);
  });

  const tbody = document.getElementById('cleanedPreviewBody');
  tbody.innerHTML = '';
  report.preview_after.forEach(row => {
    const tr = document.createElement('tr');
    report.cleaned_column_names.forEach(col => {
      const td = document.createElement('td');
      const val = row[col];
      if (val === null || val === undefined) {
        td.innerHTML = '<span class="text-muted" style="font-style: italic;">null</span>';
      } else {
        td.textContent = val;
      }
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
}
