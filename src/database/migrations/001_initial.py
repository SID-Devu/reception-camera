from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'persons',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('embedding', sa.LargeBinary, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())
    )

def downgrade():
    op.drop_table('persons')