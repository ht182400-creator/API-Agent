"""创建用户操作日志表

Revision ID: 20260423_user_operation_log
Create Date: 2026-04-23 10:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260423_user_operation_log'
down_revision = None  # 请根据实际情况设置上一个迁移的 revision
branch_labels = None
depends_on = None


def upgrade():
    # 创建 user_operation_logs 表
    op.create_table(
        'user_operation_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('username', sa.String(100), nullable=True, index=True),
        sa.Column('email', sa.String(255), nullable=True, index=True),
        sa.Column('session_id', sa.String(100), nullable=True, index=True),
        sa.Column('action', sa.String(100), nullable=False, index=True),
        sa.Column('action_name', sa.String(200), nullable=True),
        sa.Column('category', sa.String(50), nullable=False, index=True),
        sa.Column('page', sa.String(255), nullable=True),
        sa.Column('page_name', sa.String(200), nullable=True),
        sa.Column('referrer', sa.String(500), nullable=True),
        sa.Column('url_params', postgresql.JSONB, server_default='{}'),
        sa.Column('method', sa.String(10), nullable=True),
        sa.Column('endpoint', sa.String(500), nullable=True),
        sa.Column('request_data', postgresql.JSONB, server_default='{}'),
        sa.Column('response_status', sa.String(20), nullable=True),
        sa.Column('old_values', postgresql.JSONB, server_default='{}'),
        sa.Column('new_values', postgresql.JSONB, server_default='{}'),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('device_type', sa.String(50), nullable=True),
        sa.Column('browser', sa.String(100), nullable=True),
        sa.Column('os', sa.String(100), nullable=True),
        sa.Column('success', sa.Boolean, server_default='true'),
        sa.Column('error_code', sa.String(50), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()'), index=True),
        sa.Column('duration_ms', sa.String(20), nullable=True),
    )
    
    # 创建复合索引
    op.create_index('idx_user_op_user_time', 'user_operation_logs', ['user_id', 'created_at'])
    op.create_index('idx_user_op_session_time', 'user_operation_logs', ['session_id', 'created_at'])
    op.create_index('idx_user_op_category_time', 'user_operation_logs', ['category', 'created_at'])
    op.create_index('idx_user_op_action_time', 'user_operation_logs', ['action', 'created_at'])


def downgrade():
    op.drop_table('user_operation_logs')
