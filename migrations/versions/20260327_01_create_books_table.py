"""create books table

Revision ID: 20260327_01
Revises:
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260327_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uid", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=False),
        sa.Column("isbn", sa.String(length=32), nullable=True),
        sa.Column("topic", sa.String(length=128), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cover_image_url", sa.String(length=512), nullable=True),
        sa.Column("published_year", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(),
                  server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("isbn"),
        sa.UniqueConstraint("uid"),
    )
    op.create_index("ix_books_author", "books", ["author"], unique=False)
    op.create_index("ix_books_title", "books", ["title"], unique=False)


def downgrade():
    op.drop_index("ix_books_title", table_name="books")
    op.drop_index("ix_books_author", table_name="books")
    op.drop_table("books")
