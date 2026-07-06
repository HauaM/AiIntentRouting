import { Alert } from 'antd';

export function AdminSessionRequired() {
  return (
    <Alert
      type="warning"
      showIcon
      message="No accessible service selected"
      description="Sign in with an account that has access to at least one service before loading read-only Admin API data."
    />
  );
}
