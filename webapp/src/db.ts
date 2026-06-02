import initSqlJs, { type Database, type SqlValue, type Statement } from 'sql.js';
import sqlWasm from 'sql.js/dist/sql-wasm.wasm?url';
import type { Result, FilterState, AthleteSummary, AthleteProfileResult, School, SchoolProfileResult, Metadata, Gender, Environment, SortState, EventGroupData, YearRange } from './types';

let db: Database | null = null;
let eventGroups: EventGroupData | null = null;

export async function initDatabase(onProgress?: (pct: number) => void): Promise<void> {
  const SQL = await initSqlJs({
    locateFile: () => sqlWasm
  });

  const response = await fetch(`${import.meta.env.BASE_URL}ncaa_history.db`);
  const contentLength = Number(response.headers.get('Content-Length')) || 0;
  const reader = response.body?.getReader();
  let received = 0;
  const chunks: Uint8Array[] = [];

  if (reader && contentLength > 0) {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
      received += value.length;
      onProgress?.(Math.round((received / contentLength) * 100));
    }
    const combined = new Uint8Array(received);
    let offset = 0;
    for (const chunk of chunks) {
      combined.set(chunk, offset);
      offset += chunk.length;
    }
    db = new SQL.Database(combined);
  } else {
    const arrayBuffer = await response.arrayBuffer();
    db = new SQL.Database(new Uint8Array(arrayBuffer));
  }
}

export async function loadEventGroups(): Promise<void> {
  const response = await fetch(`${import.meta.env.BASE_URL}event_groups.json`);
  eventGroups = await response.json() as EventGroupData;
}

export function getEventGroups(): EventGroupData {
  if (!eventGroups) throw new Error('Event groups not loaded');
  return eventGroups;
}

function yearInRange(year: number, ranges: YearRange[] | null): boolean {
  if (!ranges) return false;
  return ranges.some(([start, end]) => {
    const e = end ?? Infinity;
    return year >= start && year <= e;
  });
}

export function getVariantName(
  discipline: string,
  year: number,
  gender: Gender,
  environment: Environment | null
): string | null {
  if (!eventGroups || !environment) return null;
  const groups = environment === 'indoor' ? eventGroups.indoor : eventGroups.outdoor;
  const group = groups.find(g => g.discipline === discipline);
  if (!group) return null;
  const genderKey = gender === 'men' ? 'men' : 'women';
  const variant = group.variants.find(v => yearInRange(year, v[genderKey]));
  return variant?.name ?? null;
}

function rowToResult(row: SqlValue[]): Result {
  const str = (v: SqlValue) => v as string;
  const num = (v: SqlValue) => v as number | null;
  const strNull = (v: SqlValue) => v as string | null;
  
  return {
    id: row[0] as number,
    year: row[1] as number,
    date: strNull(row[2]),
    name: str(row[3]),
    school: strNull(row[4]),
    discipline: str(row[5]),
    wind: num(row[6]),
    gender: str(row[7]) as Gender,
    mark_num: num(row[8]),
    mark_str: strNull(row[9]),
    class: strNull(row[10]) as Result['class'],
    place: num(row[11]),
    is_dq: row[12] as number,
    is_dnf: row[13] as number,
    is_dns: row[14] as number,
    is_wind_aided: row[15] as number,
    is_international: row[16] as number,
    split_time: strNull(row[17]),
    leg_idx: num(row[18]),
    is_relay: row[19] as number,
    is_converted: row[20] as number,
    location: strNull(row[21]),
    notes: strNull(row[22]),
    source_url: strNull(row[23]),
    environment: str(row[24]) as Environment | null,
    school_id: num(row[25]),
    athlete_id: num(row[26]),
  };
}

function runStatement(stmt: Statement, params: SqlValue[]): SqlValue[][] {
  stmt.bind(params);
  const results: SqlValue[][] = [];
  while (stmt.step()) {
    results.push(stmt.get());
  }
  stmt.reset();
  return results;
}

