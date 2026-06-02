import { Tooltip, Text } from '@mantine/core';

interface MarkCellProps {
  mark_str: string | null;
  mark_num: number | null;
  is_dq?: number;
  is_dnf?: number;
  is_dns?: number;
  is_converted?: number;
  is_wind_aided?: number;
}

function formatMarkNum(n: number): string {
  return String(Math.round(n * 10000) / 10000);
}

export function MarkCell({ mark_str, mark_num, is_dq, is_dnf, is_dns, is_converted, is_wind_aided }: MarkCellProps) {
  const isDns = !!is_dq || !!is_dnf || !!is_dns;
  const display = is_dq ? 'DQ' : is_dnf ? 'DNF' : is_dns ? 'DNS' : (mark_str || '');

  return (
    <Tooltip label={mark_num != null ? formatMarkNum(mark_num) : ''} disabled={isDns || mark_num == null}>
      <span style={{ whiteSpace: 'nowrap' }}>
        {display}
        {is_converted === 1 && <Text component="sup" size="xs" c="dimmed">c</Text>}
        {is_wind_aided === 1 && <Text component="sup" size="xs" c="dimmed">w</Text>}
      </span>
    </Tooltip>
  );
}
