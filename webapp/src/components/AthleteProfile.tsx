import { useMemo } from 'react';
import {
  Title, Text, Badge, Group, Button, Anchor, SimpleGrid, Card, Table, Stack,
} from '@mantine/core';
import { ArrowLeftIcon } from '@phosphor-icons/react';
import type { Result, Profile, Metadata, Gender, Environment } from '../types';
import { GENDER_COLOR } from '../types';
import { getVariantName } from '../db';
import { MarkCell } from './MarkCell';
import { WikipediaW } from './WikipediaLink';

interface AthleteProfileProps {
  profile: Profile;
  results: Result[];
  onBack: () => void;
  onSchoolClick: (schoolId: number | null) => void;
  metadata?: Metadata | null;
  profilesMap: Map<number, Profile>;
}

interface PersonalBest {
  discipline: string;
  environment: Environment | null;
  mark_str: string | null;
  mark_num: number | null;
  year: number;
  place: number | null;
  is_wind_aided: boolean;
  is_converted: boolean;
}

interface PlacingSummary {
  gold: number;
  silver: number;
  bronze: number;
  top8: number;
  total: number;
}

function getDisciplineLabel(
  discipline: string,
  year: number,
  gender: Gender,
  environment: Environment | null,
  metadata?: Metadata | null
): string {
  if (!metadata) return discipline;
  const variant = getVariantName(discipline, year, gender, environment);
  return variant ?? discipline;
}

function computePersonalBests(results: Result[], metadata?: Metadata | null): PersonalBest[] {
  const byKey = new Map<string, Result[]>();
  for (const r of results) {
    if (r.is_dq || r.is_dnf || r.is_dns) continue;
    if (r.mark_num == null) continue;
    const env = r.environment ?? 'outdoor';
    const key = `${r.discipline}|${env}`;
    let list = byKey.get(key);
    if (!list) { list = []; byKey.set(key, list); }
    list.push(r);
  }

  const bests: PersonalBest[] = [];
  for (const [, list] of byKey) {
    const isTrack = list[0].mark_num != null && list[0].mark_num < 1000;
    const sorted = [...list].sort((a, b) => {
      if (isTrack) return (a.mark_num ?? 0) - (b.mark_num ?? 0);
      return (b.mark_num ?? 0) - (a.mark_num ?? 0);
    });
    const best = sorted[0];
    const label = getDisciplineLabel(best.discipline, best.year, best.gender, best.environment, metadata);
    bests.push({
      discipline: label,
      environment: best.environment,
      mark_str: best.mark_str,
      mark_num: best.mark_num,
      year: best.year,
      place: best.place,
      is_wind_aided: best.is_wind_aided === 1,
      is_converted: best.is_converted === 1,
    });
  }

  bests.sort((a, b) => a.discipline.localeCompare(b.discipline));
  return bests;
}

const CLASS_ABBR: Record<string, string> = {
  freshman: 'Fr', sophomore: 'So', junior: 'Jr', senior: 'Sr',
};

function computePlacingSummary(results: Result[]): PlacingSummary {
  let gold = 0, silver = 0, bronze = 0, top8 = 0, total = 0;
  for (const r of results) {
    if (r.place == null) continue;
    total++;
    if (r.place <= 8) top8++;
    if (r.place === 1) gold++;
    else if (r.place === 2) silver++;
    else if (r.place === 3) bronze++;
  }
  return { gold, silver, bronze, top8, total };
}

