import { useEffect, useRef, useState } from 'react';
import { MoreOutlined } from '@ant-design/icons';
import { ProTable, type ActionType, type ProColumns } from '@ant-design/pro-components';
import { useModel } from '@umijs/max';
import {
  Button,
  Descriptions,
  Drawer,
  Dropdown,
  Empty,
  Form,
  Input,
  Modal,
  Space,
  Tag,
  Tooltip,
  Typography,
  message,
} from 'antd';
import { AdminShell } from '@/components/AdminShell';
import { AdminSessionRequired } from '@/components/AdminSessionRequired';
import { canEditCatalog, isAdminSessionReady } from '@/models/adminSession';
import {
  createCatalogVersion,
  deactivateCatalogVersion,
  fetchCatalogVersionDiff,
  listCatalogVersions,
  loadCatalogVersionToDraft,
} from '@/services/adminServices';

type CatalogVersionFormValues = {
  description: string;
};

const CATALOG_VERSION_LIST_LIMIT = 100;

const statusColor: Record<API.CatalogVersionStatus, string> = {
  active: 'success',
  inactive: 'default',
};

const diffSections = [
  { key: 'added_intents', title: '추가된 Intent' },
  { key: 'removed_intents', title: '삭제된 Intent' },
  { key: 'changed_intents', title: '변경된 Intent' },
  { key: 'added_examples', title: '추가된 Example' },
  { key: 'removed_examples', title: '삭제된 Example' },
  { key: 'changed_examples', title: '변경된 Example' },
] as const;

const describeDiffItem = (item: unknown) => {
  if (!item || typeof item !== 'object') return String(item ?? '-');
  const record = item as Record<string, unknown>;
  const after = record.after as Record<string, unknown> | undefined;
  const before = record.before as Record<string, unknown> | undefined;
  const target = after ?? before ?? record;
  return String(
    target.intent_id ??
      target.example_id ??
      target.display_name ??
      target.text_masked ??
      JSON.stringify(target),
  );
};

const getOperationErrorMessage = (error: unknown) =>
  error instanceof Error ? error.message : '요청 처리 중 오류가 발생했습니다.';

