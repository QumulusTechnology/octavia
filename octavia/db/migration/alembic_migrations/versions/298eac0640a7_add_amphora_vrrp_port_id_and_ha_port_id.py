#    Copyright 2015 Rackspace
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

"""Add vrrp_port_id and ha_port_id to amphora

Revision ID: 298eac0640a7
Revises: 4fe8240425b4
Create Date: 2015-07-20 15:25:37.044098

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '298eac0640a7'
down_revision = '4fe8240425b4'


def upgrade():
    op.add_column('amphora',
                  sa.Column('vrrp_port_id', sa.String(36), nullable=True))
    op.add_column('amphora',
                  sa.Column('ha_port_id', sa.String(36), nullable=True))
