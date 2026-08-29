"""add indexes to FK and timestamp columns

Revision ID: 039e8649beb5
Revises: 21fe8cc61865
Create Date: 2026-06-01 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "039e8649beb5"
down_revision: Union[str, None] = "21fe8cc61865"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        # ai_sessions
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ai_sessions_diagnostic_id ON ai_sessions (diagnostic_id)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ai_sessions_verification_id ON ai_sessions (verification_id)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ai_sessions_profile_id ON ai_sessions (profile_id)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ai_sessions_created_at ON ai_sessions (created_at)")

        # ai_suggestions
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ai_suggestions_session_id ON ai_suggestions (session_id)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ai_suggestions_created_at ON ai_suggestions (created_at)")

        # ai_audit_log
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ai_audit_log_session_id ON ai_audit_log (session_id)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ai_audit_log_created_at ON ai_audit_log (created_at)")

        # script_generation_jobs
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_script_generation_jobs_profile_id ON script_generation_jobs (profile_id)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_script_generation_jobs_created_at ON script_generation_jobs (created_at)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_script_generation_jobs_completed_at ON script_generation_jobs (completed_at)")

        # generated_scripts
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_generated_scripts_job_id ON generated_scripts (job_id)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_generated_scripts_created_at ON generated_scripts (created_at)")

        # verification_results
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_verification_results_report_id ON verification_results (report_id)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_verification_results_profile_id ON verification_results (profile_id)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_verification_results_created_at ON verification_results (created_at)")

        # verification_checks
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_verification_checks_result_id ON verification_checks (result_id)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_verification_checks_created_at ON verification_checks (created_at)")

        # uninstall_feedbacks
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_uninstall_feedbacks_created_at ON uninstall_feedbacks (created_at)")

        # profile_packages
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_profile_packages_profile_id ON profile_packages (profile_id)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_profile_packages_created_at ON profile_packages (created_at)")

    

def downgrade() -> None:
    
    # profile_packages
    op.drop_index("ix_profile_packages_created_at", table_name="profile_packages")
    op.drop_index("ix_profile_packages_profile_id", table_name="profile_packages")

    # uninstall_feedbacks
    op.drop_index("ix_uninstall_feedbacks_created_at", table_name="uninstall_feedbacks")

    # verification_checks
    op.drop_index("ix_verification_checks_created_at", table_name="verification_checks")
    op.drop_index("ix_verification_checks_result_id", table_name="verification_checks")

    # verification_results
    op.drop_index("ix_verification_results_created_at", table_name="verification_results")
    op.drop_index("ix_verification_results_profile_id", table_name="verification_results")
    op.drop_index("ix_verification_results_report_id", table_name="verification_results")

    # generated_scripts
    op.drop_index("ix_generated_scripts_created_at", table_name="generated_scripts")
    op.drop_index("ix_generated_scripts_job_id", table_name="generated_scripts")

    # script_generation_jobs
    op.drop_index("ix_script_generation_jobs_completed_at", table_name="script_generation_jobs")
    op.drop_index("ix_script_generation_jobs_created_at", table_name="script_generation_jobs")
    op.drop_index("ix_script_generation_jobs_profile_id", table_name="script_generation_jobs")

    # ai_audit_log
    op.drop_index("ix_ai_audit_log_created_at", table_name="ai_audit_log")
    op.drop_index("ix_ai_audit_log_session_id", table_name="ai_audit_log")

    # ai_suggestions
    op.drop_index("ix_ai_suggestions_created_at", table_name="ai_suggestions")
    op.drop_index("ix_ai_suggestions_session_id", table_name="ai_suggestions")

    # ai_sessions
    op.drop_index("ix_ai_sessions_created_at", table_name="ai_sessions")
    op.drop_index("ix_ai_sessions_profile_id", table_name="ai_sessions")
    op.drop_index("ix_ai_sessions_verification_id", table_name="ai_sessions")
    op.drop_index("ix_ai_sessions_diagnostic_id", table_name="ai_sessions")