export default function CatalogVersionsPage() {
  const { session } = useModel('adminSession');
  const actionRef = useRef<ActionType>();
  const [form] = Form.useForm<CatalogVersionFormValues>();
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [catalogRows, setCatalogRows] = useState<API.CatalogVersionListItem[]>([]);
  const [diffOpen, setDiffOpen] = useState(false);
  const [diffLoading, setDiffLoading] = useState(false);
  const [diffTarget, setDiffTarget] = useState<API.CatalogVersionListItem>();
  const [diffBaseline, setDiffBaseline] = useState<API.CatalogVersionListItem>();
  const [diff, setDiff] = useState<API.CatalogVersionDiff>();
  const ready = isAdminSessionReady(session);
  const canManage = ready && canEditCatalog(session);

  const reload = () => actionRef.current?.reload();

  useEffect(() => {
    setDiff(undefined);
    setDiffTarget(undefined);
    setDiffBaseline(undefined);
    setDiffOpen(false);
    setCreateOpen(false);
    form.resetFields();
    actionRef.current?.reloadAndRest?.();
  }, [form, session.serviceId]);

  const handleCreate = async () => {
    const values = await form.validateFields();
    setCreating(true);
    try {
      await createCatalogVersion(session.serviceId, {
        description: values.description.trim(),
      });
      message.success('Catalog 버전이 등록되었습니다.');
      setCreateOpen(false);
      form.resetFields();
      reload();
    } catch (error) {
      message.error(getOperationErrorMessage(error));
      throw error;
    } finally {
      setCreating(false);
    }
  };

  const openDiff = async (row: API.CatalogVersionListItem) => {
    const baseline = catalogRows
      .filter(
        (version) =>
          version.intent_catalog_version !== row.intent_catalog_version &&
          new Date(version.created_at).getTime() < new Date(row.created_at).getTime(),
      )
      .sort(
        (left, right) =>
          new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
      )[0];
    setDiffTarget(row);
    setDiffBaseline(baseline);
    setDiffOpen(true);
    setDiff(undefined);
    setDiffLoading(true);
    try {
      const result = await fetchCatalogVersionDiff(
        session.serviceId,
        row.intent_catalog_version,
        { compare_to: baseline?.intent_catalog_version },
      );
      setDiff(result);
    } catch (error) {
      message.error(getOperationErrorMessage(error));
    } finally {
      setDiffLoading(false);
    }
  };

  const confirmLoadToDraft = (row: API.CatalogVersionListItem) => {
    Modal.confirm({
      title: `${row.display_version}을 draft로 불러올까요?`,
      content: '현재 Intent Catalog 초안이 이 버전의 snapshot으로 덮어써질 수 있습니다.',
      okText: 'draft로 불러오기',
      cancelText: '취소',
      onOk: async () => {
        try {
          await loadCatalogVersionToDraft(session.serviceId, row.intent_catalog_version);
          message.success('Catalog 버전을 draft로 불러왔습니다.');
        } catch (error) {
          message.error(getOperationErrorMessage(error));
          throw error;
        }
      },
    });
  };

  const confirmDeactivate = (row: API.CatalogVersionListItem) => {
    Modal.confirm({
      title: `${row.display_version}을 비활성화할까요?`,
      content: '비활성화하면 해당 버전의 embedding이 해제되어 테스트/런타임 후보로 사용할 수 없습니다.',
      okText: '비활성화',
      cancelText: '취소',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await deactivateCatalogVersion(session.serviceId, row.intent_catalog_version);
          message.success('Catalog 버전이 비활성화되었습니다.');
          reload();
        } catch (error) {
          message.error(getOperationErrorMessage(error));
          throw error;
        }
      },
    });
  };

  const columns: ProColumns<API.CatalogVersionListItem>[] = [
    {
      title: '버전',
      dataIndex: 'display_version',
      width: 104,
      render: (_, row) => (
        <Tooltip title={row.intent_catalog_version}>
          <Typography.Text strong>{row.display_version}</Typography.Text>
        </Tooltip>
      ),
    },
    {
      title: '설명',
      dataIndex: 'description',
      ellipsis: true,
      width: 260,
    },
    {
      title: '상태',
      dataIndex: 'status',
      width: 96,
      render: (_, row) => (
        <Tag color={statusColor[row.status]}>{row.status}</Tag>
      ),
    },
    {
      title: 'Release',
      dataIndex: 'released',
      width: 120,
      render: (_, row) =>
        row.released || row.release_count > 0 ? (
          <Tag color="processing">released {row.release_count}</Tag>
        ) : (
          <Tag>unreleased</Tag>
        ),
    },
    {
      title: 'Intent',
      dataIndex: 'intent_count',
      width: 96,
    },
    {
      title: 'Example',
      dataIndex: 'example_count',
      width: 104,
    },
    {
      title: 'Embedding',
      dataIndex: 'embedding_count',
      width: 112,
    },
    {
      title: '생성 일시',
      dataIndex: 'created_at',
      valueType: 'dateTime',
      width: 168,
    },
    {
      title: '작업',
      valueType: 'option',
      width: 220,
      fixed: 'right',
      render: (_, row) =>
        canManage
          ? [
              <Space
                key="actions"
                size={8}
                align="center"
                className="table-action-cell"
                style={{ whiteSpace: 'nowrap' }}
              >
                <Button type="link" size="small" onClick={() => openDiff(row)}>
                  비교
                </Button>
                <Button type="link" size="small" onClick={() => confirmLoadToDraft(row)}>
                  draft로 불러오기
                </Button>
                <Dropdown
                  menu={{
                    items: [
                      {
                        key: 'deactivate',
                        label: '비활성화',
                        disabled: row.released || row.release_count > 0,
                      },
                    ],
                    onClick: ({ key }) => {
                      if (key === 'deactivate') confirmDeactivate(row);
                    },
                  }}
                >
                  <Button type="link" size="small" aria-label="Catalog 버전 작업 더보기">
                    <MoreOutlined />
                  </Button>
                </Dropdown>
              </Space>,
            ]
          : [],
    },
  ];

  return (
    <AdminShell title="Catalog 버전관리">
      {ready ? (
        <>
          <ProTable<API.CatalogVersionListItem>
            actionRef={actionRef}
            rowKey="intent_catalog_version"
            cardProps={{ title: 'Catalog 버전 목록' }}
            columns={columns}
            search={false}
            options={{ reload: true, density: false, setting: false }}
            pagination={false}
            scroll={{ x: 1280 }}
            locale={{
              emptyText: (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description="등록된 Catalog 버전이 없습니다."
                />
              ),
            }}
            toolBarRender={() =>
              canManage
                ? [
                    <Button key="create" type="primary" onClick={() => setCreateOpen(true)}>
                      Catalog 버전 등록
                    </Button>,
                  ]
                : []
            }
            request={async () => {
              const rows = await listCatalogVersions(session.serviceId, {
                limit: CATALOG_VERSION_LIST_LIMIT,
              });
              setCatalogRows(rows);
              return { data: rows, success: true, total: rows.length };
            }}
          />

          <Modal
            title="Catalog 버전 등록"
            open={createOpen}
            centered
            width={640}
            okText="등록"
            cancelText="취소"
            confirmLoading={creating}
            onOk={handleCreate}
            onCancel={() => setCreateOpen(false)}
          >
            <Form form={form} layout="vertical">
              <Form.Item
                name="description"
                label="버전 설명"
                rules={[
                  { required: true, message: '버전 설명을 입력해주세요.' },
                  { min: 10, message: '버전 설명은 최소 10글자 이상이어야 합니다.' },
                  {
                    validator: async (_, value?: string) => {
                      if (!value || value.trim().length >= 10) return;
                      throw new Error('공백을 제외하고 최소 10글자 이상 입력해주세요.');
                    },
                  },
                ]}
              >
                <Input.TextArea
                  rows={4}
                  showCount
                  maxLength={500}
                  placeholder="이 버전에 포함된 Intent/Example 변경 사유를 입력하세요."
                />
              </Form.Item>
            </Form>
          </Modal>

          <Drawer
            title={diffTarget ? `${diffTarget.display_version} 비교` : 'Catalog 버전 비교'}
            open={diffOpen}
            width={720}
            onClose={() => setDiffOpen(false)}
          >
            {diffTarget ? (
              <Descriptions size="small" column={1} bordered style={{ marginBottom: 16 }}>
                <Descriptions.Item label="대상 버전">
                  <Typography.Text code>{diffTarget.intent_catalog_version}</Typography.Text>
                </Descriptions.Item>
                <Descriptions.Item label="비교 기준">
                  {diffBaseline ? (
                    <Space size={6}>
                      <Typography.Text strong>{diffBaseline.display_version}</Typography.Text>
                      <Typography.Text code>{diffBaseline.intent_catalog_version}</Typography.Text>
                    </Space>
                  ) : diff?.from_version ? (
                    <Typography.Text code>{diff.from_version}</Typography.Text>
                  ) : (
                    '이전 버전 없음'
                  )}
                </Descriptions.Item>
              </Descriptions>
            ) : null}
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              {diffSections.map((section) => {
                const values = ((diff?.[section.key] ?? []) as unknown[]);
                return (
                  <div key={section.key}>
                    <Space size={8} style={{ marginBottom: 8 }}>
                      <Typography.Text strong>{section.title}</Typography.Text>
                      <Tag>{values.length}</Tag>
                    </Space>
                    {diffLoading ? (
                      <Typography.Text type="secondary">불러오는 중...</Typography.Text>
                    ) : values.length ? (
                      <Space direction="vertical" size={4} style={{ width: '100%' }}>
                        {values.slice(0, 20).map((item, index) => (
                          <Typography.Text key={`${section.key}-${index}`} code>
                            {describeDiffItem(item)}
                          </Typography.Text>
                        ))}
                      </Space>
                    ) : (
                      <Typography.Text type="secondary">변경 없음</Typography.Text>
                    )}
                  </div>
                );
              })}
            </Space>
          </Drawer>
        </>
      ) : (
        <AdminSessionRequired />
      )}
    </AdminShell>
  );
}