export function getResults(filters: FilterState, sort: SortState, limit: number = 100, offset: number = 0): Result[] {
  if (!db) throw new Error('Database not initialized');
  
  const conditions: string[] = [];
  const params: SqlValue[] = [];
  
  if (filters.year !== null) {
    conditions.push('year = ?');
    params.push(filters.year);
  }
  if (filters.gender) {
    conditions.push('gender = ?');
    params.push(filters.gender);
  }
  if (filters.discipline) {
    conditions.push('discipline = ?');
    params.push(filters.discipline);
  }
  if (filters.environment) {
    conditions.push('environment = ?');
    params.push(filters.environment);
  }
  if (filters.school) {
    conditions.push('school = ?');
    params.push(filters.school);
  }
  if (filters.name) {
    conditions.push('name = ? COLLATE NOCASE');
    params.push(filters.name);
  }
  
  const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
  
  const sortDir = sort.direction === 'asc' ? 'ASC' : 'DESC';
  
  let orderBy: string;
  switch (sort.column) {
    case 'mark_num':
      orderBy = `mark_num ${sortDir} NULLS LAST, year DESC, gender, discipline, place, leg_idx`;
      break;
    case 'place':
      orderBy = `place ${sortDir} NULLS LAST, year DESC, gender, discipline, leg_idx`;
      break;
    case 'name':
      orderBy = `name ${sortDir}, year DESC, gender, discipline, place, leg_idx`;
      break;
    case 'school':
      orderBy = `school ${sortDir} NULLS LAST, year DESC, gender, discipline, place, leg_idx`;
      break;
    case 'split_time':
      orderBy = `CASE WHEN split_time LIKE '%:%' THEN CAST(SUBSTR(split_time, 1, INSTR(split_time, ':') - 1) AS REAL) * 60 + CAST(SUBSTR(split_time, INSTR(split_time, ':') + 1) AS REAL) WHEN split_time IS NOT NULL THEN CAST(split_time AS REAL) END ${sortDir} NULLS LAST, year DESC, gender, discipline, place, leg_idx`;
      break;
    case 'year':
    default:
      orderBy = `year ${sortDir}, gender, discipline, place, leg_idx`;
      break;
  }
  
  const sql = `
    SELECT * FROM results 
    ${whereClause}
    ORDER BY ${orderBy}
    LIMIT ? OFFSET ?
  `;
  params.push(limit, offset);
  
  const stmt = db.prepare(sql);
  const rows = runStatement(stmt, params);
  
  return rows.map(rowToResult);
}

export function getResultCount(filters: FilterState): number {
  if (!db) throw new Error('Database not initialized');
  
  const conditions: string[] = [];
  const params: SqlValue[] = [];
  
  if (filters.year !== null) {
    conditions.push('year = ?');
    params.push(filters.year);
  }
  if (filters.gender) {
    conditions.push('gender = ?');
    params.push(filters.gender);
  }
  if (filters.discipline) {
    conditions.push('discipline = ?');
    params.push(filters.discipline);
  }
  if (filters.environment) {
    conditions.push('environment = ?');
    params.push(filters.environment);
  }
  if (filters.school) {
    conditions.push('school = ?');
    params.push(filters.school);
  }
  if (filters.name) {
    conditions.push('name = ? COLLATE NOCASE');
    params.push(filters.name);
  }
  
  const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
  
  const sql = `SELECT COUNT(*) FROM results ${whereClause}`;
  const stmt = db.prepare(sql);
  const rows = runStatement(stmt, params);
  
  return rows[0]?.[0] as number || 0;
}

export function getAthletes(): AthleteSummary[] {
  if (!db) throw new Error('Database not initialized');
  
  const sql = `
    SELECT name, gender, COUNT(*) as performances, MIN(year) as first_year, MAX(year) as last_year
    FROM results 
    GROUP BY name, gender
    ORDER BY name
  `;
  
  const stmt = db.prepare(sql);
  const rows = runStatement(stmt, []);
  
  return rows.map(row => ({
    name: row[0] as string,
    gender: row[1] as Gender,
    performances: row[2] as number,
    first_year: row[3] as number,
    last_year: row[4] as number,
  }));
}

export function getAllSchools(): School[] {
  if (!db) throw new Error('Database not initialized');

  const sql = `SELECT school_id, name, qid, athletics_qid, category_qid, label, description, enwiki, athletics_enwiki, category_enwiki, men_nickname, women_nickname FROM schools ORDER BY name`;

  const stmt = db.prepare(sql);
  const rows = runStatement(stmt, []);

  return rows.map(row => ({
    school_id: row[0] as number,
    name: row[1] as string,
    qid: row[2] as string | null,
    athletics_qid: row[3] as string | null,
    category_qid: row[4] as string | null,
    label: row[5] as string | null,
    description: row[6] as string | null,
    enwiki: row[7] as string | null,
    athletics_enwiki: row[8] as string | null,
    category_enwiki: row[9] as string | null,
    men_nickname: row[10] as string | null,
    women_nickname: row[11] as string | null,
  }));
}

export function getSchoolById(schoolId: number): School | null {
  if (!db) throw new Error('Database not initialized');

  const sql = `SELECT school_id, name, qid, athletics_qid, category_qid, label, description, enwiki, athletics_enwiki, category_enwiki, men_nickname, women_nickname FROM schools WHERE school_id = ?`;

  const stmt = db.prepare(sql);
  const rows = runStatement(stmt, [schoolId]);

  if (rows.length === 0) return null;
  const row = rows[0];
  return {
    school_id: row[0] as number,
    name: row[1] as string,
    qid: row[2] as string | null,
    athletics_qid: row[3] as string | null,
    category_qid: row[4] as string | null,
    label: row[5] as string | null,
    description: row[6] as string | null,
    enwiki: row[7] as string | null,
    athletics_enwiki: row[8] as string | null,
    category_enwiki: row[9] as string | null,
    men_nickname: row[10] as string | null,
    women_nickname: row[11] as string | null,
  };
}

