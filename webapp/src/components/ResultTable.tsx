import { useState, useCallback } from 'react';
import {
  Table, Badge, Tooltip, ActionIcon, Anchor, Group, Text,
} from '@mantine/core';
import { CopyIcon, CheckIcon } from '@phosphor-icons/react';
import type { Result, SortState, SortColumn, Metadata, Profile, Gender } from '../types';
import { GENDER_COLOR } from '../types';
import { getVariantName } from '../db';
import { MarkCell } from './MarkCell';
import { WikipediaW } from './WikipediaLink';

interface ResultTableProps {
  results: Result[];
  sort: SortState;
  onSortChange: (column: SortColumn) => void;
  onAthleteClick: (athleteId: number | null) => void;
  onSchoolClick: (schoolId: number | null) => void;
  metadata?: Metadata | null;
  profilesMap: Map<number, Profile>;
}

function SortHeader({
  column, label, sort, onSortChange,
}: {
  column: SortColumn; label: string;
  sort: SortState; onSortChange: (column: SortColumn) => void;
}) {
  const isActive = sort.column === column;
  const arrow = isActive ? (sort.direction === 'asc' ? ' ▲' : ' ▼') : '';
  return (
    <Table.Th
      style={{ cursor: 'pointer', userSelect: 'none', whiteSpace: 'nowrap' }}
      onClick={() => onSortChange(column)}
    >
      {label}{arrow}
    </Table.Th>
  );
}

const envBadge = (env: string) => (
  <Badge size="xs" variant="light" color={env === 'indoor' ? 'cyan' : 'teal'}>
    {env === 'indoor' ? 'I' : 'O'}
  </Badge>
);

const genderBadge = (gender: string) => (
  <Badge size="xs" variant="light" color={GENDER_COLOR[gender as Gender]}>
    {gender === 'men' ? 'M' : 'W'}
  </Badge>
);

const CLASS_ABBR: Record<string, string> = {
  freshman: 'Fr', sophomore: 'So', junior: 'Jr', senior: 'Sr',
};

const classBadge = (cls: string) => (
  <Badge size="xs" variant="outline">
    {CLASS_ABBR[cls] ?? cls.charAt(0).toUpperCase()}
  </Badge>
);

const flagBadge = (label: string) => (
  <Badge size="xs" variant="light" color="red">{label}</Badge>
);

export function ResultTable({
  results, sort, onSortChange, onAthleteClick, onSchoolClick,
  metadata, profilesMap,
}: ResultTableProps) {
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const copyToClipboard = useCallback((r: Result) => {
    const json = JSON.stringify(r, null, 2);
    navigator.clipboard.writeText(json).then(() => {
      setCopiedId(r.id);
      setTimeout(() => setCopiedId(null), 1500);
    });
  }, []);

  return (
    <Table.ScrollContainer minWidth={900} maxHeight="70vh">
      <Table striped highlightOnHover withTableBorder stickyHeader stickyHeaderOffset={0}>
        <Table.Thead>
          <Table.Tr>
            <Table.Th w={36} />
            <SortHeader column="year" label="Year" sort={sort} onSortChange={onSortChange} />
            <Table.Th>Env</Table.Th>
            <Table.Th>Gender</Table.Th>
            <SortHeader column="place" label="Pl" sort={sort} onSortChange={onSortChange} />
            <SortHeader column="name" label="Name" sort={sort} onSortChange={onSortChange} />
            <SortHeader column="school" label="School" sort={sort} onSortChange={onSortChange} />
            <Table.Th>Discipline</Table.Th>
            <SortHeader column="mark_num" label="Mark" sort={sort} onSortChange={onSortChange} />
            <SortHeader column="split_time" label="Split" sort={sort} onSortChange={onSortChange} />
            <Table.Th>Wind</Table.Th>
            <Table.Th>Class</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {results.map((r) => {
            const profile = r.athlete_id != null ? profilesMap.get(r.athlete_id) : undefined;
            const displayName = profile?.canonical_name ?? r.name;
            const nameDiffers = profile && profile.canonical_name !== r.name;

            return (
              <Table.Tr key={r.id}>
                <Table.Td>
                  <Tooltip label={copiedId === r.id ? 'Copied!' : 'Copy as JSON'}>
                    <ActionIcon
                      size="xs"
                      variant="subtle"
                      color={copiedId === r.id ? 'teal' : 'gray'}
                      onClick={() => copyToClipboard(r)}
                    >
                      {copiedId === r.id ? <CheckIcon size={14} /> : <CopyIcon size={14} />}
                    </ActionIcon>
                  </Tooltip>
                </Table.Td>
                <Table.Td>{r.year}</Table.Td>
                <Table.Td>{r.environment && envBadge(r.environment)}</Table.Td>
                <Table.Td>{r.gender && genderBadge(r.gender)}</Table.Td>
                <Table.Td>{r.place || '-'}</Table.Td>
                <Table.Td>
                  <Group gap={6} wrap="nowrap">
                    {nameDiffers ? (
                      <Tooltip label={`Originally entered as: ${r.name}`}>
                        <Anchor
                          onClick={() => onAthleteClick(r.athlete_id)}
                          style={{ cursor: 'pointer' }}
                        >
                          {displayName}
                        </Anchor>
                      </Tooltip>
                    ) : (
                      <Anchor
                        onClick={() => onAthleteClick(r.athlete_id)}
                        style={{ cursor: 'pointer' }}
                      >
                        {displayName}
                      </Anchor>
                    )}
                    {profile?.qid && <WikipediaW qid={profile.qid} />}
                  </Group>
                  {r.leg_idx !== null && r.is_relay === 1 && (
                    <Text component="span" size="xs" c="dimmed"> (Leg {r.leg_idx})</Text>
                  )}
                </Table.Td>
                <Table.Td>
                  {r.school && (
                    <Anchor onClick={() => onSchoolClick(r.school_id)} style={{ cursor: 'pointer' }}>
                      {r.school}
                    </Anchor>
                  )}
                </Table.Td>
                <Table.Td>
                  {metadata ? (getVariantName(r.discipline, r.year, r.gender, r.environment) ?? r.discipline) : r.discipline}
                </Table.Td>
                <Table.Td>
                  <MarkCell
                    mark_str={r.mark_str}
                    mark_num={r.mark_num}
                    is_dq={r.is_dq}
                    is_dnf={r.is_dnf}
                    is_dns={r.is_dns}
                    is_converted={r.is_converted}
                    is_wind_aided={r.is_wind_aided}
                  />
                </Table.Td>
                <Table.Td>{r.split_time || ''}</Table.Td>
                <Table.Td>{r.wind !== null ? `${r.wind > 0 ? '+' : ''}${r.wind.toFixed(1)}` : ''}</Table.Td>
                <Table.Td>
                  <Group gap={4} wrap="nowrap">
                    {r.class && classBadge(r.class)}
                    {r.is_dq === 1 && flagBadge('DQ')}
                    {r.is_dnf === 1 && flagBadge('DNF')}
                    {r.is_dns === 1 && flagBadge('DNS')}
                  </Group>
                </Table.Td>
              </Table.Tr>
            );
          })}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}
