"""add_indexes_paper_trades_decision_log_prospects

Revision ID: 7eaf882f9721
Revises: ca52cc9a3084
Create Date: 2026-06-02 17:40:13.664988

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7eaf882f9721'
down_revision: Union[str, Sequence[str], None] = 'ca52cc9a3084'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_paper_trades_created_at
        ON paper_trades (created_at)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_decision_log_timestamp_desc
        ON decision_log (timestamp DESC)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_prospects_score_desc
        ON prospects (score DESC)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_paper_trades_created_at")
    op.execute("DROP INDEX IF EXISTS idx_decision_log_timestamp_desc")
    op.execute("DROP INDEX IF EXISTS idx_prospects_score_desc")
