import type { PropsWithChildren } from 'react';
import { useEffect } from 'react';
import { history, useLocation, useModel } from '@umijs/max';
import { PageContainer, ProLayout } from '@ant-design/pro-components';
import { Alert, ConfigProvider, Skeleton, theme as antdTheme } from 'antd';
import koKR from 'antd/locale/ko_KR';
import {
  AuditOutlined,
  DashboardOutlined,
  ExperimentOutlined,
  FileSearchOutlined,
  KeyOutlined,
  ProfileOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import { ServiceScopeBar } from './ServiceScopeBar';

const adminUiTheme = {
  algorithm: antdTheme.defaultAlgorithm,
  token: {
    colorPrimary: '#1D5A96',
    colorSuccess: '#2F8F5B',
    colorWarning: '#D4920B',
    colorError: '#C0392B',
    colorTextBase: '#1C2733',
    colorText: '#1C2733',
    colorTextSecondary: '#64748B',
    colorBgContainer: '#FFFFFF',
    colorBgElevated: '#FFFFFF',
    colorBgLayout: '#F4F6F8',
    colorBorderSecondary: '#E6EAEF',
    borderRadius: 6,
    fontFamily: "Pretendard, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    fontFamilyCode: "'JetBrains Mono', ui-monospace, monospace",
  },
  components: {
    Alert: {
      colorInfoBg: '#EAF3FC',
      colorInfoBorder: '#BFD7F0',
      colorWarningBg: '#FFF7E6',
      colorWarningBorder: '#FFE0A3',
    },
    Card: {
      colorBgContainer: '#FFFFFF',
      headerBg: '#FFFFFF',
    },
    Layout: { siderBg: '#0D2438' },
    Menu: {
      darkItemBg: '#0D2438',
      darkSubMenuItemBg: '#091D2E',
      darkItemSelectedBg: 'rgba(58,127,192,0.22)',
      darkItemSelectedColor: '#FFFFFF',
      darkItemColor: '#AEBCCD',
    },
    Table: {
      headerBg: '#F7F9FB',
      headerColor: '#64748B',
      rowHoverBg: '#F0F5FA',
      colorBgContainer: '#FFFFFF',
    },
  },
};

type AdminShellProps = PropsWithChildren<{
  title: string;
}>;

export function AdminShell({ title, children }: AdminShellProps) {
  const location = useLocation();
  const {
    session,
    serviceOptions,
    restoring,
    displayRoles,
    setServiceId,
    logout,
  } = useModel('adminSession');

  useEffect(() => {
    if (!restoring && !session.authenticated) {
      history.replace(
        `/login?redirect=${encodeURIComponent(`${location.pathname}${location.search}`)}`,
      );
    }
  }, [location.pathname, location.search, restoring, session.authenticated]);

  return (
    <ConfigProvider locale={koKR} theme={adminUiTheme}>
      <ProLayout
        title="Intent Routing"
        layout="mix"
        navTheme="realDark"
        fixedHeader
        fixSiderbar
        siderWidth={188}
        location={{ pathname: location.pathname }}
        route={{
          routes: [
            { path: '/dashboard', name: 'Dashboard', icon: <DashboardOutlined /> },
            { path: '/intents', name: 'Intent Catalog', icon: <ProfileOutlined /> },
            { path: '/releases', name: 'Releases', icon: <RocketOutlined /> },
            { path: '/test-runs', name: 'Test Runs', icon: <ExperimentOutlined /> },
            { path: '/api-keys', name: 'API Keys', icon: <KeyOutlined /> },
            { path: '/runtime-logs', name: 'Runtime Logs', icon: <FileSearchOutlined /> },
            { path: '/audit-logs', name: 'Audit Logs', icon: <AuditOutlined /> },
          ],
        }}
        menuItemRender={(item, dom) => (
          <a
            onClick={(event) => {
              event.preventDefault();
              if (item.path) history.push(item.path);
            }}
            href={item.path}
          >
            {dom}
          </a>
        )}
      >
        <PageContainer title={title} ghost={false} header={{ breadcrumb: {} }}>
          {restoring || !session.authenticated ? (
            <Skeleton active paragraph={{ rows: 8 }} />
          ) : (
            <>
              <Alert
                type="info"
                showIcon
                message="Sprint 11 Admin UI Phase 1"
                description="Authenticated console for service-scoped catalog work, test runs, releases, API keys, runtime logs, and audit evidence. Phase 2 governed approval workflows remain informational."
                style={{ marginBottom: 12 }}
              />
              <ServiceScopeBar
                session={session}
                roles={displayRoles}
                serviceOptions={serviceOptions}
                onServiceChange={setServiceId}
                onLogout={logout}
              />
              <main className="admin-page-content">{children}</main>
            </>
          )}
        </PageContainer>
      </ProLayout>
    </ConfigProvider>
  );
}
