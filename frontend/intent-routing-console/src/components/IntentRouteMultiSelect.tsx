import { Select, Space, Typography } from 'antd';

type IntentRouteMultiSelectProps = {
  value?: string[];
  onChange?: (value: string[]) => void;
  candidates: API.IntentRouteCandidate[];
  mode: 'intent' | 'route';
  placeholder?: string;
  disabled?: boolean;
  loading?: boolean;
};

export function IntentRouteMultiSelect({
  value,
  onChange,
  candidates,
  mode,
  placeholder,
  disabled,
  loading,
}: IntentRouteMultiSelectProps) {
  return (
    <Select
      mode="multiple"
      allowClear
      disabled={disabled}
      loading={loading}
      showSearch
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      optionFilterProp="label"
      style={{ width: '100%', maxWidth: '100%' }}
      options={candidates.map((candidate) => ({
        value: mode === 'intent' ? candidate.intent_id : candidate.route_key,
        label: mode === 'intent' ? candidate.intent_id : candidate.route_key,
        candidate,
      }))}
      optionRender={({ data }) => {
        const candidate = data.candidate as API.IntentRouteCandidate;
        return (
          <Space direction="vertical" size={0}>
            <Typography.Text>
              {mode === 'intent' ? candidate.intent_id : candidate.route_key}
            </Typography.Text>
            <Typography.Text type="secondary">{candidate.display_name}</Typography.Text>
          </Space>
        );
      }}
    />
  );
}
