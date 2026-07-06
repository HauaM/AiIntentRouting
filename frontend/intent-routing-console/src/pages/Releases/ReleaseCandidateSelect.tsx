import { Select, Space, Tag, Typography } from 'antd';

type ReleaseCandidateSelectProps = {
  value?: string;
  onChange?: (testRunId?: string) => void;
  onSelectCandidate?: (candidate: API.ReleaseCandidate) => void;
  candidates: API.ReleaseCandidate[];
};

const formatRate = (value: number) => `${((value <= 1 ? value : value / 100) * 100).toFixed(1)}%`;

export function ReleaseCandidateSelect({
  value,
  onChange,
  onSelectCandidate,
  candidates,
}: ReleaseCandidateSelectProps) {
  return (
    <Select
      showSearch
      value={value}
      placeholder="Release candidate 선택"
      optionFilterProp="label"
      style={{ minWidth: 420, width: '100%' }}
      options={candidates.map((candidate) => ({
        value: candidate.test_run_id,
        label: candidate.test_run_id,
        disabled: !candidate.eligible,
        candidate,
      }))}
      onChange={(testRunId, option) => {
        const selected = (Array.isArray(option) ? option[0] : option)
          ?.candidate as API.ReleaseCandidate | undefined;
        onChange?.(testRunId);
        if (selected) onSelectCandidate?.(selected);
      }}
      optionRender={({ data }) => {
        const candidate = data.candidate as API.ReleaseCandidate;
        return (
          <Space direction="vertical" size={2}>
            <Space wrap>
              <Typography.Text code>{candidate.test_run_id}</Typography.Text>
              <Tag color={candidate.eligible ? 'green' : 'red'}>
                {candidate.eligible ? 'eligible' : 'blocked'}
              </Tag>
              <Tag>pass {formatRate(candidate.pass_rate)}</Tag>
              <Tag>risk {formatRate(candidate.risk_pass_rate)}</Tag>
            </Space>
            <Typography.Text type="secondary">
              policy {candidate.policy_version} / catalog {candidate.intent_catalog_version}
            </Typography.Text>
            {!candidate.eligible && candidate.block_reasons.length ? (
              <Typography.Text type="secondary">
                {candidate.block_reasons.join(', ')}
              </Typography.Text>
            ) : null}
          </Space>
        );
      }}
    />
  );
}
