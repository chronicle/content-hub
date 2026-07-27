// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

document.addEventListener('DOMContentLoaded', function() {
  // --- Theme Management ---
  const html = document.documentElement;
  const storedTheme = localStorage.getItem('theme');
  const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

  if (storedTheme === 'dark' || (!storedTheme && systemPrefersDark)) {
    html.classList.add('dark');
  }

  function toggleDarkMode() {
    const isDark = html.classList.toggle('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
  }

  // --- Accordion Logic ---
  function toggleAccordion(element) {
    const content = element.nextElementSibling;
    if (content && content.classList.contains('collapsible-content')) {
      const parent = element.parentElement;
      const isOpen = parent.classList.toggle('is-open');
      content.classList.toggle('is-open', isOpen);
    }
  }

  // --- Search Filtering ---
  function filterIntegrations(query) {
    const q = query.toLowerCase().trim();
    const items = document.querySelectorAll('.integration-item');
    items.forEach(item => {
      const name = item.getAttribute('data-name') || '';
      if (name.includes(q)) {
        item.style.display = '';
      } else {
        item.style.display = 'none';
      }
    });
  }

  // --- Global Controls ---
  function expandAll() {
    document.querySelectorAll('.integration-item').forEach(item => {
      item.classList.add('is-open');
      const content = item.querySelector('.collapsible-content');
      if (content) content.classList.add('is-open');
    });
  }

  function collapseAll() {
    document.querySelectorAll('.integration-item').forEach(item => {
      item.classList.remove('is-open');
      const content = item.querySelector('.collapsible-content');
      if (content) content.classList.remove('is-open');
    });
  }

  // --- Report Export ---
  function downloadReport() {
    const docClone = document.documentElement.cloneNode(true);
    const blob = new Blob([docClone.outerHTML], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `test-report-${new Date().toISOString().slice(0, 10)}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // --- Public API ---
  window.toggleDarkMode = toggleDarkMode;
  window.toggleAccordion = toggleAccordion;
  window.filterIntegrations = filterIntegrations;
  window.expandAll = expandAll;
  window.collapseAll = collapseAll;
  window.downloadReport = downloadReport;

  // Initialize
  filterIntegrations('');
});
