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

  // --- Tab Logic ---
  function switchTab(buttonElement, contentId) {
    const nav = buttonElement.closest('nav');
    if (!nav) return;

    // 1. Update Tab Buttons Appearance
    nav.querySelectorAll('.tab-button').forEach(btn => {
      btn.classList.remove('active', 'bg-white', 'dark:bg-slate-700', 'text-indigo-600', 'dark:text-white', 'shadow-sm');
      btn.classList.add('text-slate-500', 'dark:text-slate-400');
    });

    buttonElement.classList.add('active', 'bg-white', 'dark:bg-slate-700', 'text-indigo-600', 'dark:text-white', 'shadow-sm');
    buttonElement.classList.remove('text-slate-500', 'dark:text-slate-400');

    // 2. Show Target Content, Hide Siblings
    const targetContent = document.getElementById(contentId);
    if (targetContent) {
      const container = targetContent.parentElement;
      Array.from(container.children).forEach(child => {
        if (child.classList.contains('tab-content')) {
          child.classList.add('hidden');
        }
      });
      targetContent.classList.remove('hidden');
    }

    // 3. Reset Search when switching main tabs
    if (contentId.startsWith('group-')) {
        const searchInput = document.getElementById('integration-search');
        if (searchInput) {
            searchInput.value = '';
            filterIntegrations('');
        }
        // Also ensure the first sub-tab of the new group is "clicked" if none are active
        const firstSubTab = targetContent.querySelector('.tab-button');
        if (firstSubTab) firstSubTab.click();
    }
  }

  // --- Search Filtering ---
  function filterIntegrations(query) {
    const q = query.toLowerCase().trim();
    // Find the currently visible category content
    const activeGroup = document.querySelector('section.tab-content-container > .tab-content:not(.hidden)');
    if (!activeGroup) return;

    const activeCategory = activeGroup.querySelector('.tab-content-container > .tab-content:not(.hidden)');
    if (!activeCategory) return;

    const items = activeCategory.querySelectorAll('.integration-item');
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
  function getActiveItems() {
    const activeGroup = document.querySelector('section.tab-content-container > .tab-content:not(.hidden)');
    if (!activeGroup) return [];
    const activeCategory = activeGroup.querySelector('.tab-content-container > .tab-content:not(.hidden)');
    if (!activeCategory) return [];
    return activeCategory.querySelectorAll('.integration-item');
  }

  function expandAll() {
    getActiveItems().forEach(item => {
      item.classList.add('is-open');
      const content = item.querySelector('.collapsible-content');
      if (content) content.classList.add('is-open');
    });
  }

  function collapseAll() {
    getActiveItems().forEach(item => {
      item.classList.remove('is-open');
      const content = item.querySelector('.collapsible-content');
      if (content) content.classList.remove('is-open');
    });
  }

  // --- Report Export ---
  function downloadReport() {
    // Clone document to avoid modifying the current view
    const docClone = document.documentElement.cloneNode(true);

    // Ensure theme is baked into the clone if we want the downloaded file to respect current view
    // (Optional, currently it relies on the script running in the opened file)

    const blob = new Blob([docClone.outerHTML], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `validation-report-${new Date().toISOString().slice(0, 10)}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // --- Public API ---
  window.toggleDarkMode = toggleDarkMode;
  window.toggleAccordion = toggleAccordion;
  window.switchTab = switchTab;
  window.filterIntegrations = filterIntegrations;
  window.expandAll = expandAll;
  window.collapseAll = collapseAll;
  window.downloadReport = downloadReport;

  // --- Initialization ---
  // If no search query, ensure all items are shown (redundant but safe)
  filterIntegrations('');
});
