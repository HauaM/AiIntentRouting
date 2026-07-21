import { Tag, Typography } from 'antd';

type VersionChipProps = {
  label?: string;
  value: string | null | undefined;
  maxDisplayLength?: number;
};

export function VersionChip({ label, value, maxDisplayLength }: VersionChipProps) {
  const displayValue =
    value && maxDisplayLength && value.length > maxDisplayLength
      ? `${value.slice(0, maxDisplayLength)}...`
      : value;

  return (
    <Tag>
      {label ? <>{label} </> : null}
      {value ? (
        <Typography.Text code copyable={{ text: value }}>
          {displayValue}
        </Typography.Text>
      ) : (
        'none'
      )}
    </Tag>
  );
}
