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
    # ai_sessions
    op.create_index("ix_ai_sessions_diagnostic_id", "ai_sessions", ["diagnostic_id"])
    op.create_index("ix_ai_sessions_verification_id", "ai_sessions", ["verification_id"])
    op.create_index("ix_ai_sessions_profile_id", "ai_sessions", ["profile_id"])
    op.create_index("ix_ai_sessions_created_at", "ai_sessions", ["created_at"])

    # ai_suggestions
    op.create_index("ix_ai_suggestions_session_id", "ai_suggestions", ["session_id"])
    op.create_index("ix_ai_suggestions_created_at", "ai_suggestions", ["created_at"])

    # ai_audit_log
    op.create_index("ix_ai_audit_log_session_id", "ai_audit_log", ["session_id"])
    op.create_index("ix_ai_audit_log_created_at", "ai_audit_log", ["created_at"])

    # script_generation_jobs
    op.create_index("ix_script_generation_jobs_profile_id", "script_generation_jobs", ["profile_id"])
    op.create_index("ix_script_generation_jobs_created_at", "script_generation_jobs", ["created_at"])
    op.create_index("ix_script_generation_jobs_completed_at", "script_generation_jobs", ["completed_at"])

    # generated_scripts
    op.create_index("ix_generated_scripts_job_id", "generated_scripts", ["job_id"])
    op.create_index("ix_generated_scripts_created_at", "generated_scripts", ["created_at"])

    # verification_results
    op.create_index("ix_verification_results_report_id", "verification_results", ["report_id"])
    op.create_index("ix_verification_results_profile_id", "verification_results", ["profile_id"])
    op.create_index("ix_verification_results_created_at", "verification_results", ["created_at"])

    # verification_checks
    op.create_index("ix_verification_checks_result_id", "verification_checks", ["result_id"])
    op.create_index("ix_verification_checks_created_at", "verification_checks", ["created_at"])

    # uninstall_feedbacks
    op.create_index("ix_uninstall_feedbacks_created_at", "uninstall_feedbacks", ["created_at"])

    # profile_packages
    op.create_index("ix_profile_packages_profile_id", "profile_packages", ["profile_id"])
    op.create_index("ix_profile_packages_created_at", "profile_packages", ["created_at"])

    

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