export function AthleteProfile({
  profile, results, onBack, onSchoolClick, metadata,
}: AthleteProfileProps) {
  const personalBests = useMemo(() => computePersonalBests(results, metadata), [results, metadata]);
  const placingSummary = useMemo(() => computePlacingSummary(results), [results]);

  const member = profile.members[0];
  const schools = [...new Set(profile.members.map(m => m.school))];
  const schoolNameToId = useMemo(() => {
    const map = new Map<string, number>();
    for (const r of results) {
      if (r.school && r.school_id != null) {
        map.set(r.school, r.school_id);
      }
    }
    return map;
  }, [results]);
  const yearStart = Math.min(...profile.members.map(m => m.year_start));
  const yearEnd = Math.max(...profile.members.map(m => m.year_end));
  const gender = member?.gender as Gender | undefined;
  const altNames = profile.aliases.filter(a => a !== profile.canonical_name);

  return (
    <Stack gap="md">
      <Button
        variant="subtle"
        size="xs"
        leftSection={<ArrowLeftIcon size={14} />}
        onClick={onBack}
        style={{ alignSelf: 'flex-start' }}
      >
        Back to results
      </Button>

      <div>
        <Group gap="xs" align="center">
          <Title order={2}>{profile.canonical_name}</Title>
          {gender && (
            <Badge variant="light" color={GENDER_COLOR[gender]}>
              {gender === 'men' ? 'M' : 'W'}
            </Badge>
          )}
          {profile.qid && <WikipediaW qid={profile.qid} size={26} />}
        </Group>
        <Text size="sm" c="dimmed" mt={2}>NCAAdb ID #{profile.athlete_id}</Text>
        <Group gap="xs" mt={4}>
          {schools.map(s => (
            <Anchor
              key={s}
              onClick={() => onSchoolClick(schoolNameToId.get(s) ?? null)}
              size="sm"
            >
              {s}
            </Anchor>
          )).reduce<React.ReactNode[]>((acc, el, i) =>
            i === 0 ? [el] : [...acc, ' / ', el], []
          )}
          <Text size="sm" c="dimmed">
            {yearStart === yearEnd ? yearStart : `${yearStart}\u2013${yearEnd}`}
          </Text>
          <Text size="sm" c="dimmed">
            {results.length} {results.length === 1 ? 'performance' : 'performances'}
          </Text>
        </Group>
        {altNames.length > 0 && (
          <Group gap="xs" mt={4}>
            <Text size="sm" c="dimmed">Also known as:</Text>
            {altNames.map(name => (
              <Badge key={name} size="sm" variant="outline" tt="none">{name}</Badge>
            ))}
          </Group>
        )}
      </div>

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        <Card withBorder padding="md">
          <Text fw={600} mb="xs">Championship Placings</Text>
          <Group gap="md" mb="xs">
            {placingSummary.gold > 0 && (
              <Text size="lg" title="Gold">{'\u{1F947}'} {placingSummary.gold}</Text>
            )}
            {placingSummary.silver > 0 && (
              <Text size="lg" title="Silver">{'\u{1F948}'} {placingSummary.silver}</Text>
            )}
            {placingSummary.bronze > 0 && (
              <Text size="lg" title="Bronze">{'\u{1F949}'} {placingSummary.bronze}</Text>
            )}
          </Group>
          <Group gap="md">
            <Text size="sm" c="dimmed">{placingSummary.top8} top-8 finishes</Text>
          </Group>
        </Card>

        {personalBests.length > 0 && (
          <Card withBorder padding="md">
            <Text fw={600} mb="xs">Championship Top-8 Bests</Text>
            <Stack gap={2}>
              {personalBests.map((pb, i) => (
                <Group key={`${pb.discipline}-${i}`} justify="space-between" wrap="nowrap">
                  <Group gap="xs" wrap="nowrap">
                    <Text size="sm">{pb.discipline}</Text>
                    {pb.environment && (
                      <Badge size="xs" variant="light" color={pb.environment === 'indoor' ? 'cyan' : 'teal'}>
                        {pb.environment === 'indoor' ? 'I' : 'O'}
                      </Badge>
                    )}
                  </Group>
                  <Group gap="xs" wrap="nowrap">
                    <Text size="sm" fw={500}>
                      <MarkCell
                        mark_str={pb.mark_str}
                        mark_num={pb.mark_num}
                        is_converted={pb.is_converted ? 1 : 0}
                        is_wind_aided={pb.is_wind_aided ? 1 : 0}
                      />
                    </Text>
                    <Text size="xs" c="dimmed">{pb.year}</Text>
                  </Group>
                </Group>
              ))}
            </Stack>
          </Card>
        )}
      </SimpleGrid>

      <div>
        <Title order={4} mb="xs">All Performances</Title>
        <Table.ScrollContainer minWidth={800}>
          <Table striped highlightOnHover withTableBorder>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Year</Table.Th>
                <Table.Th>Env</Table.Th>
                <Table.Th>Pl</Table.Th>
                <Table.Th>Discipline</Table.Th>
                <Table.Th>School</Table.Th>
                <Table.Th>Mark</Table.Th>
                <Table.Th>Split</Table.Th>
                <Table.Th>Wind</Table.Th>
                <Table.Th>Class</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {results.map(r => {
                const label = getDisciplineLabel(r.discipline, r.year, r.gender, r.environment, metadata);
                return (
                  <Table.Tr key={r.id}>
                    <Table.Td>{r.year}</Table.Td>
                    <Table.Td>
                      {r.environment && (
                        <Badge size="xs" variant="light" color={r.environment === 'indoor' ? 'cyan' : 'teal'}>
                          {r.environment === 'indoor' ? 'I' : 'O'}
                        </Badge>
                      )}
                    </Table.Td>
                    <Table.Td>{r.place || '-'}</Table.Td>
                    <Table.Td>
                      {r.is_relay === 1 && r.leg_idx != null
                        ? <>{label} <Text component="span" size="xs" c="dimmed">(Leg {r.leg_idx})</Text></>
                        : label}
                    </Table.Td>
                    <Table.Td>
                      <Anchor onClick={() => r.school && onSchoolClick(r.school_id)} style={{ cursor: 'pointer' }}>
                        {r.school}
                      </Anchor>
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
                        {r.class && (
                          <Badge size="xs" variant="outline">
                            {CLASS_ABBR[r.class] ?? r.class.charAt(0).toUpperCase()}
                          </Badge>
                        )}
                        {r.is_dq === 1 && <Badge size="xs" variant="light" color="red">DQ</Badge>}
                        {r.is_dnf === 1 && <Badge size="xs" variant="light" color="red">DNF</Badge>}
                        {r.is_dns === 1 && <Badge size="xs" variant="light" color="red">DNS</Badge>}
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </div>

      {results.some(r => r.is_relay === 1) && (
        <div>
          <Title order={4} mb="xs">Relay Appearances</Title>
          <Stack gap={4}>
            {results
              .filter(r => r.is_relay === 1)
              .map(r => (
                <Group key={r.id} gap="xs">
                  <Text size="sm" fw={500}>{r.year}</Text>
                  <Badge size="xs" variant="light" color={(r.environment ?? 'outdoor') === 'indoor' ? 'cyan' : 'teal'}>
                    {r.environment === 'indoor' ? 'I' : 'O'}
                  </Badge>
                  <Text size="sm">
                    {getDisciplineLabel(r.discipline, r.year, r.gender, r.environment, metadata)}
                  </Text>
                  <Text size="sm" c="dimmed">Pl {r.place ?? '-'}</Text>
                </Group>
              ))}
          </Stack>
        </div>
      )}
    </Stack>
  );
}
