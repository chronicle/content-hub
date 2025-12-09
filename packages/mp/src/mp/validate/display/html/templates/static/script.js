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

  function toggleAccordion(element) {
    const content = element.nextElementSibling;
    if (content && content.classList.contains('collapsible-content')) {
      element.parentElement.classList.toggle('is-open');
      content.classList.toggle('is-open');
    }
  }

  /**
   * Switches tabs within a specific scope.
   * @param {HTMLElement} buttonElement The clicked tab button.
   * @param {string} contentId The ID of the content to show.
   * @param {string} scopeSelector CSS selector to limit the scope (e.g., '.main-tabs', '.sub-tabs-integrations')
   */
  function switchTab(buttonElement, contentId, scopeSelector) {
    // Find the container for this set of tabs
    const container = buttonElement.closest(scopeSelector || '.tab-container');

    if (!container) return;

    // Deactivate all buttons in this container
    container.querySelectorAll('.tab-button').forEach(button => button.classList.remove('active'));

    // Activate clicked button
    buttonElement.classList.add('active');

    // Hide all content sections associated with this container
    // We look for the sibling content container
    const contentContainer = container.nextElementSibling || container.parentElement.querySelector('.tab-content-container');

    if (contentContainer) {
      // Hide direct children that are tab contents
      Array.from(contentContainer.children).forEach(child => {
        if (child.classList.contains('tab-content')) {
          child.classList.add('hidden');
        }
      });
    }

    // Show target content
    const targetContent = document.getElementById(contentId);
    if (targetContent) {
      targetContent.classList.remove('hidden');
    }
  }

  function downloadReport() {
    const htmlContent = document.documentElement.outerHTML;
    const blob = new Blob([htmlContent], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `validation-report-${new Date().toISOString().slice(0,10)}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  window.toggleAccordion = toggleAccordion;
  window.switchTab = switchTab;
  window.downloadReport = downloadReport;

  // Initialize: Click the first tab in every tab-container
  document.querySelectorAll('.tab-container').forEach(container => {
    const firstTab = container.querySelector('.tab-button');
    if (firstTab) firstTab.click();
  });
});