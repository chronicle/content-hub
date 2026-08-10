# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import RuleEvaluationResult, VerdictEnum
from .rules import EvaluationRule


class EvaluationStorage:
    """SQLite storage engine for mp describe evaluate rule_evaluations table."""

    def __init__(self, db_path: Path | str) -> None:
        """Initialize EvaluationStorage.

        Args:
            db_path: Path to SQLite database file.

        """
        self.db_path = Path(db_path)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create sqlite3 connection with row factory.

        Returns:
            sqlite3 Connection object.

        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create rules and rule_evaluations tables and index if they do not exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS rules (
                    rule_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    target_field TEXT NOT NULL,
                    criteria TEXT NOT NULL
                );
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS rule_evaluations (
                    evaluation_id TEXT PRIMARY KEY,
                    integration_id TEXT NOT NULL,
                    action_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    evaluated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    rule_id TEXT DEFAULT '',
                    rule_title TEXT NOT NULL,
                    actual_value TEXT DEFAULT '',
                    verdict TEXT CHECK(verdict IN ('PASS', 'FAIL', 'PARTIAL')) NOT NULL,
                    reasoning TEXT NOT NULL,
                    suggested_fix TEXT,
                    FOREIGN KEY (rule_id) REFERENCES rules(rule_id)
                );
                """
            )
            cursor.execute("PRAGMA table_info(rule_evaluations);")
            columns = {row["name"] for row in cursor.fetchall()}
            if "actual_value" not in columns:
                cursor.execute("ALTER TABLE rule_evaluations ADD COLUMN actual_value TEXT DEFAULT '';")
            if "rule_id" not in columns:
                cursor.execute("ALTER TABLE rule_evaluations ADD COLUMN rule_id TEXT DEFAULT '';")
            if "rule_number" in columns:
                cursor.execute("ALTER TABLE rule_evaluations RENAME TO rule_evaluations_old;")
                cursor.execute(
                    """
                    CREATE TABLE rule_evaluations (
                        evaluation_id TEXT PRIMARY KEY,
                        integration_id TEXT NOT NULL,
                        action_id TEXT NOT NULL,
                        run_id TEXT NOT NULL,
                        evaluated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        rule_id TEXT DEFAULT '',
                        rule_title TEXT NOT NULL,
                        actual_value TEXT DEFAULT '',
                        verdict TEXT CHECK(verdict IN ('PASS', 'FAIL', 'PARTIAL')) NOT NULL,
                        reasoning TEXT NOT NULL,
                        suggested_fix TEXT,
                        FOREIGN KEY (rule_id) REFERENCES rules(rule_id)
                    );
                    """
                )
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO rule_evaluations (
                        evaluation_id, integration_id, action_id, run_id,
                        evaluated_at, rule_id, rule_title, actual_value, verdict,
                        reasoning, suggested_fix
                    )
                    SELECT
                        evaluation_id, integration_id, action_id, run_id,
                        evaluated_at, '', rule_title, actual_value, verdict,
                        reasoning, suggested_fix
                    FROM rule_evaluations_old;
                    """
                )
                cursor.execute("DROP TABLE rule_evaluations_old;")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_eval_lookup ON rule_evaluations(integration_id, action_id, run_id);"
            )
            conn.commit()

    def save_rules(self, rules: list[EvaluationRule]) -> None:
        """Persist evaluation rules to the rules table.

        Args:
            rules: List of EvaluationRule objects to persist.

        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for rule in rules:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO rules (
                        rule_id, title, target_field, criteria
                    ) VALUES (?, ?, ?, ?);
                    """,
                    (rule.rule_id, rule.title, rule.target_field, rule.criteria),
                )
            conn.commit()

    def get_rules(self) -> list[EvaluationRule]:
        """Fetch all rules from database.

        Returns:
            List of EvaluationRule objects.

        """
        with self._get_connection() as conn:

            cursor = conn.cursor()
            cursor.execute("SELECT rule_id, title, target_field, criteria FROM rules ORDER BY rule_id ASC;")
            rows = cursor.fetchall()
            return [
                EvaluationRule(
                    rule_id=row["rule_id"],
                    title=row["title"],
                    target_field=row["target_field"],
                    criteria=row["criteria"],
                )
                for row in rows
            ]

    def save_evaluation(self, result: RuleEvaluationResult) -> None:
        """Persist a single rule evaluation record to SQLite database.

        Args:
            result: RuleEvaluationResult object to persist.

        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO rule_evaluations (
                    evaluation_id, integration_id, action_id, run_id,
                    evaluated_at, rule_id, rule_title, actual_value, verdict,
                    reasoning, suggested_fix
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    result.evaluation_id,
                    result.integration_id,
                    result.action_id,
                    result.run_id,
                    result.evaluated_at,
                    result.rule_id,
                    result.rule_title,
                    result.actual_value,
                    result.verdict.value,
                    result.reasoning,
                    result.suggested_fix,
                ),
            )
            conn.commit()

    def get_evaluations(
        self,
        integration_id: str | None = None,
        action_id: str | None = None,
        run_id: str | None = None,
    ) -> list[RuleEvaluationResult]:
        """Fetch evaluations by integration_id, action_id, or run_id filters.

        Args:
            integration_id: Optional integration ID filter.
            action_id: Optional action ID filter.
            run_id: Optional run ID filter.

        Returns:
            List of RuleEvaluationResult records.

        """
        query = "SELECT * FROM rule_evaluations WHERE 1=1"
        params: list[str] = []

        if integration_id:
            query += " AND integration_id = ?"
            params.append(integration_id)
        if action_id:
            query += " AND action_id = ?"
            params.append(action_id)
        if run_id:
            query += " AND run_id = ?"
            params.append(run_id)

        query += " ORDER BY rule_title ASC"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [
                RuleEvaluationResult(
                    evaluation_id=row["evaluation_id"],
                    integration_id=row["integration_id"],
                    action_id=row["action_id"],
                    run_id=row["run_id"],
                    evaluated_at=str(row["evaluated_at"]),
                    rule_id=str(dict(row).get("rule_id", "")),
                    rule_title=row["rule_title"],
                    actual_value=str(dict(row).get("actual_value", "")),
                    verdict=VerdictEnum(row["verdict"]),
                    reasoning=row["reasoning"],
                    suggested_fix=row["suggested_fix"],
                )
                for row in rows
            ]
