import { ExclamationCircleOutlined } from '@ant-design/icons';
import { Tag } from 'antd';

type AdminStatus =
  | 'active'
  | 'inactive'
  | 'disabled'
  | 'draft'
  | 'deprecated'
  | 'approved'
  | 'rejected'
  | 'pass'
  | 'fail'
  | 'success'
  | 'error'
  | 'risk'
  | 'low'
  | 'medium'
  | 'high'
  | 'unauthorized'
  | 'clarify'
  | 'review'
  | 'warning'
  | 'fallback'
  | 'blocker'
  | 'off_topic'
  | 'confident'
  | 'pending'
  | 'processing'
  | 'recommendation'
  | 'released'
  | 'blocked'
  | 'positive'
  | 'negative'
  | 'info'
  | 'system_admin'
  | 'dev'
  | 'test'
  | 'stage'
  | 'staging'
  | 'prod'
  | 'recorded'
  | 'normal'
  | 'none';

type AdminStatusTone = {
  bg: string;
  color: string;
  border: string;
  icon?: boolean;
};

const STATUS_TONE: Record<string, AdminStatusTone> = {
  active: { bg: '#EAF3EE', color: '#17724D', border: '#BFD8CA' },
  approved: { bg: '#EAF3EE', color: '#17724D', border: '#BFD8CA' },
  confident: { bg: '#EAF3EE', color: '#17724D', border: '#BFD8CA' },
  pass: { bg: '#EAF3EE', color: '#17724D', border: '#BFD8CA' },
  positive: { bg: '#EAF3EE', color: '#17724D', border: '#BFD8CA' },
  recorded: { bg: '#EAF3EE', color: '#17724D', border: '#BFD8CA' },
  clarify: { bg: '#FDF3E3', color: '#8A5A12', border: '#E9C889' },
  medium: { bg: '#FDF3E3', color: '#8A5A12', border: '#E9C889' },
  pending: { bg: '#FDF3E3', color: '#8A5A12', border: '#E9C889' },
  prod: { bg: '#FDF3E3', color: '#8A5A12', border: '#E9C889' },
  review: { bg: '#FDF3E3', color: '#8A5A12', border: '#E9C889' },
  warning: { bg: '#FDF3E3', color: '#8A5A12', border: '#E9C889' },
  blocked: { bg: '#FBE7E5', color: '#B3261E', border: '#E6B8B3', icon: true },
  blocker: { bg: '#FBE7E5', color: '#B3261E', border: '#E6B8B3', icon: true },
  error: { bg: '#FBE7E5', color: '#B3261E', border: '#E6B8B3', icon: true },
  fail: { bg: '#FBE7E5', color: '#B3261E', border: '#E6B8B3', icon: true },
  high: { bg: '#FBE9E7', color: '#A23B2E', border: '#E6B8B3', icon: true },
  rejected: { bg: '#FBE7E5', color: '#B3261E', border: '#E6B8B3', icon: true },
  risk: { bg: '#FBE9E7', color: '#A23B2E', border: '#E6B8B3', icon: true },
  unauthorized: { bg: '#FBE7E5', color: '#B3261E', border: '#E6B8B3', icon: true },
  dev: { bg: '#EEF0F3', color: '#5C6478', border: '#DCE1E8' },
  inactive: { bg: '#EEF0F3', color: '#5C6478', border: '#DCE1E8' },
  disabled: { bg: '#EEF0F3', color: '#5C6478', border: '#DCE1E8' },
  draft: { bg: '#EEF0F3', color: '#5C6478', border: '#DCE1E8' },
  deprecated: { bg: '#EEF0F3', color: '#5C6478', border: '#DCE1E8' },
  fallback: { bg: '#EEF0F3', color: '#5C6478', border: '#DCE1E8' },
  negative: { bg: '#EEF0F3', color: '#5C6478', border: '#DCE1E8' },
  normal: { bg: '#EEF0F3', color: '#5C6478', border: '#DCE1E8' },
  off_topic: { bg: '#EEF0F3', color: '#5C6478', border: '#DCE1E8' },
  stage: { bg: '#EAF3FC', color: '#1D5A96', border: '#BFD7F0' },
  staging: { bg: '#EAF3FC', color: '#1D5A96', border: '#BFD7F0' },
  test: { bg: '#EAF3FC', color: '#1D5A96', border: '#BFD7F0' },
  info: { bg: '#EAF3FC', color: '#1D5A96', border: '#BFD7F0' },
  low: { bg: '#EAF3FC', color: '#1D5A96', border: '#BFD7F0' },
  processing: { bg: '#EAF3FC', color: '#1D5A96', border: '#BFD7F0' },
  recommendation: { bg: '#EAF3FC', color: '#1D5A96', border: '#BFD7F0' },
  released: { bg: '#EAF3FC', color: '#1D5A96', border: '#BFD7F0' },
  system_admin: { bg: '#EAF3FC', color: '#1D5A96', border: '#BFD7F0' },
  success: { bg: '#EAF3EE', color: '#17724D', border: '#BFD8CA' },
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
