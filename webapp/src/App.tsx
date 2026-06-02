import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  Container, Title, Text, Group, Tabs, Pagination, Progress, Breadcrumbs,
  Anchor, Stack, Alert, Loader, ActionIcon,
} from '@mantine/core';
import { useMantineColorScheme } from '@mantine/core';
import { SunIcon, MoonIcon, EnvelopeIcon } from '@phosphor-icons/react';
import { initDatabase, loadEventGroups, getResults, getResultCount, getMetadata, getResultsByAthleteId, getResultsBySchoolId, getAllSchools } from './db';
import { ResultTable } from './components/ResultTable';
import { Filters } from './components/Filters';
import { SearchPanel } from './components/SearchPanel';
import { AthleteProfile } from './components/AthleteProfile';
import { CollegeProfile } from './components/CollegeProfile';
import type { FilterState, Metadata, SortState, SortColumn, Profile, Result, School } from './types';

function ColorSchemeToggle() {
  const { colorScheme, toggleColorScheme } = useMantineColorScheme();
  return (
    <ActionIcon
      onClick={toggleColorScheme}
      variant="subtle"
      size="lg"
      title={colorScheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {colorScheme === 'dark' ? <SunIcon size={20} /> : <MoonIcon size={20} />}
    </ActionIcon>
  );
}

const PAGE_SIZE = 100;

type ViewMode = 'browse' | 'search' | 'profile' | 'school-profile';

function parseProfileHash(): number | null {
  const hash = window.location.hash;
  const match = hash.match(/^#athlete-(\d+)$/);
  return match ? parseInt(match[1], 10) : null;
}

function parseSchoolHash(): number | null {
  const hash = window.location.hash;
  const match = hash.match(/^#school-(\d+)$/);
  return match ? parseInt(match[1], 10) : null;
}

function App() {
  const [loading, setLoading] = useState(true);
  const [loadProgress, setLoadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<Metadata | null>(null);

  const [viewMode, setViewMode] = useState<ViewMode>('browse');
  const [tabValue, setTabValue] = useState<string>('browse');
  const [filters, setFilters] = useState<FilterState>({
    year: null,
    gender: null,
    discipline: null,
    environment: null,
    school: null,
    name: null,
  });

  const [sort, setSort] = useState<SortState>({
    column: 'year',
    direction: 'desc',
  });

  const [results, setResults] = useState<Result[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(0);
  const [profiles, setProfiles] = useState<Profile[]>([]);

  const [selectedAthleteId, setSelectedAthleteId] = useState<number | null>(null);
  const [profileResults, setProfileResults] = useState<Result[]>([]);
  const savedBrowseState = useRef<{ filters: FilterState; sort: SortState; page: number } | null>(null);

  const [selectedSchoolId, setSelectedSchoolId] = useState<number | null>(null);
  const [schoolProfileResults, setSchoolProfileResults] = useState<Result[]>([]);
  const [schoolsCache, setSchoolsCache] = useState<School[]>([]);

  const profilesMap = useMemo(() => {
    const map = new Map<number, Profile>();
    for (const p of profiles) {
      map.set(p.athlete_id, p);
    }
    return map;
  }, [profiles]);

  const findProfile = useCallback((athleteId: number): Profile | undefined => {
    return profilesMap.get(athleteId);
  }, [profilesMap]);

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}profiles.json`)
      .then(r => r.json())
      .then(setProfiles)
      .catch(() => {});
  }, []);

  useEffect(() => {
    Promise.all([initDatabase(setLoadProgress), loadEventGroups()])
      .then(() => {
        const meta = getMetadata();
        setMetadata(meta);
        setSchoolsCache(getAllSchools());
        const hashId = parseProfileHash();
        const schoolHashId = parseSchoolHash();
        if (hashId) {
          setSelectedAthleteId(hashId);
          setViewMode('profile');
        } else if (schoolHashId) {
          setSelectedSchoolId(schoolHashId);
          setViewMode('school-profile');
        }
        setLoading(false);
      })
      .catch((err) => {
        setError(`Failed to load database: ${err.message}`);
        setLoading(false);
      });
  }, []);

  const handleBackFromProfile = useCallback(() => {
    setViewMode('browse');
    setTabValue('browse');
    setSelectedAthleteId(null);
    setSelectedSchoolId(null);
    setProfileResults([]);
    setSchoolProfileResults([]);
    window.location.hash = '';
    if (savedBrowseState.current) {
      const { filters: sf, sort: ss, page: sp } = savedBrowseState.current;
      setFilters(sf);
      setSort(ss);
      setPage(sp);
      savedBrowseState.current = null;
    }
  }, []);

  useEffect(() => {
    const handleHash = () => {
      const hashId = parseProfileHash();
      const schoolHashId = parseSchoolHash();
      if (hashId != null) {
        setSelectedAthleteId(hashId);
        setViewMode('profile');
      } else if (schoolHashId != null) {
        setSelectedSchoolId(schoolHashId);
        setViewMode('school-profile');
      } else if (viewMode === 'profile' || viewMode === 'school-profile') {
        handleBackFromProfile();
      }
    };
    window.addEventListener('hashchange', handleHash);
    return () => window.removeEventListener('hashchange', handleHash);
  }, [viewMode, handleBackFromProfile]);

  const loadResults = useCallback((f: FilterState, s: SortState, p: number) => {
    const offset = p * PAGE_SIZE;
    const data = getResults(f, s, PAGE_SIZE, offset);
    const count = getResultCount(f);
    setResults(data);
    setTotalCount(count);
  }, []);

  useEffect(() => {
    if (metadata && viewMode !== 'profile' && viewMode !== 'school-profile') {
      loadResults(filters, sort, page);
    }
  }, [filters, sort, page, metadata, loadResults, viewMode]);

  const handleFilterChange = (newFilters: FilterState) => {
    setFilters(newFilters);
    setPage(0);
  };

  const handleSortChange = (column: SortColumn) => {
    setSort(prev => ({
      column,
      direction: prev.column === column && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
    setPage(0);
  };

  const handleAthleteClick = (athleteId: number | null) => {
    if (athleteId == null) return;
    savedBrowseState.current = { filters, sort, page };
    setSelectedAthleteId(athleteId);
    setViewMode('profile');
    window.location.hash = `athlete-${athleteId}`;
  };

  useEffect(() => {
    if (viewMode === 'profile' && selectedAthleteId != null && metadata) {
      const data = getResultsByAthleteId(selectedAthleteId);
      setProfileResults(data);
    }
  }, [viewMode, selectedAthleteId, metadata]);

  useEffect(() => {
    if (viewMode === 'school-profile' && selectedSchoolId != null && metadata) {
      const data = getResultsBySchoolId(selectedSchoolId);
      setSchoolProfileResults(data);
    }
  }, [viewMode, selectedSchoolId, metadata]);

  const handleSchoolProfileClick = useCallback((schoolId: number | null) => {
    if (schoolId == null) return;
    savedBrowseState.current = { filters, sort, page };
    setSelectedSchoolId(schoolId);
    setViewMode('school-profile');
    window.location.hash = `school-${schoolId}`;
  }, [filters, sort, page]);

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  const handleTabChange = useCallback((value: string | null) => {
    if (value === 'browse') {
      setViewMode('browse');
    } else if (value === 'search') {
      setViewMode('search');
    }
    setTabValue(value ?? 'browse');
  }, []);

  if (loading) {
    return (
      <Container size="xl" py="xl">
        <Stack align="center" gap="md">
          <Loader size="lg" />
          <Text c="dimmed">Loading database... (should take less than a minute)</Text>
          {loadProgress > 0 && loadProgress < 100 && (
            <Progress value={loadProgress} w={300} size="lg" />
          )}
        </Stack>
      </Container>
    );
  }

  if (error) {
    return (
      <Container size="xl" py="xl">
        <Alert color="red" title="Error">{error}</Alert>
      </Container>
    );
  }

  const currentProfile = selectedAthleteId != null ? findProfile(selectedAthleteId) : undefined;

  return (
    <Container size="xl" py="md">
      <Group justify="space-between" align="center" mb={4}>
        <Title order={2} style={{ letterSpacing: '-0.02em' }}>
          NCAA<span style={{ opacity: 0.5 }}>db</span>
        </Title>
        <ColorSchemeToggle />
      </Group>
      <Text c="dimmed" mb="lg" size="sm">
        Listing all known top-8 finishers at NCAA Division I indoor and outdoor track and field championships. Spot an error? Want to use the data?{' '}
        <Anchor href="mailto:habs@sdf.org" inherit>
          <EnvelopeIcon size={14} style={{ verticalAlign: '-2px', marginRight: 2 }} />
          Contact me
        </Anchor>
      </Text>

      {viewMode === 'profile' && currentProfile ? (
        <AthleteProfile
          profile={currentProfile}
          results={profileResults}
          onBack={handleBackFromProfile}
          onSchoolClick={handleSchoolProfileClick}
          metadata={metadata}
          profilesMap={profilesMap}
        />
      ) : viewMode === 'school-profile' && selectedSchoolId != null ? (
        <CollegeProfile
          school={schoolsCache.find(s => s.school_id === selectedSchoolId)!}
          results={schoolProfileResults}
          onBack={handleBackFromProfile}
          onAthleteClick={handleAthleteClick}
          metadata={metadata}
        />
      ) : (
        <>
          <Tabs value={tabValue} onChange={handleTabChange} mb="md">
            <Tabs.List>
              <Tabs.Tab value="browse">Browse</Tabs.Tab>
              <Tabs.Tab value="search">Search</Tabs.Tab>
            </Tabs.List>
          </Tabs>

          {viewMode === 'search' && (
            <SearchPanel
              onAthleteSelect={handleAthleteClick}
              onSchoolSelect={handleSchoolProfileClick}
              profilesMap={profilesMap}
            />
          )}

          {viewMode === 'browse' && metadata && (
            <>
              <Filters
                filters={filters}
                metadata={metadata}
                schools={schoolsCache}
                count={totalCount}
                onChange={handleFilterChange}
              />

              {(filters.name || filters.school) && (
                <Breadcrumbs mb="md" mt="xs">
                  <Anchor
                    onClick={() => handleFilterChange({ ...filters, name: null, school: null })}
                  >
                    All Results
                  </Anchor>
                  {filters.name && <Text fw={500}>Athlete: {filters.name}</Text>}
                  {filters.school && <Text fw={500}>School: {filters.school}</Text>}
                </Breadcrumbs>
              )}

              <ResultTable
                results={results}
                sort={sort}
                onSortChange={handleSortChange}
                onAthleteClick={handleAthleteClick}
                onSchoolClick={handleSchoolProfileClick}
                metadata={metadata}
                profilesMap={profilesMap}
              />

              {totalPages > 1 && (
                <Group justify="center" mt="md">
                  <Pagination
                    total={totalPages}
                    value={page + 1}
                    onChange={(p) => setPage(p - 1)}
                  />
                </Group>
              )}
            </>
          )}
        </>
      )}
    </Container>
  );
}

export default App;
