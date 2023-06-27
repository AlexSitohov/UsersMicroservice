"""add_columns_email_confirmed_and_verification_token_to_users_table

Revision ID: 81cb174a93c4
Revises: e41e60c5d79a
Create Date: 2023-06-26 17:38:49.978652

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '81cb174a93c4'
down_revision = 'e41e60c5d79a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('email_confirmed', sa.BOOLEAN(), nullable=True))
    op.add_column('users', sa.Column('verification_token', sa.String(), nullable=True))
    op.alter_column('users', 'email',
               existing_type=sa.VARCHAR(length=30),
               nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('users', 'email',
               existing_type=sa.VARCHAR(length=30),
               nullable=True)
    op.drop_column('users', 'verification_token')
    op.drop_column('users', 'email_confirmed')
    # ### end Alembic commands ###
