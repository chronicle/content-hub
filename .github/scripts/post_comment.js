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

async function postComment({github, context, prNumber, title, reportPath}) {
    const body = fs.readFileSync(reportPath, "utf8");
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

module.exports = {postComment};
