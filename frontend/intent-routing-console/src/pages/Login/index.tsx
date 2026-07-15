import { useEffect, useMemo, useState } from 'react';
import { history, useLocation, useModel } from '@umijs/max';
import { Button, Card, ConfigProvider, Form, Input, Typography, theme as antdTheme } from 'antd';
import koKR from 'antd/locale/ko_KR';

type LoginFormValues = {
  email: string;
  password: string;
};

const loginTheme = {
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
  return error?.message ?? 'Sign-in failed.';
};

export default function LoginPage() {
  const location = useLocation();
  const { login, restoring, session } = useModel('adminSession');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();

  const redirectPath = useMemo(() => {
    const params = new URLSearchParams(location.search);
    const redirect = params.get('redirect');
    return redirect?.startsWith('/') && !redirect.startsWith('//') ? redirect : '/dashboard';
  }, [location.search]);
  const submitting = loading || restoring;

  useEffect(() => {
    if (!restoring && session.authenticated) {
      history.replace(redirectPath);
    }
  }, [redirectPath, restoring, session.authenticated]);

  const submit = async (values: LoginFormValues) => {
    setLoading(true);
    setError(undefined);
    try {
      await login(values.email.trim(), values.password);
      history.replace(redirectPath);
    } catch (err: any) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <ConfigProvider locale={koKR} theme={loginTheme}>
      <main className="login-page">
        <Card className="login-panel">
          <Typography.Title level={2}>Intent Routing Admin</Typography.Title>
          <Typography.Paragraph type="secondary">
            Sign in with your admin account to continue.
          </Typography.Paragraph>
          <Typography.Paragraph type="secondary">
            Need a new admin account?{' '}
            <Button
              type="link"
              onClick={() => history.push('/admin-access-request')}
              style={{ paddingInline: 0 }}
            >
              Submit an access request
            </Button>
          </Typography.Paragraph>
          <Form<LoginFormValues>
            layout="vertical"
            requiredMark={false}
            onFinish={submit}
            validateTrigger="onBlur"
            disabled={submitting}
          >
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
              validateStatus={error ? 'error' : undefined}
              help={error}
              rules={[{ required: true, message: 'Password is required.' }]}
            >
              <Input.Password autoComplete="current-password" />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={submitting} block>
              Sign in
            </Button>
          </Form>
        </Card>
      </main>
    </ConfigProvider>
  );
}
