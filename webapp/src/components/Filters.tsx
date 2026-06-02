import { Group, Select, TextInput, Button, Text, Grid } from '@mantine/core';
import { MagnifyingGlassIcon } from '@phosphor-icons/react';
import type { FilterState, Gender, Environment, Metadata, EventGroup, School } from '../types';

interface FiltersProps {
  filters: FilterState;
  metadata: Metadata;
  schools: School[];
  count: number;
  onChange: (filters: FilterState) => void;
}

function getDisciplineOptions(
  eventGroups: Metadata['eventGroups'],
  environment: Environment | null
): EventGroup[] {
  if (environment === 'indoor') return eventGroups.indoor;
  if (environment === 'outdoor') return eventGroups.outdoor;
  const seen = new Set<string>();
  const merged: EventGroup[] = [];
  for (const g of [...eventGroups.outdoor, ...eventGroups.indoor]) {
    if (!seen.has(g.discipline)) {
      seen.add(g.discipline);
      merged.push(g);
    }
  }
  return merged;
}

export function Filters({ filters, metadata, schools, count, onChange }: FiltersProps) {
  const updateFilter = <K extends keyof FilterState>(key: K, value: FilterState[K]) => {
    const next = { ...filters, [key]: value };
    if (key === 'environment') {
      const opts = getDisciplineOptions(metadata.eventGroups, value as Environment | null);
      if (next.discipline && !opts.some(g => g.discipline === next.discipline)) {
        next.discipline = null;
      }
    }
    onChange(next);
  };

  const clearFilters = () => {
    onChange({
      year: null,
      gender: null,
      discipline: null,
      environment: null,
      school: null,
      name: null,
    });
  };

  const disciplineOptions = getDisciplineOptions(metadata.eventGroups, filters.environment);

  return (
    <div>
      <Grid align="flex-end" mb="xs">
        <Grid.Col span={{ base: 6, md: 2 }}>
          <Select
            label="Environment"
            placeholder="All"
            clearable
            size="xs"
            data={metadata.environments.map(env => ({
              value: env,
              label: env.charAt(0).toUpperCase() + env.slice(1),
            }))}
            value={filters.environment}
            onChange={(v) => updateFilter('environment', (v as Environment) || null)}
          />
        </Grid.Col>
        <Grid.Col span={{ base: 6, md: 2 }}>
          <Select
            label="Gender"
            placeholder="All"
            clearable
            size="xs"
            data={metadata.genders.map(g => ({
              value: g,
              label: g.charAt(0).toUpperCase() + g.slice(1),
            }))}
            value={filters.gender}
            onChange={(v) => updateFilter('gender', (v as Gender) || null)}
          />
        </Grid.Col>
        <Grid.Col span={{ base: 6, md: 2 }}>
          <Select
            label="Year"
            placeholder="All"
            clearable
            size="xs"
            data={metadata.years.map(y => ({ value: String(y), label: String(y) }))}
            value={filters.year != null ? String(filters.year) : null}
            onChange={(v) => updateFilter('year', v ? parseInt(v) : null)}
          />
        </Grid.Col>
        <Grid.Col span={{ base: 6, md: 3 }}>
          <Select
            label="Discipline"
            placeholder="All"
            clearable
            searchable
            size="xs"
            data={disciplineOptions.map(g => ({
              value: g.discipline,
              label: g.label,
            }))}
            value={filters.discipline}
            onChange={(v) => updateFilter('discipline', v || null)}
          />
        </Grid.Col>
        <Grid.Col span={{ base: 6, md: 3 }}>
          <Select
            label="School"
            placeholder="All"
            clearable
            searchable
            size="xs"
            data={schools.map(s => ({
              value: s.name,
              label: s.name,
            }))}
            value={filters.school}
            onChange={(v) => updateFilter('school', v || null)}
          />
        </Grid.Col>
        <Grid.Col span={{ base: 6, md: 3 }}>
          <TextInput
            label="Athlete (Exact match)"
            placeholder="Filter by name..."
            size="xs"
            leftSection={<MagnifyingGlassIcon size={14} />}
            value={filters.name || ''}
            onChange={(e) => updateFilter('name', e.currentTarget.value || null)}
          />
        </Grid.Col>
         <Grid.Col span={{ base: 12, md: 'auto' }}>
           <Group h="100%" align="center" gap="md" pt={18}>
             <Button variant="subtle" size="xs" onClick={clearFilters}>Clear</Button>
            <Text size="xs" c="dimmed">{count.toLocaleString()} results</Text>
          </Group>
        </Grid.Col>
      </Grid>
    </div>
  );
}
