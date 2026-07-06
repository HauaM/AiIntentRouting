import { Tag, Typography } from 'antd';

type VersionChipProps = {
  label: string;
  value: string | null | undefined;
};

export function VersionChip({ label, value }: VersionChipProps) {
  return (
    <Tag>
      {label}{' '}
      {value ? (
        <Typography.Text code copyable>
          {value}
        </Typography.Text>
      ) : (
        'none'
      )}
    </Tag>
  );
}
