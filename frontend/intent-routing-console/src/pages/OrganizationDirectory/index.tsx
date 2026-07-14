import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ProTable, type ActionType, type ProColumns } from '@ant-design/pro-components';
import { useModel } from '@umijs/max';
import {
  Alert,
  Button,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd';
import { AdminShell } from '@/components/AdminShell';
import { AdminSessionRequired } from '@/components/AdminSessionRequired';
import { ConfirmActionButton } from '@/components/ConfirmActionButton';
import {
  createDepartment,
  createOrganizationUser,
  deleteDepartment,
  deleteOrganizationUser,
  listDepartments,
  listOrganizationUsers,
  patchDepartment,
  patchOrganizationUser,
} from '@/services/adminServices';
import {
  toDepartmentCreateRequest,
  toOrganizationUserCreateRequest,
  type DepartmentFormValues,
  type OrganizationUserFormValues,
} from './directoryForms';

type DepartmentFormMode = 'create' | 'edit';
type UserFormMode = 'create' | 'edit';

type DepartmentOption = {
  label: string;
  value: string;
};

const useYnValueEnum = {
  Y: { text: 'Y' },
  N: { text: 'N' },
} as const;

const formatUseYn = (useYn: API.UseYn) => (
  <Tag color={useYn === 'Y' ? 'green' : 'default'}>{useYn}</Tag>
);

const toDepartmentOption = (department: API.Department): DepartmentOption => ({
  label: `${department.dept_number} / ${department.name} / ${department.use_yn}`,
  value: department.id,
});

export default function OrganizationDirectoryPage() {
  const { session } = useModel('adminSession');
  const [departmentForm] = Form.useForm<DepartmentFormValues>();
  const [userForm] = Form.useForm<OrganizationUserFormValues>();
  const [departmentModalOpen, setDepartmentModalOpen] = useState(false);
  const [userModalOpen, setUserModalOpen] = useState(false);
  const [departmentFormMode, setDepartmentFormMode] = useState<DepartmentFormMode>('create');
  const [userFormMode, setUserFormMode] = useState<UserFormMode>('create');
  const [editingDepartment, setEditingDepartment] = useState<API.Department>();
  const [editingUser, setEditingUser] = useState<API.OrganizationUser>();
  const [departmentSaving, setDepartmentSaving] = useState(false);
  const [userSaving, setUserSaving] = useState(false);
  const [departmentOptions, setDepartmentOptions] = useState<DepartmentOption[]>([]);
  const [loadingDepartmentOptions, setLoadingDepartmentOptions] = useState(false);
  const departmentActionRef = useRef<ActionType>();
  const userActionRef = useRef<ActionType>();
  const ready = Boolean(session.authenticated && session.user);
  const canManage = session.globalRoles.includes('system_admin');

  const loadDepartmentOptions = useCallback(async () => {
    setLoadingDepartmentOptions(true);
    try {
      const rows = await listDepartments({ limit: 100 });
      setDepartmentOptions(rows.map(toDepartmentOption));
    } catch {
      message.error('Failed to load department options.');
    } finally {
      setLoadingDepartmentOptions(false);
    }
  }, []);

  useEffect(() => {
    if (!ready) {
      setDepartmentOptions([]);
      return;
    }
    void loadDepartmentOptions();
  }, [loadDepartmentOptions, ready]);

  const reloadDepartmentViews = useCallback(() => {
    departmentActionRef.current?.reload();
    userActionRef.current?.reload();
    void loadDepartmentOptions();
  }, [loadDepartmentOptions]);

  const reloadUserTable = useCallback(() => {
    userActionRef.current?.reload();
  }, []);

  const closeDepartmentModal = () => {
    setDepartmentModalOpen(false);
    setEditingDepartment(undefined);
    departmentForm.resetFields();
  };

  const closeUserModal = () => {
    setUserModalOpen(false);
    setEditingUser(undefined);
    userForm.resetFields();
  };

  const openCreateDepartmentModal = () => {
    setDepartmentFormMode('create');
    setEditingDepartment(undefined);
    departmentForm.resetFields();
    setDepartmentModalOpen(true);
  };

  const openEditDepartmentModal = (department: API.Department) => {
    setDepartmentFormMode('edit');
    setEditingDepartment(department);
    departmentForm.resetFields();
    departmentForm.setFieldsValue({
      dept_number: department.dept_number,
      name: department.name,
    });
    setDepartmentModalOpen(true);
  };

  const openCreateUserModal = () => {
    setUserFormMode('create');
    setEditingUser(undefined);
    userForm.resetFields();
    setUserModalOpen(true);
  };

  const openEditUserModal = (user: API.OrganizationUser) => {
    setUserFormMode('edit');
    setEditingUser(user);
    userForm.resetFields();
    userForm.setFieldsValue({
      user_number: user.user_number,
      name: user.name,
      department_id: user.department_id,
    });
    setUserModalOpen(true);
  };

  const handleDepartmentSubmit = async (values: DepartmentFormValues) => {
    setDepartmentSaving(true);
    try {
      const payload = toDepartmentCreateRequest(values);
      if (departmentFormMode === 'create') {
        await createDepartment(payload);
        message.success('Department created.');
      } else if (editingDepartment) {
        await patchDepartment(editingDepartment.id, payload);
        message.success('Department updated.');
      }
      closeDepartmentModal();
      reloadDepartmentViews();
    } finally {
      setDepartmentSaving(false);
    }
  };

  const handleUserSubmit = async (values: OrganizationUserFormValues) => {
    setUserSaving(true);
    try {
      const payload = toOrganizationUserCreateRequest(values);
      if (userFormMode === 'create') {
        await createOrganizationUser(payload);
        message.success('User created.');
      } else if (editingUser) {
        await patchOrganizationUser(editingUser.id, payload);
        message.success('User updated.');
      }
      closeUserModal();
      reloadUserTable();
    } finally {
      setUserSaving(false);
    }
  };

  const departmentFilterOptions = useMemo(
    () => departmentOptions.map((option) => ({ label: option.label, value: option.value })),
    [departmentOptions],
  );

  const departmentColumns: ProColumns<API.Department>[] = [
    {
      title: 'Search',
      dataIndex: 'keyword',
      hideInTable: true,
    },
    {
      title: 'Dept #',
      dataIndex: 'dept_number',
      search: false,
      render: (_, row) => <Typography.Text code>{row.dept_number}</Typography.Text>,
    },
    {
      title: 'Name',
      dataIndex: 'name',
      search: false,
    },
    {
      title: 'Use',
      dataIndex: 'use_yn',
      valueType: 'select',
      valueEnum: useYnValueEnum,
      render: (_, row) => formatUseYn(row.use_yn),
    },
    {
      title: 'Updated',
      dataIndex: 'updated_at',
      valueType: 'dateTime',
      search: false,
    },
    {
      title: '',
      valueType: 'option',
      width: 152,
      render: (_, row) => {
        if (!canManage) return [];
        return [
          <Button
            key="edit"
            type="link"
            size="small"
            onClick={() => openEditDepartmentModal(row)}
          >
            편집
          </Button>,
          row.use_yn === 'Y' ? (
            <ConfirmActionButton
              key="deactivate"
              danger
              type="link"
              size="small"
              title="Deactivate department?"
              okText="Deactivate"
              content={`${row.dept_number} ${row.name} 부서를 비활성화합니다.`}
              onConfirm={() => deleteDepartment(row.id).then(() => undefined)}
              onSuccess={reloadDepartmentViews}
            >
              비활성화
            </ConfirmActionButton>
          ) : null,
        ].filter(Boolean);
      },
    },
  ];

  const userColumns: ProColumns<API.OrganizationUser>[] = [
    {
      title: 'Search',
      dataIndex: 'keyword',
      hideInTable: true,
    },
    {
      title: 'Department',
      dataIndex: 'department_id',
      hideInTable: true,
      valueType: 'select',
      fieldProps: {
        options: departmentFilterOptions,
        showSearch: true,
        optionFilterProp: 'label',
      },
    },
    {
      title: 'User #',
      dataIndex: 'user_number',
      search: false,
      render: (_, row) => <Typography.Text code>{row.user_number}</Typography.Text>,
    },
    {
      title: 'Name',
      dataIndex: 'name',
      search: false,
    },
    {
      title: 'Department',
      dataIndex: ['department', 'name'],
      search: false,
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <span>{row.department.name}</span>
          <span className="muted-small">{row.department.dept_number}</span>
        </Space>
      ),
    },
    {
      title: 'Use',
      dataIndex: 'use_yn',
      valueType: 'select',
      valueEnum: useYnValueEnum,
      render: (_, row) => formatUseYn(row.use_yn),
    },
    {
      title: 'Updated',
      dataIndex: 'updated_at',
      valueType: 'dateTime',
      search: false,
    },
    {
      title: '',
      valueType: 'option',
      width: 152,
      render: (_, row) => {
        if (!canManage) return [];
        return [
          <Button key="edit" type="link" size="small" onClick={() => openEditUserModal(row)}>
            편집
          </Button>,
          row.use_yn === 'Y' ? (
            <ConfirmActionButton
              key="deactivate"
              danger
              type="link"
              size="small"
              title="Deactivate user?"
              okText="Deactivate"
              content={`${row.user_number} ${row.name} 사용자를 비활성화합니다.`}
              onConfirm={() => deleteOrganizationUser(row.id).then(() => undefined)}
              onSuccess={reloadUserTable}
            >
              비활성화
            </ConfirmActionButton>
          ) : null,
        ].filter(Boolean);
      },
    },
  ];

  return (
    <AdminShell title="Users & Departments">
      {ready ? (
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          {!canManage ? (
            <Alert
              type="info"
              showIcon
              message="Read-only access"
              description="Department and user changes require system_admin."
            />
          ) : null}
          <Tabs
            destroyInactiveTabPane
            items={[
              {
                key: 'departments',
                label: 'Departments',
                children: (
                  <ProTable<API.Department>
                    rowKey="id"
                    actionRef={departmentActionRef}
                    columns={departmentColumns}
                    request={async (params) => {
                      const rows = await listDepartments({
                        query: typeof params.keyword === 'string' ? params.keyword : undefined,
                        use_yn: params.use_yn as API.UseYn | undefined,
                        limit: 100,
                      });
                      return { data: rows, total: rows.length, success: true };
                    }}
                    pagination={false}
                    search={{ labelWidth: 88 }}
                    options={{ density: true, fullScreen: false, reload: true, setting: true }}
                    toolBarRender={() =>
                      canManage
                        ? [
                            <Button
                              key="create-department"
                              type="primary"
                              onClick={openCreateDepartmentModal}
                            >
                              Department 추가
                            </Button>,
                          ]
                        : []
                    }
                  />
                ),
              },
              {
                key: 'users',
                label: 'Users',
                children: (
                  <ProTable<API.OrganizationUser>
                    rowKey="id"
                    actionRef={userActionRef}
                    columns={userColumns}
                    request={async (params) => {
                      const rows = await listOrganizationUsers({
                        query: typeof params.keyword === 'string' ? params.keyword : undefined,
                        department_id:
                          typeof params.department_id === 'string'
                            ? params.department_id
                            : undefined,
                        use_yn: params.use_yn as API.UseYn | undefined,
                        limit: 100,
                      });
                      return { data: rows, total: rows.length, success: true };
                    }}
                    pagination={false}
                    search={{ labelWidth: 88 }}
                    options={{ density: true, fullScreen: false, reload: true, setting: true }}
                    toolBarRender={() =>
                      canManage
                        ? [
                            <Button
                              key="create-user"
                              type="primary"
                              onClick={openCreateUserModal}
                            >
                              User 추가
                            </Button>,
                          ]
                        : []
                    }
                  />
                ),
              },
            ]}
          />
          <Modal
            destroyOnClose
            open={departmentModalOpen}
            title={departmentFormMode === 'create' ? 'Create Department' : 'Edit Department'}
            okText={departmentFormMode === 'create' ? 'Create' : 'Save'}
            cancelText="취소"
            confirmLoading={departmentSaving}
            onCancel={closeDepartmentModal}
            onOk={() => departmentForm.submit()}
          >
            <Form<DepartmentFormValues>
              form={departmentForm}
              layout="vertical"
              requiredMark={false}
              onFinish={handleDepartmentSubmit}
            >
              <Form.Item
                name="dept_number"
                label="Dept number"
                rules={[
                  { required: true, whitespace: true, message: 'Dept number is required.' },
                ]}
              >
                <Input placeholder="0969" />
              </Form.Item>
              <Form.Item
                name="name"
                label="Name"
                rules={[{ required: true, whitespace: true, message: 'Name is required.' }]}
              >
                <Input placeholder="IT지원부" />
              </Form.Item>
            </Form>
          </Modal>
          <Modal
            destroyOnClose
            open={userModalOpen}
            title={userFormMode === 'create' ? 'Create User' : 'Edit User'}
            okText={userFormMode === 'create' ? 'Create' : 'Save'}
            cancelText="취소"
            confirmLoading={userSaving}
            onCancel={closeUserModal}
            onOk={() => userForm.submit()}
          >
            <Form<OrganizationUserFormValues>
              form={userForm}
              layout="vertical"
              requiredMark={false}
              onFinish={handleUserSubmit}
            >
              <Form.Item
                name="user_number"
                label="User number"
                rules={[
                  { required: true, whitespace: true, message: 'User number is required.' },
                ]}
              >
                <Input placeholder="21P0031" />
              </Form.Item>
              <Form.Item
                name="name"
                label="Name"
                rules={[{ required: true, whitespace: true, message: 'Name is required.' }]}
              >
                <Input placeholder="홍길동" />
              </Form.Item>
              <Form.Item
                name="department_id"
                label="Department"
                rules={[{ required: true, message: 'Department is required.' }]}
              >
                <Select
                  loading={loadingDepartmentOptions}
                  options={departmentFilterOptions}
                  placeholder="부서를 선택하세요."
                  showSearch
                  optionFilterProp="label"
                />
              </Form.Item>
            </Form>
          </Modal>
        </Space>
      ) : (
        <AdminSessionRequired />
      )}
    </AdminShell>
  );
}
