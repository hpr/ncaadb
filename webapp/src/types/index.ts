export interface Result {
  id: number;
  year: number;
  date: string | null;
  name: string;
  school: string | null;
  discipline: string;
  wind: number | null;
  gender: Gender;
  mark_num: number | null;
  mark_str: string | null;
  class: AthleteClass | null;
  place: number | null;
  is_dq: number;
  is_dnf: number;
  is_dns: number;
  is_wind_aided: number;
  is_international: number;
  split_time: string | null;
  leg_idx: number | null;
  is_relay: number;
  is_converted: number;
  location: string | null;
  notes: string | null;
  environment: Environment | null;
  source_url: string | null;
  athlete_id: number | null;
  school_id: number | null;
}

export type Gender = 'men' | 'women';

export const GENDER_COLOR: Record<Gender, string> = { men: 'teal', women: 'violet' };
export type Environment = 'indoor' | 'outdoor';
export type AthleteClass = 'freshman' | 'sophomore' | 'junior' | 'senior';

export interface FilterState {
  year: number | null;
  gender: Gender | null;
  discipline: string | null;
  environment: Environment | null;
  school: string | null;
  name: string | null;
}

export type SortColumn = 'year' | 'place' | 'mark_num' | 'name' | 'school' | 'split_time';
export type SortDirection = 'asc' | 'desc';

export interface SortState {
  column: SortColumn;
  direction: SortDirection;
}

export interface AthleteSummary {
  name: string;
  gender: Gender;
  performances: number;
  first_year: number;
  last_year: number;
}

export interface AthleteProfileResult {
  athlete_id: number | null;
  name: string;
  schools: string[];
  gender: Gender;
  performances: number;
  first_year: number;
  last_year: number;
}

export interface Profile {
  athlete_id: number;
  canonical_name: string;
  aliases: string[];
  members: Array<{
    name: string;
    gender: string;
    school: string;
    year_start: number;
    year_end: number;
  }>;
  qid?: string | null;
}

export interface School {
  school_id: number;
  name: string;
  qid: string | null;
  athletics_qid: string | null;
  category_qid: string | null;
  label: string | null;
  description: string | null;
  enwiki: string | null;
  athletics_enwiki: string | null;
  category_enwiki: string | null;
  men_nickname: string | null;
  women_nickname: string | null;
}

export interface SchoolProfileResult {
  school_id: number;
  name: string;
  label: string | null;
  description: string | null;
  men_nickname: string | null;
  women_nickname: string | null;
  enwiki: string | null;
  athletics_enwiki: string | null;
  category_enwiki: string | null;
  performances: number;
  years: number;
  first_year: number;
  last_year: number;
}

export type YearRange = [number, number | null];

export interface EventGroupVariant {
  name: string;
  men: YearRange[] | null;
  women: YearRange[] | null;
}

export interface EventGroup {
  discipline: string;
  label: string;
  variants: EventGroupVariant[];
}

export interface EventGroupData {
  outdoor: EventGroup[];
  indoor: EventGroup[];
}

export interface RelayTeamMember {
  name: string;
  athlete_id: number | null;
  leg_idx: number | null;
  split_time: string | null;
}

export interface Metadata {
  years: number[];
  locations: string[];
  environments: Environment[];
  genders: Gender[];
  eventGroups: EventGroupData;
}