export function getSchoolByName(schoolName: string): School | null {
  if (!db) throw new Error('Database not initialized');

  const sql = `SELECT school_id, name, qid, athletics_qid, category_qid, label, description, enwiki, athletics_enwiki, category_enwiki, men_nickname, women_nickname FROM schools WHERE name = ?`;

  const stmt = db.prepare(sql);
  const rows = runStatement(stmt, [schoolName]);

  if (rows.length === 0) return null;
  const row = rows[0];
  return {
    school_id: row[0] as number,
    name: row[1] as string,
    qid: row[2] as string | null,
    athletics_qid: row[3] as string | null,
    category_qid: row[4] as string | null,
    label: row[5] as string | null,
    description: row[6] as string | null,
    enwiki: row[7] as string | null,
    athletics_enwiki: row[8] as string | null,
    category_enwiki: row[9] as string | null,
    men_nickname: row[10] as string | null,
    women_nickname: row[11] as string | null,
  };
}

export function getResultsBySchoolId(schoolId: number): Result[] {
  if (!db) throw new Error('Database not initialized');

  const sql = `
    SELECT * FROM results
    WHERE school_id = ?
    ORDER BY year DESC, environment, discipline, place, leg_idx
  `;

  const stmt = db.prepare(sql);
  const rows = runStatement(stmt, [schoolId]);

  return rows.map(rowToResult);
}

export function getResultsByAthleteId(athleteId: number): Result[] {
  if (!db) throw new Error('Database not initialized');

  const sql = `
    SELECT * FROM results
    WHERE athlete_id = ?
    ORDER BY year DESC, environment, discipline, place, leg_idx
  `;

  const stmt = db.prepare(sql);
  const rows = runStatement(stmt, [athleteId]);

  return rows.map(rowToResult);
}

export function getMetadata(): Metadata {
  if (!db) throw new Error('Database not initialized');
  if (!eventGroups) throw new Error('Event groups not loaded');
  
  const yearsStmt = db.prepare('SELECT DISTINCT year FROM results ORDER BY year');
  const yearsRows = runStatement(yearsStmt, []);
  const years = yearsRows.map(r => r[0] as number);
  
  const locationsStmt = db.prepare('SELECT DISTINCT location FROM results WHERE location IS NOT NULL ORDER BY location');
  const locationsRows = runStatement(locationsStmt, []);
  const locations = locationsRows.map(r => r[0] as string);
  
  return {
    years,
    locations,
    environments: ['indoor', 'outdoor'],
    genders: ['men', 'women'],
    eventGroups,
  };
}

export function searchAthletes(query: string): AthleteProfileResult[] {
  if (!db) throw new Error('Database not initialized');

  const sql = `
    SELECT athlete_id, MIN(name) as name, GROUP_CONCAT(DISTINCT school) as schools, gender, COUNT(*) as performances, MIN(year) as first_year, MAX(year) as last_year
    FROM results 
    WHERE athlete_id IN (
      SELECT DISTINCT athlete_id FROM results WHERE name LIKE ?
    )
    GROUP BY athlete_id, gender
    ORDER BY name
    LIMIT 50
  `;

  const stmt = db.prepare(sql);
  const rows = runStatement(stmt, [`%${query}%`]);

  return rows.map(row => ({
    athlete_id: row[0] as number | null,
    name: row[1] as string,
    schools: (row[2] as string).split(',').filter(Boolean),
    gender: row[3] as Gender,
    performances: row[4] as number,
    first_year: row[5] as number,
    last_year: row[6] as number,
  }));
}

export function searchSchools(query: string): SchoolProfileResult[] {
  if (!db) throw new Error('Database not initialized');

  const sql = `
    SELECT s.school_id, s.name, s.label, s.description, s.men_nickname, s.women_nickname,
           s.enwiki, s.athletics_enwiki, s.category_enwiki,
           COUNT(*) as performances, COUNT(DISTINCT r.year) as years,
           MIN(r.year) as first_year, MAX(r.year) as last_year
    FROM results r
    JOIN schools s ON r.school_id = s.school_id
    WHERE s.name LIKE ? OR s.label LIKE ? OR s.men_nickname LIKE ? OR s.women_nickname LIKE ?
    GROUP BY s.school_id
    ORDER BY performances DESC
    LIMIT 50
  `;

  const like = `%${query}%`;
  const stmt = db.prepare(sql);
  const rows = runStatement(stmt, [like, like, like, like]);

  return rows.map(row => ({
    school_id: row[0] as number,
    name: row[1] as string,
    label: row[2] as string | null,
    description: row[3] as string | null,
    men_nickname: row[4] as string | null,
    women_nickname: row[5] as string | null,
    enwiki: row[6] as string | null,
    athletics_enwiki: row[7] as string | null,
    category_enwiki: row[8] as string | null,
    performances: row[9] as number,
    years: row[10] as number,
    first_year: row[11] as number,
    last_year: row[12] as number,
  }));
}
