import { useEffect } from 'react';
import { Alert, Form, Input, InputNumber, Modal, Space, Switch, Typography } from 'antd';
import type { TestPolicyDraft } from './testPolicy';

const MODAL_TOKENS = {
  contentPadding: 24,
  headerHeight: 56,
  footerHeight: 56,
  viewportGap: 48,
  bodyReservedHeight: 180,
  separator: '1px solid var(--ant-color-border-secondary)',
} as const;

type CustomTestPolicyModalProps = {
  open: boolean;
  initialValue: TestPolicyDraft;
  onCancel: () => void;
  onConfirm: (value: TestPolicyDraft) => void;
};

type CustomPolicyFormValues = Omit<TestPolicyDraft, 'off_topic_policy'> & {
  off_topic_policy: Omit<API.OffTopicPolicySettings, 'keywords'> & { keywords: string };
};

const scoreField = (label: string, help: string) => ({
  label,
  extra: help,
  rules: [{ required: true, message: `${label}를 입력하세요.` }],
});

export function CustomTestPolicyModal({
  open,
  initialValue,
  onCancel,
  onConfirm,
}: CustomTestPolicyModalProps) {
  const [form] = Form.useForm<CustomPolicyFormValues>();

  useEffect(() => {
    if (open) {
      form.setFieldsValue({
        ...initialValue,
        off_topic_policy: {
          ...initialValue.off_topic_policy,
          keywords: initialValue.off_topic_policy.keywords.join(', '),
        },
      });
    }
  }, [form, initialValue, open]);

  return (
    <Modal
      title="테스트 정책 직접 설정"
      open={open}
      centered
      width={720}
      style={{ maxWidth: `calc(100vw - ${MODAL_TOKENS.viewportGap}px)` }}
      onCancel={onCancel}
      onOk={() => form.submit()}
      okText="설정 반영"
      cancelText="취소"
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
      }}
    >
      <Alert
        type="info"
        showIcon
        message="현재 선택된 정책을 초기값으로 보여줍니다."
        description="설정을 반영해도 기존 정책 버전은 수정되지 않습니다. 다음 단계에서 새 정책 버전을 만들어 테스트에 적용합니다."
        style={{ marginBottom: 20 }}
      />
      <Form
        form={form}
        layout="vertical"
        onFinish={(value) => onConfirm({
          ...value,
          threshold_preset: 'custom',
          off_topic_policy: {
            ...value.off_topic_policy,
            keywords: value.off_topic_policy.keywords
              .split(',')
              .map((keyword) => keyword.trim())
              .filter(Boolean),
          },
        })}
      >
        <Form.Item hidden name="threshold_preset"><Input /></Form.Item>
        <Form.Item
          name="threshold_value"
          {...scoreField('일치 기준 점수', '후보의 신뢰도가 이 점수 이상일 때만 intent를 확정합니다. 오탐을 더 줄여야 하면 높이고, 미분류가 많으면 낮추세요.')}
        >
          <InputNumber min={0} max={1} step={0.01} precision={2} style={{ width: 328 }} />
        </Form.Item>
        <Form.Item
          name="clarify_margin"
          {...scoreField('명확화 여유 점수', '1·2순위 후보 점수 차이가 이 값보다 작으면 확인이 필요한 요청으로 분류합니다. 유사한 의도가 자주 혼동되면 높이세요.')}
        >
          <InputNumber min={0} max={1} step={0.01} precision={2} style={{ width: 328 }} />
        </Form.Item>
        <Form.Item
          name="min_candidate_score"
          {...scoreField('최소 후보 점수', '후보로 검토할 최소 신뢰도입니다. 일치 기준 점수보다 클 수 없습니다. 낮추면 더 많은 후보를 비교합니다.')}
        >
          <InputNumber min={0} max={1} step={0.01} precision={2} style={{ width: 328 }} />
        </Form.Item>
        <Form.Item
          name="fallback_score"
          {...scoreField('Fallback 점수', '후보가 이 점수에도 미치지 못하면 fallback으로 처리합니다. 최소 후보 점수보다 클 수 없습니다.')}
        >
          <InputNumber min={0} max={1} step={0.01} precision={2} style={{ width: 328 }} />
        </Form.Item>
        <Space direction="vertical" size={0} style={{ width: '100%' }}>
          <Form.Item name={['risk_policy', 'enabled']} valuePropName="checked" label="위험 요청 정책">
            <Switch checkedChildren="사용" unCheckedChildren="미사용" />
          </Form.Item>
          <Typography.Text type="secondary">
            위험 요청 감지 정책을 사용합니다. 안전 검증 요구사항이 있는 서비스에서는 기본값을 유지하세요.
          </Typography.Text>
          <Form.Item name={['off_topic_policy', 'enabled']} valuePropName="checked" label="범위 외 요청 정책" style={{ marginTop: 16 }}>
            <Switch checkedChildren="사용" unCheckedChildren="미사용" />
          </Form.Item>
          <Typography.Text type="secondary">
            서비스 범위를 벗어난 요청을 별도로 처리합니다. 전용 안내가 필요할 때만 아래 문구와 키워드를 수정하세요.
          </Typography.Text>
          <Form.Item name={['off_topic_policy', 'keywords']} label="범위 외 키워드 (쉼표로 구분)" style={{ marginTop: 16 }}>
            <Input placeholder="예: 날씨, 주식" />
          </Form.Item>
          <Form.Item name={['off_topic_policy', 'message']} label="범위 외 안내 문구">
            <Input.TextArea rows={3} maxLength={300} showCount />
          </Form.Item>
        </Space>
      </Form>
    </Modal>
  );
}
