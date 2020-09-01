"""course description added and address renamed to place_details

Revision ID: c8502fca9dbd
Revises: bba441000591
Create Date: 2020-09-01 19:02:15.434307

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c8502fca9dbd'
down_revision = 'bba441000591'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('course', schema=None) as batch_op:
        batch_op.add_column(sa.Column('course_description', sa.String(length=255), nullable=True))

    with op.batch_alter_table('location', schema=None) as batch_op:
        batch_op.add_column(sa.Column('place_details', sa.String(length=64), nullable=True))
        batch_op.drop_column('address')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('location', schema=None) as batch_op:
        batch_op.add_column(sa.Column('address', sa.VARCHAR(length=64), nullable=True))
        batch_op.drop_column('place_details')

    with op.batch_alter_table('course', schema=None) as batch_op:
        batch_op.drop_column('course_description')

    # ### end Alembic commands ###
