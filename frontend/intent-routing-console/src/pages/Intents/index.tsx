import { useState } from 'react';
import { useModel } from '@umijs/max';
import { Descriptions, Drawer, Space, Tag } from 'antd';
import { AdminShell } from '@/components/AdminShell';
import { AdminSessionRequired } from '@/components/AdminSessionRequired';
import { IntentCatalogTable } from '@/components/IntentCatalogTable';
import { isAdminSessionReady } from '@/models/adminSession';

const statusColor: Record<string, string> = {
  active: 'green',
  draft: 'orange',
  deprecated: 'default',
};

export default function IntentsPage() {
  const { session } = useModel('adminSession');
  const [selected, setSelected] = useState<API.Intent>();
  const ready = isAdminSessionReady(session);

  return (
    <AdminShell title="Intent Catalog">
      {ready ? (
        <IntentCatalogTable serviceId={session.serviceId} onSelectIntent={setSelected} />
      ) : (
        <AdminSessionRequired />
      )}
      <Drawer
        title={selected?.intent_id}
        width={620}
        open={Boolean(selected)}
        onClose={() => setSelected(undefined)}
      >
        {selected ? (
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label="Display name">{selected.display_name}</Descriptions.Item>
              <Descriptions.Item label="Domain">{selected.domain}</Descriptions.Item>
              <Descriptions.Item label="Description">{selected.description}</Descriptions.Item>
              <Descriptions.Item label="Route">
                <Tag>{selected.route_key}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag color={statusColor[selected.status] ?? 'default'}>{selected.status}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Created">{selected.created_at ?? 'none'}</Descriptions.Item>
              <Descriptions.Item label="Updated">{selected.updated_at ?? 'none'}</Descriptions.Item>
            </Descriptions>
            <Space wrap>
              {selected.include_keywords.map((keyword) => (
                <Tag color="green" key={`include:${keyword}`}>
                  + {keyword}
                </Tag>
              ))}
              {selected.exclude_keywords.map((keyword) => (
                <Tag color="default" key={`exclude:${keyword}`}>
                  - {keyword}
                </Tag>
              ))}
            </Space>
          </Space>
        ) : null}
      </Drawer>
    </AdminShell>
  );
}
