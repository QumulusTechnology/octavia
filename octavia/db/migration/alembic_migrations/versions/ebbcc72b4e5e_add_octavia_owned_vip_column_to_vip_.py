#    Copyright 2018 Rackspace, US Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""Add Octavia owned VIP column to VIP table

Revision ID: ebbcc72b4e5e
Revises: 0f242cf02c74
Create Date: 2018-07-09 17:25:30.137527

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ebbcc72b4e5e'
down_revision = '0f242cf02c74'


def upgrade():
    op.add_column(
        'vip',
        sa.Column('octavia_owned', sa.Boolean(), nullable=True)
    )
