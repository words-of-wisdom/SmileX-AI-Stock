from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision = '0008'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sys_ai_model',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='雪花算法主键 ID'),
        sa.Column('name', sa.String(length=100), nullable=False, comment='模型配置名称'),
        sa.Column('provider', sa.Enum('openai', 'anthropic', 'deepseek', 'qwen', 'zhipu', 'custom', name='aiproviderenum'),
                  nullable=False, comment='AI 模型提供商'),
        sa.Column('base_url', sa.String(length=500), nullable=False, comment='API 基础地址'),
        sa.Column('api_key_encrypted', sa.String(length=1000), nullable=False, comment='API Key（Fernet 加密）'),
        sa.Column('model_name', sa.String(length=200), nullable=False, comment='模型标识'),
        sa.Column('temperature', sa.Float(), nullable=True, comment='温度参数'),
        sa.Column('max_tokens', sa.Integer(), nullable=True, comment='最大 token 数'),
        sa.Column('is_default', sa.Boolean(), nullable=False, comment='是否为默认模型'),
        sa.Column('status', sa.Boolean(), nullable=False, comment='状态：True-启用，False-禁用'),
        sa.Column('remark', sa.String(length=500), nullable=True, comment='备注'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间，为空则未删除'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uk_sys_ai_model_name'),
        comment='AI 模型配置表',
    )
    op.create_index(op.f('ix_sys_ai_model_id'), 'sys_ai_model', ['id'], unique=True)
    op.create_index(op.f('ix_sys_ai_model_name'), 'sys_ai_model', ['name'], unique=False)

    op.create_table(
        'sys_ai_model_binding',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='雪花算法主键 ID'),
        sa.Column('function_code',
                  sa.Enum('stock_picking', 'sentiment_analysis', 'news_summary', 'chat_qa', 'trend_prediction',
                          name='aifunctionenum'),
                  nullable=False, comment='功能场景编码'),
        sa.Column('model_id', sa.BigInteger(), nullable=False, comment='绑定的 AI 模型 ID'),
        sa.Column('status', sa.Boolean(), nullable=False, comment='状态：True-启用，False-禁用'),
        sa.Column('remark', sa.String(length=500), nullable=True, comment='备注'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间，为空则未删除'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.ForeignKeyConstraint(['model_id'], ['sys_ai_model.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('function_code', name='uk_sys_ai_model_binding_function'),
        comment='AI 场景模型绑定表',
    )
    op.create_index(op.f('ix_sys_ai_model_binding_id'), 'sys_ai_model_binding', ['id'], unique=True)
    op.create_index(op.f('ix_sys_ai_model_binding_function_code'), 'sys_ai_model_binding', ['function_code'],
                    unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_sys_ai_model_binding_function_code'), table_name='sys_ai_model_binding')
    op.drop_index(op.f('ix_sys_ai_model_binding_id'), table_name='sys_ai_model_binding')
    op.drop_table('sys_ai_model_binding')
    op.drop_index(op.f('ix_sys_ai_model_name'), table_name='sys_ai_model')
    op.drop_index(op.f('ix_sys_ai_model_id'), table_name='sys_ai_model')
    op.drop_table('sys_ai_model')
    sa.Enum(name='aifunctionenum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='aiproviderenum').drop(op.get_bind(), checkfirst=True)
