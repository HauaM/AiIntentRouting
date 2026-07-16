import { useEffect, useMemo, useState } from 'react';
import { history } from '@umijs/max';
import {
  Alert,
  Button,
  Card,
  ConfigProvider,
  Form,
  Input,
  Select,
  Space,
  Tag,
  Typography,
  theme as antdTheme,
} from 'antd';
import koKR from 'antd/locale/ko_KR';
import { listPublicDepartments, submitAdminAccessRequest } from '@/services/authServices';
import {
  toAdminAccessRequestCreateRequest,
  type AdminAccessRequestFormValues,
} from './requestForm';

const requestTheme = {
  algorithm: antdTheme.defaultAlgorithm,
  token: {
    colorPrimary: '#1D5A96',
    colorTextBase: '#1C2733',
    colorBgLayout: '#F4F6F8',
    borderRadius: 6,
    fontFamily: "Pretendard, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  },
};

const errorMessage = (error: any) => {
  const payload = error?.response?.data ?? error?.data;
  const detail = payload?.detail;
  if (typeof detail === 'string') return detail;
  if (detail?.error?.message) return detail.error.message;
  if (payload?.error?.message) return payload.error.message;
  return error?.message ?? '신청을 제출하지 못했습니다.';
};

export default function AdminAccessRequestPage() {
  const [loading, setLoading] = useState(false);
  const [departmentsLoading, setDepartmentsLoading] = useState(false);
  const [error, setError] = useState<string>();
  const [departmentError, setDepartmentError] = useState<string>();
  const [departments, setDepartments] = useState<API.PublicDepartment[]>([]);
  const [submittedRequest, setSubmittedRequest] = useState<API.AdminAccessRequest | null>(null);

  useEffect(() => {
    let mounted = true;
    setDepartmentsLoading(true);
    setDepartmentError(undefined);
    listPublicDepartments()
      .then((rows) => {
        if (!mounted) return;
        setDepartments(rows);
      })
      .catch(() => {
        if (!mounted) return;
        setDepartmentError('부서 목록을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.');
      })
      .finally(() => {
        if (!mounted) return;
        setDepartmentsLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const departmentOptions = useMemo(
    () =>
      departments.map((department) => ({
        value: department.id,
        label: `${department.dept_number} - ${department.name}`,
      })),
    [departments],
  );

  const submit = async (values: AdminAccessRequestFormValues) => {
    setLoading(true);
    setError(undefined);
    try {
      const response = await submitAdminAccessRequest(
        toAdminAccessRequestCreateRequest(values),
      );
      setSubmittedRequest(response);
    } catch (err: any) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <ConfigProvider locale={koKR} theme={requestTheme}>
      <main className="login-page">
        <Card className="login-panel">
          {submittedRequest ? (
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              <div>
                <Typography.Title level={2}>신청이 접수되었습니다</Typography.Title>
                <Typography.Paragraph type="secondary">
                  Admin Console 접근 신청이 기록되었고 system_admin 검토를 기다리고 있습니다.
                </Typography.Paragraph>
              </div>
              <div>
                <Typography.Text type="secondary">신청 상태</Typography.Text>
                <div style={{ marginTop: 8 }}>
                  <Tag color="processing">{submittedRequest.status}</Tag>
                </div>
              </div>
              <div>
                <Typography.Text type="secondary">신청 ID</Typography.Text>
                <div style={{ marginTop: 8 }}>
                  <Typography.Text code>{submittedRequest.request_id}</Typography.Text>
                </div>
              </div>
              <Button type="primary" onClick={() => history.push('/login')} block>
                로그인으로 돌아가기
              </Button>
            </Space>
          ) : (
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              <div>
                <Typography.Title level={2}>Admin Console 접근 신청</Typography.Title>
                <Typography.Paragraph type="secondary">
                  조직 사용자 정보와 접근 사유를 입력하면 system_admin이 승인 여부를 검토합니다.
                </Typography.Paragraph>
              </div>
              <Form<AdminAccessRequestFormValues>
                layout="vertical"
                requiredMark={false}
                onFinish={submit}
                validateTrigger="onBlur"
                disabled={loading}
              >
                {error ? (
                  <Alert
                    type="error"
                    showIcon
                    message={error}
                    style={{ marginBottom: 16 }}
                  />
                ) : null}
                {departmentError ? (
                  <Alert
                    type="warning"
                    showIcon
                    message={departmentError}
                    style={{ marginBottom: 16 }}
                  />
                ) : null}
                <Form.Item
                  label="사번"
                  name="user_number"
                  rules={[{ required: true, message: '사번을 입력해 주세요.' }]}
                >
                  <Input autoComplete="off" />
                </Form.Item>
                <Form.Item
                  label="이름"
                  name="name"
                  rules={[{ required: true, message: '이름을 입력해 주세요.' }]}
                >
                  <Input autoComplete="name" />
                </Form.Item>
                <Form.Item
                  label="부서"
                  name="department_id"
                  rules={[{ required: true, message: '부서를 선택해 주세요.' }]}
                >
                  <Select
                    showSearch
                    loading={departmentsLoading}
                    placeholder="부서 선택"
                    optionFilterProp="label"
                    options={departmentOptions}
                    notFoundContent={departmentsLoading ? '불러오는 중' : '선택 가능한 부서가 없습니다'}
                  />
                </Form.Item>
                <Form.Item
                  label="이메일"
                  name="email"
                  rules={[
                    { required: true, message: '이메일을 입력해 주세요.' },
                    { type: 'email', message: '올바른 이메일 주소를 입력해 주세요.' },
                  ]}
                >
                  <Input autoComplete="email" inputMode="email" />
                </Form.Item>
                <Form.Item
                  label="비밀번호"
                  name="password"
                  rules={[
                    { required: true, message: '비밀번호를 입력해 주세요.' },
                    { min: 8, message: '비밀번호는 8자 이상이어야 합니다.' },
                  ]}
                >
                  <Input.Password autoComplete="new-password" />
                </Form.Item>
                <Form.Item
                  label="비밀번호 확인"
                  name="password_confirm"
                  dependencies={['password']}
                  rules={[
                    { required: true, message: '비밀번호를 다시 입력해 주세요.' },
                    ({ getFieldValue }) => ({
                      validator(_, value) {
                        if (!value || getFieldValue('password') === value) {
                          return Promise.resolve();
                        }
                        return Promise.reject(new Error('비밀번호가 일치하지 않습니다.'));
                      },
                    }),
                  ]}
                >
                  <Input.Password autoComplete="new-password" />
                </Form.Item>
                <Form.Item
                  label="접근 사유"
                  name="access_reason"
                  rules={[
                    { required: true, message: '접근 사유를 입력해 주세요.' },
                    {
                      validator: (_, value) =>
                        !value || value.trim().length >= 10
                          ? Promise.resolve()
                          : Promise.reject(
                              new Error('접근 사유는 10자 이상 입력해 주세요.'),
                            ),
                    },
                  ]}
                >
                  <Input.TextArea rows={4} showCount maxLength={500} />
                </Form.Item>
                <Space direction="vertical" size={12} style={{ width: '100%' }}>
                  <Button type="primary" htmlType="submit" loading={loading} block>
                    신청 제출
                  </Button>
                  <Button onClick={() => history.push('/login')} block>
                    로그인으로 돌아가기
                  </Button>
                </Space>
              </Form>
            </Space>
          )}
        </Card>
      </main>
    </ConfigProvider>
  );
}
