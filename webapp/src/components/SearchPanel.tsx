import { useState, useEffect, useCallback } from 'react';
import {
  TextInput, Tabs, Paper, Text, Group, Stack, Badge,
} from '@mantine/core';
import { MagnifyingGlassIcon } from '@phosphor-icons/react';
import { useDebouncedCallback } from '@mantine/hooks';
import type { AthleteProfileResult, SchoolProfileResult, Profile } from '../types';
import { GENDER_COLOR } from '../types';
import { searchAthletes, searchSchools } from '../db';

interface SearchPanelProps {
  onAthleteSelect: (athleteId: number | null) => void;
  onSchoolSelect: (schoolId: number | null) => void;
  profilesMap: Map<number, Profile>;
}

export function SearchPanel({ onAthleteSelect, onSchoolSelect, profilesMap }: SearchPanelProps) {
  const [mode, setMode] = useState<string>('athletes');
  const [query, setQuery] = useState('');
  const [athleteResults, setAthleteResults] = useState<AthleteProfileResult[]>([]);
  const [schoolResults, setSchoolResults] = useState<SchoolProfileResult[]>([]);

  const doSearch = useCallback((q: string, m: string) => {
    if (q.length === 0) {
      setAthleteResults([]);
      setSchoolResults([]);
      return;
    }
    if (m === 'athletes') {
      setAthleteResults(searchAthletes(q));
    } else {
      setSchoolResults(searchSchools(q));
    }
  }, []);

  const debouncedSearch = useDebouncedCallback(doSearch, 200);

  useEffect(() => {
    debouncedSearch(query, mode);
  }, [query, mode, debouncedSearch]);

  const handleAthleteSelect = (item: AthleteProfileResult) => {
    onAthleteSelect(item.athlete_id);
    setQuery('');
    setAthleteResults([]);
  };

  const handleSchoolSelect = (item: SchoolProfileResult) => {
    onSchoolSelect(item.school_id);
    setQuery('');
    setSchoolResults([]);
  };

  return (
    <div>
      <Tabs value={mode} onChange={(v) => { setMode(v ?? 'athletes'); setQuery(''); }} mb="sm">
        <Tabs.List>
          <Tabs.Tab value="athletes">Athletes</Tabs.Tab>
          <Tabs.Tab value="schools">Schools</Tabs.Tab>
        </Tabs.List>
      </Tabs>

      <TextInput
        placeholder={`Search ${mode}...`}
        value={query}
        onChange={(e) => setQuery(e.currentTarget.value)}
        leftSection={<MagnifyingGlassIcon size={16} />}
        mb="md"
      />

      <Stack gap="xs">
        {mode === 'athletes' && athleteResults.map((item, idx) => {
          const profile = item.athlete_id != null ? profilesMap.get(item.athlete_id) : undefined;
          const displayName = profile?.canonical_name ?? item.name;
          return (
            <Paper
              key={`${item.athlete_id}-${item.name}-${idx}`}
              p="xs"
              withBorder
              style={{ cursor: 'pointer' }}
              onClick={() => handleAthleteSelect(item)}
            >
              <Group justify="space-between">
                <Group gap="xs">
                  <Text fw={500} size="sm">{displayName}</Text>
                  <Badge size="xs" variant="light" color={GENDER_COLOR[item.gender]}>
                    {item.gender === 'men' ? 'M' : 'W'}
                  </Badge>
                  {item.schools.length > 0 && (
                    <Text size="xs" c="dimmed">{item.schools.join(' / ')}</Text>
                  )}
                </Group>
                <Text size="xs" c="dimmed">
                  {item.performances} {item.performances === 1 ? 'perf.' : 'perfs.'} ({item.first_year}{item.first_year !== item.last_year ? `\u2013${item.last_year}` : ''})
                </Text>
              </Group>
            </Paper>
          );
        })}
        {mode === 'schools' && schoolResults.map((item, idx) => {
          const nicknames: string[] = [];
          if (item.men_nickname && item.men_nickname === item.women_nickname) {
            nicknames.push(item.men_nickname);
          } else {
            if (item.men_nickname) nicknames.push(item.men_nickname);
            if (item.women_nickname) nicknames.push(item.women_nickname);
          }
          return (
            <Paper
              key={`${item.school_id}-${idx}`}
              p="xs"
              withBorder
              style={{ cursor: 'pointer' }}
              onClick={() => handleSchoolSelect(item)}
            >
              <Group justify="space-between">
                <Group gap="xs">
                  <Text fw={500} size="sm">{item.name}</Text>
                  {nicknames.length > 0 && (
                    <Badge size="xs" variant="outline" tt="none">{nicknames.join(' / ')}</Badge>
                  )}
                </Group>
                <Text size="xs" c="dimmed">
                  {item.performances.toLocaleString()} {item.performances === 1 ? 'perf.' : 'perfs.'}, {item.years} {item.years === 1 ? 'yr' : 'yrs'}
                </Text>
              </Group>
            </Paper>
          );
        })}
      </Stack>
    </div>
  );
}
