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

async function findAndDownloadArtifact({github, context, artifactName, destZipPath}) {
    const {owner, repo} = context.repo;
    const run_id = context.payload.workflow_run.id;

    const {data: list} = await github.rest.actions.listWorkflowRunArtifacts({
        owner,
        repo,
        run_id,
    });

    const matchingArtifacts = list.artifacts.filter((a) => a.name === artifactName);
    if (matchingArtifacts.length === 0) {
        throw new Error(`Artifact not found: ${artifactName}`);
    }

    matchingArtifacts.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    const latestArtifact = matchingArtifacts[0];

    const {data: zipData} = await github.rest.actions.downloadArtifact({
        owner,
        repo,
        artifact_id: latestArtifact.id,
        archive_format: "zip",
    });

    fs.writeFileSync(destZipPath, Buffer.from(zipData));
}

module.exports = {findAndDownloadArtifact};