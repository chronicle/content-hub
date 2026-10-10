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

const fs = require("fs");

/**
 * Redacts potential credentials and SOAR tenant hostnames from CI report text
 * before posting it to a public pull request comment.
 *
 * @param {string} rawText The raw report markdown content.
 * @return {string} The sanitized report content with secrets redacted.
 */
function redactSensitivePatterns(rawText) {
    return rawText
        .replace(
            /((?:x-?siemplify-?app-?key|x-?app-?key|siemplify[_-]?app[_-]?key|eval[_-]?sdk[_-]?app[_-]?key|soar[_-]?api[_-]?key|app[_-]?key|api[_-]?key)["']?\s*[:=]\s*["']?)([A-Za-z0-9+/]{43}=|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/gi,
            "$1[REDACTED_APP_KEY]"
        )
        .replace(
            /((?:--api-key|--password|access[_-]?key|secret[_-]?key)\s*[:=]?\s*["']?)([^\s"'<>]{8,})/gi,
            "$1[REDACTED_SECRET]"
        )
        .replace(
            /\b([a-z0-9][a-z0-9-]{0,62})\.siemplify-soar\.com\b/gi,
            "[REDACTED_TENANT].siemplify-soar.com"
        );
}

/**
 * Posts a collapsible CI failure report comment on a pull request.
 *
 * @param {{github: object, context: object, prNumber: number, title: string, reportPath: string}} params
 *   The GitHub client context, pull request number, comment title, and report file path.
 * @return {Promise<void>} A promise that resolves when the comment is created.
 */
async function postComment({github, context, prNumber, title, reportPath}) {
    const rawBody = fs.readFileSync(reportPath, "utf8");
    const body = redactSensitivePatterns(rawBody);
    const comment =
        `❌ **${title}**\n` +
        `<details>\n<summary>Click to view the full report</summary>\n\n---\n` +
        body +
        `\n</details>`;

    await github.rest.issues.createComment({
        owner: context.repo.owner,
        repo: context.repo.repo,
        issue_number: prNumber,
        body: comment,
    });
}

module.exports = {postComment, redactSensitivePatterns};
