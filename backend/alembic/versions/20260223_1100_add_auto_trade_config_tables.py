"""Add auto-trade configuration tables.

Creates strategy_templates, auto_trade_configs, and pending_auto_trades tables
for the Recommendation Auto-Trade Pipeline feature.

Revision ID: auto_trade_config_001
Revises: screener_auto_trade_001
Create Date: 2026-02-23 11:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ENUM as PgEnum

# revision identifiers, used by Alembic.
revision = "auto_trade_config_001"
down_revision = "screener_auto_trade_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create confirmation_mode enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE confirmationmode AS ENUM ('auto', 'notify', 'disabled');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create screener_source_type enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE screenersourcetype AS ENUM ('preset', 'custom');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create pending_trade_status enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE pendingtradestatus AS ENUM ('pending', 'approved', 'rejected', 'expired', 'executed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create strategyproducttype enum if it doesn't exist
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE strategyproducttype AS ENUM ('DELIVERY', 'INTRADAY', 'MTF');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Use existing PostgreSQL enum types directly (avoid create_type issues)
    positionsizingmethod_enum = PgEnum(
        'FIXED_QUANTITY', 'FIXED_AMOUNT', 'PERCENT_OF_PORTFOLIO', 'RISK_BASED', 'VOLATILITY_ADJUSTED',
        name='positionsizingmethod', create_type=False
    )
    strategyproducttype_enum = PgEnum(
        'DELIVERY', 'INTRADAY', 'MTF',
        name='strategyproducttype', create_type=False
    )

    # Create strategy_templates table
    op.create_table(
        "strategy_templates",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, index=True),
        sa.Column("user_id", UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("strategy_type", sa.String(50), nullable=False),
        sa.Column("strategy_params", sa.JSON, nullable=True),
        sa.Column("position_sizing_method", positionsizingmethod_enum, nullable=False, server_default="PERCENT_OF_PORTFOLIO"),
        sa.Column("position_size_value", sa.Numeric(10, 2), nullable=False, server_default="5.00"),
        sa.Column("max_position_value", sa.Numeric(18, 2), nullable=True),
        sa.Column("stop_loss_percent", sa.Numeric(5, 2), nullable=False, server_default="2.00"),
        sa.Column("take_profit_percent", sa.Numeric(5, 2), nullable=False, server_default="4.00"),
        sa.Column("max_daily_loss", sa.Numeric(18, 2), nullable=False, server_default="5000.00"),
        sa.Column("max_consecutive_losses", sa.Integer, nullable=False, server_default="3"),
        sa.Column("product_type", strategyproducttype_enum, nullable=False, server_default="DELIVERY"),
        sa.Column("trading_start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trading_end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_strategy_templates_user", "strategy_templates", ["user_id"])

    # Use existing PostgreSQL enum types directly for auto_trade_configs
    confirmationmode_enum = PgEnum('auto', 'notify', 'disabled', name='confirmationmode', create_type=False)
    screenersourcetype_enum = PgEnum('preset', 'custom', name='screenersourcetype', create_type=False)
    pendingtradestatus_enum = PgEnum('pending', 'approved', 'rejected', 'expired', 'executed', name='pendingtradestatus', create_type=False)

    # Create auto_trade_configs table
    op.create_table(
        "auto_trade_configs",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, index=True),
        sa.Column("user_id", UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("confirmation_mode", confirmationmode_enum, nullable=False, server_default="notify"),
        sa.Column("strategy_template_id", UUID(as_uuid=False), sa.ForeignKey("strategy_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("max_positions_per_day", sa.Integer, nullable=False, server_default="3"),
        sa.Column("max_capital_per_day", sa.Numeric(18, 2), nullable=False, server_default="50000.00"),
        sa.Column("expiry_hours", sa.Integer, nullable=False, server_default="4"),
        sa.Column("weight_technical", sa.Integer, nullable=False, server_default="40"),
        sa.Column("weight_fundamental", sa.Integer, nullable=False, server_default="40"),
        sa.Column("weight_sentiment", sa.Integer, nullable=False, server_default="20"),
        sa.Column("min_confidence", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("screener_source_type", screenersourcetype_enum, nullable=False, server_default="preset"),
        sa.Column("preset_category", sa.String(50), nullable=True),
        sa.Column("saved_screener_id", UUID(as_uuid=False), sa.ForeignKey("custom_screeners.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_auto_trade_configs_user", "auto_trade_configs", ["user_id"])
    op.create_index("ix_auto_trade_configs_category", "auto_trade_configs", ["user_id", "category"], unique=True)

    # Create pending_auto_trades table
    op.create_table(
        "pending_auto_trades",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, index=True),
        sa.Column("user_id", UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("auto_trade_config_id", UUID(as_uuid=False), sa.ForeignKey("auto_trade_configs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("recommendation_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbols", sa.JSON, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("scores", sa.JSON, nullable=True),
        sa.Column("recommended_strategy_type", sa.String(50), nullable=False),
        sa.Column("suggested_params", sa.JSON, nullable=True),
        sa.Column("status", pendingtradestatus_enum, nullable=False, server_default="pending"),
        sa.Column("created_strategy_id", UUID(as_uuid=False), sa.ForeignKey("user_strategies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actioned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_pending_auto_trades_user", "pending_auto_trades", ["user_id"])
    op.create_index("ix_pending_auto_trades_status", "pending_auto_trades", ["status"])
    op.create_index("ix_pending_auto_trades_expires", "pending_auto_trades", ["expires_at"])


def downgrade() -> None:
    op.drop_table("pending_auto_trades")
    op.drop_table("auto_trade_configs")
    op.drop_table("strategy_templates")

    op.execute("DROP TYPE IF EXISTS pendingtradestatus;")
    op.execute("DROP TYPE IF EXISTS screenersourcetype;")
    op.execute("DROP TYPE IF EXISTS confirmationmode;")

