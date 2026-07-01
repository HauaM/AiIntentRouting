import type { PropsWithChildren } from 'react';
import { PageContainer, ProLayout } from '@ant-design/pro-components';
import { Alert, ConfigProvider } from 'antd';
import {
  AuditOutlined,
  DashboardOutlined,
  DeploymentUnitOutlined,
  FileSearchOutlined,
  ProfileOutlined,
} from '@ant-design/icons';
import { ServiceScopeBar, type ServiceScopeBarProps } from './ServiceScopeBar';

const theme = {
  token: {
    colorPrimary: '#1D5A96',
    colorSuccess: '#2F8F5B',
    colorWarning: '#D4920B',
    colorError: '#C0392B',
    colorTextBase: '#1C2733',
    colorBgLayout: '#F4F6F8',
    borderRadius: 6,
    fontFamily: "'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    fontFamilyCode: "'JetBrains Mono', ui-monospace, monospace",
  },
  components: {
    Layout: { siderBg: '#0D2438' },
    Menu: {
      darkItemBg: '#0D2438',
      darkSubMenuItemBg: '#091D2E',
      darkItemSelectedBg: 'rgba(58,127,192,0.22)',
      darkItemSelectedColor: '#FFFFFF',
      darkItemColor: '#AEBCCD',
    },
    Table: { headerBg: '#F7F9FB', headerColor: '#64748B', rowHoverBg: '#F0F5FA' },
  },
};

type AdminShellProps = PropsWithChildren<{
  title: string;
  scope: ServiceScopeBarProps;
}>;

export function AdminShell({ title, scope, children }: AdminShellProps) {
  return (
    <ConfigProvider theme={theme}>
      <ProLayout
        title="Intent Routing"
        layout="mix"
        navTheme="realDark"
        fixedHeader
        fixSiderbar
        siderWidth={178}
        route={{
          routes: [
            { path: '/', name: 'Dashboard', icon: <DashboardOutlined /> },
            { path: '/intents', name: 'Intent Catalog', icon: <ProfileOutlined /> },
            { path: '/runtime-logs', name: 'Runtime Logs', icon: <FileSearchOutlined /> },
            { path: '/audit-logs', name: 'Audit Logs', icon: <AuditOutlined /> },
            { path: '/releases', name: 'Releases', icon: <DeploymentUnitOutlined /> },
          ],
        }}
        menuItemRender={(item, dom) => <a href={item.path ?? '#'}>{dom}</a>}
      >
        <PageContainer
          title={title}
          ghost={false}
          header={{
            breadcrumb: {},
          }}
        >
          <Alert
            type="info"
            showIcon
            message="Sprint 9: Go"
            description="Admin UI implementation was excluded from Sprint 9. This screen follows the v04 reference pattern kit."
            style={{ marginBottom: 12 }}
          />
          <ServiceScopeBar {...scope} />
          <div style={{ marginTop: 12 }}>{children}</div>
        </PageContainer>
      </ProLayout>
    </ConfigProvider>
  );
}
