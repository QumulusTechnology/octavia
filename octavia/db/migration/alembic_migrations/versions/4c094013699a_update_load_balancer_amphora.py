#    Copyright 2014 Rackspace
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

'''update load balancer amphora relationship

Revision ID: 4c094013699a
Revises: 35dee79d5865
Create Date: 2014-09-15 14:42:44.875448

'''

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '4c094013699a'
down_revision = '35dee79d5865'


def upgrade():
    op.add_column(
        'amphora',
        sa.Column('load_balancer_id', sa.String(36),
                  sa.ForeignKey('load_balancer.id',
                                name='fk_amphora_load_balancer_id'),
                  nullable=True)
    )
    op.drop_table('load_balancer_amphora')
    op.drop_constraint(
        'fk_container_provisioning_status_name', 'amphora',
        type_='foreignkey'
    )
    op.create_foreign_key(
        'fk_amphora_provisioning_status_name', 'amphora',
        'provisioning_status', ['status'], ['name']
    )
