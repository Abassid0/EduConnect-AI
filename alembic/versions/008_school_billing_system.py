"""Phase 8: School billing system — fee types, invoices, invoice items,
and Payment model extensions for multi-type billing.

Revision ID: 008
Revises: 007
"""

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None

DEFAULT_FEE_TYPES = [
    {
        "name": "School Fees",
        "slug": "school_fees",
        "description": "Tuition and school fees per term",
        "category": "tuition",
        "is_recurring": True,
    },
    {
        "name": "Uniform",
        "slug": "uniform",
        "description": "School uniform and dress code items",
        "category": "material",
        "is_recurring": False,
    },
    {
        "name": "Textbooks",
        "slug": "textbooks",
        "description": "Required textbooks and workbooks",
        "category": "material",
        "is_recurring": False,
    },
    {
        "name": "PTA Contribution",
        "slug": "pta_contribution",
        "description": "Parent-Teacher Association dues",
        "category": "contribution",
        "is_recurring": True,
    },
    {
        "name": "School Utilities",
        "slug": "school_utilities",
        "description": "Lab fees, computer fees, sports fees, and other utilities",
        "category": "service",
        "is_recurring": True,
    },
    {
        "name": "Transport / Bus",
        "slug": "transport",
        "description": "School bus and transport service fees",
        "category": "service",
        "is_recurring": True,
    },
    {
        "name": "Exam Fees",
        "slug": "exam_fees",
        "description": "Internal and external examination fees",
        "category": "service",
        "is_recurring": False,
    },
    {
        "name": "Excursion",
        "slug": "excursion",
        "description": "Field trips and excursion fees",
        "category": "service",
        "is_recurring": False,
    },
]


def upgrade() -> None:
    # 1. Create fee_types table
    op.create_table(
        "fee_types",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(50), unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("default_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "currency",
            sa.String(3),
            server_default=sa.text("'NGN'"),
            nullable=False,
        ),
        sa.Column(
            "is_recurring",
            sa.Boolean,
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean,
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_fee_types_slug", "fee_types", ["slug"], unique=True)
    op.create_index("idx_fee_types_category", "fee_types", ["category"])

    # 2. Create invoices table
    op.create_table(
        "invoices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("invoice_number", sa.String(30), unique=True, nullable=False),
        sa.Column(
            "parent_id",
            UUID(as_uuid=True),
            sa.ForeignKey("parents.id"),
            nullable=False,
        ),
        sa.Column(
            "student_id",
            UUID(as_uuid=True),
            sa.ForeignKey("students.id"),
            nullable=True,
        ),
        sa.Column("academic_term", sa.String(50), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "amount_paid",
            sa.Numeric(12, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "currency",
            sa.String(3),
            server_default=sa.text("'NGN'"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(20),
            server_default=sa.text("'unpaid'"),
            nullable=False,
        ),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_invoices_number", "invoices", ["invoice_number"], unique=True
    )
    op.create_index("idx_invoices_parent", "invoices", ["parent_id"])
    op.create_index("idx_invoices_student", "invoices", ["student_id"])
    op.create_index("idx_invoices_status", "invoices", ["status"])

    # 3. Create invoice_items table
    op.create_table(
        "invoice_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "invoice_id",
            UUID(as_uuid=True),
            sa.ForeignKey("invoices.id"),
            nullable=False,
        ),
        sa.Column(
            "fee_type_id",
            UUID(as_uuid=True),
            sa.ForeignKey("fee_types.id"),
            nullable=False,
        ),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column(
            "quantity", sa.Integer, server_default=sa.text("1"), nullable=False
        ),
        sa.Column("unit_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_invoice_items_invoice", "invoice_items", ["invoice_id"])
    op.create_index("idx_invoice_items_fee_type", "invoice_items", ["fee_type_id"])

    # 4. Extend payments table — new columns
    op.add_column(
        "payments",
        sa.Column(
            "invoice_id",
            UUID(as_uuid=True),
            sa.ForeignKey("invoices.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "payments",
        sa.Column(
            "fee_type_id",
            UUID(as_uuid=True),
            sa.ForeignKey("fee_types.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "payments",
        sa.Column(
            "payment_type",
            sa.String(30),
            server_default=sa.text("'enrollment'"),
            nullable=False,
        ),
    )
    op.add_column(
        "payments",
        sa.Column("description", sa.String(300), nullable=True),
    )
    op.create_index("idx_payments_invoice", "payments", ["invoice_id"])
    op.create_index("idx_payments_type", "payments", ["payment_type"])

    # 5. Make enrollment_id and programme_id nullable on payments
    op.alter_column("payments", "enrollment_id", existing_type=UUID(as_uuid=True), nullable=True)
    op.alter_column("payments", "programme_id", existing_type=UUID(as_uuid=True), nullable=True)

    # 6. Backfill existing payments as enrollment type
    op.execute("UPDATE payments SET payment_type = 'enrollment' WHERE payment_type IS NULL")

    # 7. Seed default fee types
    for ft in DEFAULT_FEE_TYPES:
        op.execute(
            sa.text(
                "INSERT INTO fee_types (id, name, slug, description, category, is_recurring, created_at) "
                "VALUES (gen_random_uuid(), :name, :slug, :description, :category, :is_recurring, NOW())"
            ).bindparams(
                name=ft["name"],
                slug=ft["slug"],
                description=ft["description"],
                category=ft["category"],
                is_recurring=ft["is_recurring"],
            )
        )


def downgrade() -> None:
    op.drop_index("idx_payments_type", table_name="payments")
    op.drop_index("idx_payments_invoice", table_name="payments")
    op.drop_column("payments", "description")
    op.drop_column("payments", "payment_type")
    op.drop_column("payments", "fee_type_id")
    op.drop_column("payments", "invoice_id")

    op.alter_column("payments", "enrollment_id", existing_type=UUID(as_uuid=True), nullable=False)
    op.alter_column("payments", "programme_id", existing_type=UUID(as_uuid=True), nullable=False)

    op.drop_index("idx_invoice_items_fee_type", table_name="invoice_items")
    op.drop_index("idx_invoice_items_invoice", table_name="invoice_items")
    op.drop_table("invoice_items")

    op.drop_index("idx_invoices_status", table_name="invoices")
    op.drop_index("idx_invoices_student", table_name="invoices")
    op.drop_index("idx_invoices_parent", table_name="invoices")
    op.drop_index("idx_invoices_number", table_name="invoices")
    op.drop_table("invoices")

    op.drop_index("idx_fee_types_category", table_name="fee_types")
    op.drop_index("idx_fee_types_slug", table_name="fee_types")
    op.drop_table("fee_types")
