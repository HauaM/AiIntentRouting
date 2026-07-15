import { ExclamationCircleOutlined } from '@ant-design/icons';
import { Tag } from 'antd';

type AdminStatus =
  | 'active'
  | 'inactive'
  | 'disabled'
  | 'draft'
  | 'deprecated'
  | 'pass'
  | 'fail'
  | 'risk'
  | 'unauthorized'
  | 'clarify'
  | 'fallback'
  | 'off_topic'
  | 'confident'
  | 'pending'
  | 'recorded'
  | 'none';

type AdminStatusTone = {
  bg: string;
  color: string;
  border: string;
  icon?: boolean;
};

const STATUS_TONE: Record<string, AdminStatusTone> = {
  active: { bg: '#EAF3EE', color: '#17724D', border: '#BFD8CA' },
  confident: { bg: '#EAF3EE', color: '#17724D', border: '#BFD8CA' },
  pass: { bg: '#EAF3EE', color: '#17724D', border: '#BFD8CA' },
  recorded: { bg: '#EAF3EE', color: '#17724D', border: '#BFD8CA' },
  clarify: { bg: '#FDF3E3', color: '#8A5A12', border: '#E9C889' },
  pending: { bg: '#FDF3E3', color: '#8A5A12', border: '#E9C889' },
  fail: { bg: '#FBE7E5', color: '#B3261E', border: '#E6B8B3', icon: true },
  risk: { bg: '#FBE9E7', color: '#A23B2E', border: '#E6B8B3', icon: true },
  unauthorized: { bg: '#FBE7E5', color: '#B3261E', border: '#E6B8B3', icon: true },
  inactive: { bg: '#EEF0F3', color: '#5C6478', border: '#DCE1E8' },
  disabled: { bg: '#EEF0F3', color: '#5C6478', border: '#DCE1E8' },
  draft: { bg: '#EEF0F3', color: '#5C6478', border: '#DCE1E8' },
  deprecated: { bg: '#EEF0F3', color: '#5C6478', border: '#DCE1E8' },
  fallback: { bg: '#EEF0F3', color: '#5C6478', border: '#DCE1E8' },
  off_topic: { bg: '#EEF0F3', color: '#5C6478', border: '#DCE1E8' },
  none: { bg: '#EEF0F3', color: '#5C6478', border: '#DCE1E8' },
};

export function StatusTag({
  status,
  label,
  size = 'small',
}: {
  status?: AdminStatus | string | null;
  label?: string;
  size?: 'small' | 'middle';
}) {
  const normalized = status || 'none';
  const tone = STATUS_TONE[normalized] ?? STATUS_TONE.none;
  return (
    <Tag
      className={`admin-status-tag admin-status-tag-${size}`}
      icon={tone.icon ? <ExclamationCircleOutlined /> : undefined}
      style={{
        background: tone.bg,
        borderColor: tone.border,
        color: tone.color,
      }}
    >
      {label ?? normalized}
    </Tag>
  );
}
