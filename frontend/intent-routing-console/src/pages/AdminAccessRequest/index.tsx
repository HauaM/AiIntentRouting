import { useState } from 'react';
import { history } from '@umijs/max';
import {
  Alert,
  Button,
  Card,
  ConfigProvider,
  Form,
  Input,
  Space,
  Tag,
  Typography,
  theme as antdTheme,
} from 'antd';
import koKR from 'antd/locale/ko_KR';
import { submitAdminAccessRequest } from '@/services/authServices';
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
  return error?.message ?? 'Request submission failed.';
};

export default function AdminAccessRequestPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();
  const [submittedRequest, setSubmittedRequest] = useState<API.AdminAccessRequest | null>(null);

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
                <Typography.Title level={2}>Request submitted</Typography.Title>
                <Typography.Paragraph type="secondary">
                  Your Admin Console access request has been recorded and is waiting for review.
                </Typography.Paragraph>
              </div>
              <div>
                <Typography.Text type="secondary">Request status</Typography.Text>
                <div style={{ marginTop: 8 }}>
                  <Tag color="processing">{submittedRequest.status}</Tag>
                </div>
              </div>
              <div>
                <Typography.Text type="secondary">Request ID</Typography.Text>
                <div style={{ marginTop: 8 }}>
                  <Typography.Text code>{submittedRequest.request_id}</Typography.Text>
                </div>
              </div>
              <Button type="primary" onClick={() => history.push('/login')} block>
                Back to sign in
              </Button>
            </Space>
          ) : (
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              <div>
                <Typography.Title level={2}>Admin access request</Typography.Title>
                <Typography.Paragraph type="secondary">
                  Submit your organization profile and reason for Admin Console access.
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
                <Form.Item
                  label="User number"
                  name="user_number"
                  rules={[{ required: true, message: 'User number is required.' }]}
                >
                  <Input autoComplete="off" />
                </Form.Item>
                <Form.Item
                  label="Name"
                  name="name"
                  rules={[{ required: true, message: 'Name is required.' }]}
                >
                  <Input autoComplete="name" />
                </Form.Item>
                <Form.Item
                  label="Department ID"
                  name="department_id"
                  extra="Use the department ID assigned by your organization administrator."
                  rules={[{ required: true, message: 'Department ID is required.' }]}
                >
                  <Input autoComplete="off" />
                </Form.Item>
                <Form.Item
                  label="Email"
                  name="email"
                  rules={[
                    { required: true, message: 'Email is required.' },
                    { type: 'email', message: 'Enter a valid email address.' },
                  ]}
                >
                  <Input autoComplete="email" inputMode="email" />
                </Form.Item>
                <Form.Item
                  label="Password"
                  name="password"
                  rules={[
                    { required: true, message: 'Password is required.' },
                    { min: 8, message: 'Password must be at least 8 characters.' },
                  ]}
                >
                  <Input.Password autoComplete="new-password" />
                </Form.Item>
                <Form.Item
                  label="Access reason"
                  name="access_reason"
                  rules={[{ required: true, message: 'Access reason is required.' }]}
                >
                  <Input.TextArea rows={4} showCount maxLength={500} />
                </Form.Item>
                <Space direction="vertical" size={12} style={{ width: '100%' }}>
                  <Button type="primary" htmlType="submit" loading={loading} block>
                    Submit request
                  </Button>
                  <Button onClick={() => history.push('/login')} block>
                    Back to sign in
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
