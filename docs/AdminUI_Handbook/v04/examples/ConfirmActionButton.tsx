import type { ReactNode } from 'react';
import { Button, Modal, message } from 'antd';

type ConfirmActionButtonProps = {
  children: ReactNode;
  title: string;
  content: ReactNode;
  okText: string;
  danger?: boolean;
  disabled?: boolean;
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
    <Button danger={danger} disabled={disabled} onClick={openConfirm}>
      {children}
    </Button>
  );
}

