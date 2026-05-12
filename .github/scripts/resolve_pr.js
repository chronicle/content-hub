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

async function findPullRequestForWorkflowRun({github, context}) {
    const run = context.payload.workflow_run;

    // Fallback 0: direct from payload
    let pr = (run.pull_requests && run.pull_requests[0]) || null;

    // Fallback 1: by commit SHA (works for same-repo PRs)
    if (!pr) {
        const {owner, repo} = context.repo;
        const sha = run.head_sha;
        const {data: prsBySha} = await github.rest.repos.listPullRequestsAssociatedWithCommit({
            owner,
            repo,
            commit_sha: sha,
        });

        if (prsBySha.length > 1) {
            // Pick the PR with the most recent update
            prsBySha.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
        }
        pr = prsBySha[0] || null;
    }

    // Fallback 2: by head "owner:branch" (works for forks)
    if (!pr) {
        const headRepo = run.head_repository && run.head_repository.full_name;
        const headBranch = run.head_branch; // "feature"
        if (headRepo && headBranch) {
            const headParam = `${headRepo.split("/")[0]}:${headBranch}`;
            const {owner, repo} = context.repo;

            const {data: openPRs} = await github.rest.pulls.list({
                owner,
                repo,
                state: "open",
                head: headParam,
                per_page: 100,
            });
            if (openPRs.length > 1) {
                openPRs.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
            }
            pr = openPRs[0] || null;

            if (!pr) {
                const {data: closedPRs} = await github.rest.pulls.list({
                    owner,
                    repo,
                    state: "closed",
                    head: headParam,
                    per_page: 100,
                });
                if (closedPRs.length > 1) {
                    closedPRs.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
                }
                pr = closedPRs[0] || null;
            }
        }
    }

    if (!pr) throw new Error("Could not resolve PR for this workflow_run.");
    return Number(pr.number);
}

module.exports = {findPullRequestForWorkflowRun};