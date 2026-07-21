import { Form, Input, Modal } from 'antd';

type CatalogVersionCreateModalProps = {
  open: boolean;
  loading?: boolean;
  onCancel: () => void;
  onCreate: (description: string) => Promise<void> | void;
};

type CatalogVersionFormValues = {
  description: string;
};

export function CatalogVersionCreateModal({
  open,
  loading = false,
  onCancel,
  onCreate,
}: CatalogVersionCreateModalProps) {
  const [form] = Form.useForm<CatalogVersionFormValues>();

  const handleCreate = async () => {
    const values = await form.validateFields();
    await onCreate(values.description.trim());
    form.resetFields();
  };

  const handleCancel = () => {
    form.resetFields();
    onCancel();
  };

  return (
    <Modal
      title="Catalog 버전 등록"
      open={open}
      centered
      width={640}
      okText="등록"
      cancelText="취소"
      confirmLoading={loading}
      onOk={handleCreate}
      onCancel={handleCancel}
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="description"
          label="버전 설명"
          rules={[
            { required: true, message: '버전 설명을 입력해주세요.' },
            {
              validator: async (_, value?: string) => {
                if ((value?.trim().length ?? 0) >= 10) return;
                throw new Error('공백을 제외하고 최소 10글자 이상 입력해주세요.');
              },
            },
          ]}
        >
          <Input.TextArea
            rows={4}
            showCount
            maxLength={500}
            placeholder="이 버전에 포함된 Intent/Example 변경 사유를 입력하세요."
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}
