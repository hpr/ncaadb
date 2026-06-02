import { useMemo, useState } from 'react';
import {
  Title, Text, Badge, Group, Button, Anchor, SimpleGrid, Card, Table, Stack, Pagination,
} from '@mantine/core';
import { ArrowLeftIcon, ArrowSquareOutIcon } from '@phosphor-icons/react';
import type { Result, School, Metadata, Gender, Environment } from '../types';
import { GENDER_COLOR } from '../types';
import { getVariantName } from '../db';
import { MarkCell } from './MarkCell';

const PERF_PAGE_SIZE = 100;

interface CollegeProfileProps {
  school: School;
  results: Result[];
  onBack: () => void;
  onAthleteClick: (athleteId: number | null) => void;
  metadata?: Metadata | null;
}

interface PersonalBest {
  discipline: string;
  environment: Environment | null;
  gender: Gender;
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

interface NotableAthlete {
  athlete_id: number | null;
  name: string;
  gender: Gender;
  performances: number;
  first_year: number;
  last_year: number;
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
    const key = `${r.discipline}|${env}|${r.gender}`;
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
      gender: best.gender,
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

function computeNotableAthletes(results: Result[], limit: number = 20): NotableAthlete[] {
  const byAthlete = new Map<number | null, { athlete_id: number | null; name: string; gender: Gender; years: Set<number>; count: number }>();
  for (const r of results) {
    const key = r.athlete_id;
    let entry = byAthlete.get(key);
    if (!entry) {
      entry = { athlete_id: r.athlete_id, name: r.name, gender: r.gender, years: new Set(), count: 0 };
      byAthlete.set(key, entry);
    }
    entry.count++;
    entry.years.add(r.year);
  }
  return [...byAthlete.values()]
    .sort((a, b) => b.count - a.count)
    .slice(0, limit)
    .map(e => ({
      athlete_id: e.athlete_id,
      name: e.name,
      gender: e.gender,
      performances: e.count,
      first_year: Math.min(...e.years),
      last_year: Math.max(...e.years),
    }));
}

const CLASS_ABBR: Record<string, string> = {
  freshman: 'Fr', sophomore: 'So', junior: 'Jr', senior: 'Sr',
};

const WP_BASE = 'https://en.wikipedia.org/wiki/';

function wpUrl(title: string | null): string | null {
  if (!title) return null;
  return WP_BASE + encodeURIComponent(title.replace(/ /g, '_'));
}

export function CollegeProfile({
  school, results, onBack, onAthleteClick, metadata,
}: CollegeProfileProps) {
  const personalBests = useMemo(() => computePersonalBests(results, metadata), [results, metadata]);
  const placingSummary = useMemo(() => computePlacingSummary(results), [results]);
  const notableAthletes = useMemo(() => computeNotableAthletes(results), [results]);
  const [perfPage, setPerfPage] = useState(0);
  const perfTotalPages = Math.ceil(results.length / PERF_PAGE_SIZE);
  const pagedResults = results.slice(perfPage * PERF_PAGE_SIZE, (perfPage + 1) * PERF_PAGE_SIZE);

  const firstYear = results.length > 0 ? Math.min(...results.map(r => r.year)) : null;
  const lastYear = results.length > 0 ? Math.max(...results.map(r => r.year)) : null;
  const yearsSpan = firstYear && lastYear && firstYear !== lastYear ? `${firstYear}\u2013${lastYear}` : firstYear?.toString();

  const nicknames = useMemo(() => {
    const nicks: string[] = [];
    if (school.men_nickname && school.men_nickname === school.women_nickname) {
      nicks.push(school.men_nickname);
    } else {
      if (school.men_nickname) nicks.push(school.men_nickname);
      if (school.women_nickname) nicks.push(school.women_nickname);
    }
    return nicks;
  }, [school]);

  const externalLinks = useMemo(() => {
    const links: { label: string; url: string }[] = [];
    const enwikiUrl = wpUrl(school.enwiki);
    if (enwikiUrl) links.push({ label: school.enwiki!, url: enwikiUrl });
    const athUrl = wpUrl(school.athletics_enwiki);
    if (athUrl) links.push({ label: school.athletics_enwiki!, url: athUrl });
    const catUrl = wpUrl(school.category_enwiki);
    if (catUrl) links.push({ label: school.category_enwiki!, url: catUrl });
    return links;
  }, [school]);

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
          <Title order={2}>{school.label || school.name}</Title>
        </Group>
        {school.description && (
          <Text size="sm" c="dimmed" mt={4}>{school.description}</Text>
        )}
        <Group gap="xs" mt={4}>
          {nicknames.length > 0 && (
            <Group gap={4}>
              {nicknames.map(n => (
                <Badge key={n} variant="outline" tt="none">{n}</Badge>
              ))}
            </Group>
          )}
          {yearsSpan && (
            <Text size="sm" c="dimmed">{yearsSpan}</Text>
          )}
          <Text size="sm" c="dimmed">
            {results.length.toLocaleString()} {results.length === 1 ? 'performance' : 'performances'}
          </Text>
        </Group>
        {externalLinks.length > 0 && (
          <Group gap="xs" mt={4}>
            {externalLinks.map(link => (
              <Anchor
                key={link.url}
                href={link.url}
                target="_blank"
                size="xs"
              >
                {link.label} <ArrowSquareOutIcon size={10} style={{ verticalAlign: '1px' }} />
              </Anchor>
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
            <Text size="sm" c="dimmed">{placingSummary.top8.toLocaleString()} top-8 finishes</Text>
          </Group>
        </Card>

        {personalBests.length > 0 && (
          <Card withBorder padding="md" style={{ maxHeight: 400, overflowY: 'auto' }}>
            <Text fw={600} mb="xs">Championship Top-8 Bests</Text>
            <Stack gap={2}>
              {personalBests.map((pb, i) => (
                <Group key={`${pb.discipline}-${pb.gender}-${i}`} justify="space-between" wrap="nowrap">
                  <Group gap="xs" wrap="nowrap">
                    <Text size="sm">{pb.discipline}</Text>
                    {pb.environment && (
                      <Badge size="xs" variant="light" color={pb.environment === 'indoor' ? 'cyan' : 'teal'}>
                        {pb.environment === 'indoor' ? 'I' : 'O'}
                      </Badge>
                    )}
                    <Badge size="xs" variant="light" color={GENDER_COLOR[pb.gender]}>
                      {pb.gender === 'men' ? 'M' : 'W'}
                    </Badge>
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

      {notableAthletes.length > 0 && (
        <Card withBorder padding="md">
          <Text fw={600} mb="xs">Notable Athletes</Text>
          <Stack gap={2}>
            {notableAthletes.map(a => (
              <Group key={a.athlete_id} justify="space-between" wrap="nowrap">
                <Group gap="xs" wrap="nowrap">
                  <Anchor
                    size="sm"
                    onClick={() => onAthleteClick(a.athlete_id)}
                    style={{ cursor: 'pointer' }}
                  >
                    {a.name}
                  </Anchor>
                  <Badge size="xs" variant="light" color={GENDER_COLOR[a.gender]}>
                    {a.gender === 'men' ? 'M' : 'W'}
                  </Badge>
                </Group>
                <Text size="xs" c="dimmed">
                  {a.performances} {a.performances === 1 ? 'perf.' : 'perfs.'} ({a.first_year}{a.first_year !== a.last_year ? `\u2013${a.last_year}` : ''})
                </Text>
              </Group>
            ))}
          </Stack>
        </Card>
      )}

      <div>
        <Title order={4} mb="xs">All Performances</Title>
        <Table.ScrollContainer minWidth={900}>
          <Table striped highlightOnHover withTableBorder>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Year</Table.Th>
                <Table.Th>Env</Table.Th>
                <Table.Th>Gender</Table.Th>
                <Table.Th>Pl</Table.Th>
                <Table.Th>Athlete</Table.Th>
                <Table.Th>Discipline</Table.Th>
                <Table.Th>Mark</Table.Th>
                <Table.Th>Wind</Table.Th>
                <Table.Th>Class</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {pagedResults.map(r => {
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
                    <Table.Td>
                      <Badge size="xs" variant="light" color={GENDER_COLOR[r.gender]}>
                        {r.gender === 'men' ? 'M' : 'W'}
                      </Badge>
                    </Table.Td>
                    <Table.Td>{r.place || '-'}</Table.Td>
                    <Table.Td>
                      <Anchor onClick={() => onAthleteClick(r.athlete_id)} style={{ cursor: 'pointer' }}>
                        {r.name}
                      </Anchor>
                      {r.leg_idx !== null && r.is_relay === 1 && (
                        <Text component="span" size="xs" c="dimmed"> (Leg {r.leg_idx})</Text>
                      )}
                    </Table.Td>
                    <Table.Td>{label}</Table.Td>
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
        {perfTotalPages > 1 && (
          <Group justify="center" mt="md">
            <Pagination
              total={perfTotalPages}
              value={perfPage + 1}
              onChange={(p) => setPerfPage(p - 1)}
            />
          </Group>
        )}
      </div>
    </Stack>
  );
}
