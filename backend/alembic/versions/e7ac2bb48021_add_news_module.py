"""add news module

Revision ID: e7ac2bb48021
Revises: 0004
Create Date: 2026-08-09

仅创建新闻聚合相关的两张表，不含 autogenerate 产生的无关 drift。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e7ac2bb48021'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建新闻聚合表与采集日志表。"""
    op.create_table(
        'business_news',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='雪花算法主键 ID'),
        sa.Column('title', sa.String(length=500), nullable=False, comment='新闻标题'),
        sa.Column('content', sa.Text(), nullable=True, comment='新闻正文'),
        sa.Column('summary', sa.String(length=1000), nullable=True, comment='新闻摘要'),
        sa.Column('url', sa.String(length=1000), nullable=False, comment='新闻原文链接'),
        sa.Column('source', sa.String(length=50), nullable=False, comment='新闻源 key'),
        sa.Column('source_name', sa.String(length=100), nullable=False, comment='新闻源中文名'),
        sa.Column('author', sa.String(length=100), nullable=True, comment='作者'),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True, comment='发布时间'),
        sa.Column('raw_time', sa.String(length=50), nullable=True, comment='原始时间字符串'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间，为空则未删除'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url', name='uk_news_url'),
        comment='新闻聚合表',
    )
    op.create_index(op.f('ix_business_news_id'), 'business_news', ['id'], unique=True)
    op.create_index(op.f('ix_business_news_published_at'), 'business_news', ['published_at'], unique=False)
    op.create_index(op.f('ix_business_news_source'), 'business_news', ['source'], unique=False)

    op.create_table(
        'business_news_sync_log',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='雪花算法主键 ID'),
        sa.Column('source', sa.String(length=50), nullable=False, comment='新闻源 key'),
        sa.Column('status', sa.Boolean(), nullable=False, comment='采集状态：True-成功，False-失败'),
        sa.Column('fetched_count', sa.Integer(), nullable=False, comment='抓取条数'),
        sa.Column('saved_count', sa.Integer(), nullable=False, comment='入库条数'),
        sa.Column('error_msg', sa.Text(), nullable=True, comment='错误信息'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True, comment='开始时间'),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True, comment='结束时间'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间，为空则未删除'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        comment='新闻采集日志表',
    )
    op.create_index(op.f('ix_business_news_sync_log_id'), 'business_news_sync_log', ['id'], unique=True)
    op.create_index(op.f('ix_business_news_sync_log_source'), 'business_news_sync_log', ['source'], unique=False)


def downgrade() -> None:
    """回滚：删除两张表。"""
    op.drop_index(op.f('ix_business_news_sync_log_source'), table_name='business_news_sync_log')
    op.drop_index(op.f('ix_business_news_sync_log_id'), table_name='business_news_sync_log')
    op.drop_table('business_news_sync_log')
    op.drop_index(op.f('ix_business_news_source'), table_name='business_news')
    op.drop_index(op.f('ix_business_news_published_at'), table_name='business_news')
    op.drop_index(op.f('ix_business_news_id'), table_name='business_news')
    op.drop_table('business_news')
