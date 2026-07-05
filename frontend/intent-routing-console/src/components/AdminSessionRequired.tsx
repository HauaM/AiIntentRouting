import { Alert } from 'antd';

export function AdminSessionRequired() {
  return (
    <Alert
      type="warning"
      showIcon
      message="Admin API session is required"
      description="Open the settings control in the service scope bar and save X-Admin-Token, actor, roles, and service scope before loading read-only Admin API data."
    />
  );
}
