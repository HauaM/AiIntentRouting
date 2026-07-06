import { InfoCircleOutlined } from '@ant-design/icons';
import { Popover, Space, Typography } from 'antd';
import type { ReactNode } from 'react';

type FieldHelpLabelProps = {
  label: ReactNode;
  help: ReactNode;
};

export function FieldHelpLabel({ label, help }: FieldHelpLabelProps) {
  return (
    <Space size={6} className="field-help-label">
      <span>{label}</span>
      <Popover
        trigger={['hover', 'click']}
        placement="top"
        overlayClassName="field-help-popover"
        content={
          typeof help === 'string' ? (
            <Typography.Text>{help}</Typography.Text>
          ) : (
            help
          )
        }
      >
        <button
          type="button"
          className="field-help-label-button"
          aria-label={`${String(label)} 설명`}
        >
          <InfoCircleOutlined />
        </button>
      </Popover>
    </Space>
  );
}
