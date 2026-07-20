import { useEffect, useState } from 'react';
import { Alert, Input, Modal, Space, Typography } from 'antd';
import { parseCsvText, type CsvCaseDraft } from './csvCaseBuilder';

type CsvImportModalProps = {
  open: boolean;
  initialCsvText: string;
  onCancel: () => void;
  onSave: (cases: CsvCaseDraft[], csvText: string) => void;
};

const MODAL_TOKENS = {
  contentPadding: 24,
  headerHeight: 56,
  footerHeight: 56,
  viewportGap: 48,
  bodyReservedHeight: 180,
  separator: '1px solid var(--ant-color-border-secondary)',
} as const;

export function CsvImportModal({
  open,
  initialCsvText,
  onCancel,
  onSave,
}: CsvImportModalProps) {
  const [csvText, setCsvText] = useState(initialCsvText);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  useEffect(() => {
    if (open) {
      setCsvText(initialCsvText);
      setValidationErrors([]);
    }
  }, [initialCsvText, open]);

  const save = () => {
    const result = parseCsvText(csvText);
    if (!result.ok) {
      setValidationErrors(result.errors);
      return;
    }
    onSave(result.cases, csvText);
  };

  return (
    <Modal
      title="CSV 가져오기"
      open={open}
      centered
      width={800}
      okText="저장"
      cancelText="취소"
      onCancel={onCancel}
      onOk={save}
      style={{ maxWidth: `calc(100vw - ${MODAL_TOKENS.viewportGap}px)` }}
      styles={{
        header: {
          height: MODAL_TOKENS.headerHeight,
          padding: `0 ${MODAL_TOKENS.contentPadding}px`,
          display: 'flex',
          alignItems: 'center',
          borderBottom: MODAL_TOKENS.separator,
          marginBottom: 0,
        },
        body: {
          padding: MODAL_TOKENS.contentPadding,
          maxHeight: `calc(100dvh - ${MODAL_TOKENS.bodyReservedHeight}px)`,
          overflow: 'auto',
        },
        footer: {
          height: MODAL_TOKENS.footerHeight,
          padding: `12px ${MODAL_TOKENS.contentPadding}px`,
          borderTop: MODAL_TOKENS.separator,
          marginTop: 0,
        },
        content: {
          padding: 0,
          overflow: 'hidden',
        },
      }}
    >
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <Typography.Text type="secondary">
          헤더는 반드시 <Typography.Text code>case_id</Typography.Text>,{' '}
          <Typography.Text code>query</Typography.Text>,{' '}
          <Typography.Text code>expected_intent</Typography.Text>,{' '}
          <Typography.Text code>case_type</Typography.Text>,{' '}
          <Typography.Text code>memo</Typography.Text> 순서여야 합니다.
        </Typography.Text>
        {validationErrors.length ? (
          <Alert
            type="error"
            showIcon
            message="CSV 검증 오류"
            description={
              <Space direction="vertical" size={2}>
                {validationErrors.map((error) => (
                  <Typography.Text key={error} type="danger">
                    {error}
                  </Typography.Text>
                ))}
              </Space>
            }
          />
        ) : null}
        <Input.TextArea
          rows={12}
          value={csvText}
          onChange={(event) => setCsvText(event.target.value)}
          placeholder={[
            'case_id,query,expected_intent,case_type,memo',
            'tc-001,password reset help,it_password_reset,positive,known happy path',
          ].join('\n')}
        />
      </Space>
    </Modal>
  );
}
