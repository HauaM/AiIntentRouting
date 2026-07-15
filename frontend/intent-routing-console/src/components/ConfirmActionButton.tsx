import type { ReactNode } from 'react';
import { Button, Input, Modal, Space, Typography, message, type ButtonProps } from 'antd';

type ConfirmActionButtonProps = Pick<
  ButtonProps,
  'className' | 'danger' | 'disabled' | 'size' | 'style' | 'type'
> & {
  children: ReactNode;
  title: string;
  content: ReactNode;
  okText: string;
  onConfirm: () => Promise<void>;
  onSuccess?: () => void;
  riskLevel?: 'low' | 'high';
  confirmText?: string;
  requireTypedConfirmation?: boolean;
};

export function ConfirmActionButton({
  children,
  title,
  content,
  okText,
  danger = false,
  disabled = false,
  className,
  riskLevel,
  confirmText,
  requireTypedConfirmation,
  size,
  style,
  type,
  onConfirm,
  onSuccess,
}: ConfirmActionButtonProps) {
  const highRisk = danger || riskLevel === 'high';

  const openConfirm = () => {
    let typedValue = '';

    Modal.confirm({
      title,
      content:
        requireTypedConfirmation && confirmText ? (
          <Space direction="vertical" size={8} style={{ width: '100%' }}>
            {content}
            <Typography.Text type="secondary">typed confirmation: {confirmText}</Typography.Text>
            <Input
              aria-label="typed confirmation"
              placeholder={confirmText}
              onChange={(event) => {
                typedValue = event.target.value;
              }}
            />
          </Space>
        ) : (
          content
        ),
      okText,
      cancelText: '취소',
      okButtonProps: { danger: highRisk },
      async onOk() {
        if (requireTypedConfirmation && confirmText && typedValue !== confirmText) {
          message.error('확인 문구가 일치하지 않습니다.');
          throw new Error('typed confirmation mismatch');
        }
        await onConfirm();
        message.success('처리되었습니다.');
        onSuccess?.();
      },
    });
  };

  return (
    <Button
      className={className}
      danger={highRisk}
      disabled={disabled}
      size={size}
      style={style}
      type={type}
      onClick={openConfirm}
    >
      {children}
    </Button>
  );
}
