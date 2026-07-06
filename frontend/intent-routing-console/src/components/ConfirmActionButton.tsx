import type { ReactNode } from 'react';
import { Button, Modal, message, type ButtonProps } from 'antd';

type ConfirmActionButtonProps = Pick<ButtonProps, 'danger' | 'disabled' | 'size' | 'type'> & {
  children: ReactNode;
  title: string;
  content: ReactNode;
  okText: string;
  onConfirm: () => Promise<void>;
  onSuccess?: () => void;
};

export function ConfirmActionButton({
  children,
  title,
  content,
  okText,
  danger = false,
  disabled = false,
  size,
  type,
  onConfirm,
  onSuccess,
}: ConfirmActionButtonProps) {
  const openConfirm = () => {
    Modal.confirm({
      title,
      content,
      okText,
      cancelText: '취소',
      okButtonProps: { danger },
      async onOk() {
        await onConfirm();
        message.success('처리되었습니다.');
        onSuccess?.();
      },
    });
  };

  return (
    <Button danger={danger} disabled={disabled} size={size} type={type} onClick={openConfirm}>
      {children}
    </Button>
  );
}
