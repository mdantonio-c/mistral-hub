export interface CustomUser {
  disk_quota: number;
  /**
   * @nullable
   */
  amqp_queue: string;
  /** @nullable */
  requests_expiration_days: number;
  datasets: SimpleDataset[];
}

export interface CodeDescPair {
  code: string;
  /** @nullable */
  desc?: string;
}

export interface Bcode {
  bcode: string;
  description: string;
  /** @nullable */
  short?: string;
  unit: string;
  offset: number;
  scale: number;
  userunit: string;
}

export interface FieldsSummary {
  items: Items | GenericItems;
}

export interface GenericItems {
  // @ts-ignore
  summarystats: SummaryStats;
  // some more fixed keys.
  [key: string]: any[];
}

export interface Items {
  product: any[];
  available_products: any[];
  level?: any[];
  network?: any[];
  timerange?: any[];
  summarystats: SummaryStats;
}

export interface SummaryStats {
  b?: number[];
  e?: number[];
  c: number;
  s: number;
}

export interface StorageUsage {
  quota: number;
  used: number;
}

export interface DerivedVariables {
  code: string;
  desc: string;
}

/**
 * Expected filter names:
 *
 * area
 * level
 * origin
 * proddef
 * product
 * quantity
 * run
 * task
 * timerange
 */
export interface Filters {
  name: string;
  values: any[];
  query: string;
}

export interface SimpleDataset {
  id: string;
  name: string;
}

export interface SimpleGroupLicence {
  id: string;
  name: string;
}

export interface Dataset {
  id: string;
  name: string;
  description?: string;
  category: string;
  format: string;
  bounding?: string;

  // attribution
  attribution?: string;
  attribution_description?: string;
  attribution_url?: string;

  // group of license
  group_license?: string;
  group_license_description?: string;

  // license
  license?: string;
  license_description?: string;
  license_url?: string;

  is_public: boolean;
  authorized: boolean;
}

export interface RefTime {
  from: Date;
  to: Date;
}

export interface TaskSchedule {
  type: ScheduleType;
  time?: string; // hh:mm
  every?: number;
  repeat?: RepeatEvery;
}

export enum RepeatEvery {
  MINUTE = "minute",
  HOUR = "hour",
  DAY = "day",
  WEEK = "week",
  MONTH = "month",
}

export enum ScheduleType {
  CRONTAB = "crontab",
  PERIOD = "period",
  DATA_READY = "data-ready",
}

export interface DateSchedule {
  /** The year, for example 2019 */
  year: number;
  /** The month, for example 1=Jan ... 12=Dec */
  month: number;
  /** The day of month, starting at 1 */
  day: number;
}

export interface TimeSchedule {
  /** The hour in the `[0, 23]` range. */
  hour: number;
  /** The minute in the `[0, 59]` range. */
  minute: number;
}

export interface OnOffSchedule {
  /** Current status of the schedule */
  enabled: boolean;
  /** Schedule ID */
  id: number;
}

export interface Templates {
  files: string[];
  type: string;
}
export interface ObsFilter {
  product: string;
  reftime: Date;
  network?: string;
  timerange?: string;
  level?: string;
  bbox?: BoundingBox;
  onlyStations?: boolean;
}

export interface Network {
  id: number;
  memo: string;
  desc?: string;
}

export interface Product {
  code: string;
  desc?: string;
}

export interface BoundingBox {
  latMin: number;
  lonMin: number;
  latMax: number;
  lonMax: number;
}

export interface Station {
  ident?: string;
  altitude?: string;
  net: string;
  lat: number;
  lon: number;
  details?: StationDetail[];
}

export interface StationDetail {
  var: string;
  val: string;
}

export interface ObsValues {
  // level: string;
  ref: string;
  // timerange: string;
  val: number;
  rel?: number; // 1 or 0
}

export interface ObsData {
  val: ObsValues[];
  var: string;
}

export interface SingleObsData {
  description: string;
  scale: number;
  unit: string;
  val: ObsValues;
  var: string;
}

export interface DescriptionDict {
  [key: string]: DescrItem;
}

export interface DescrItem {
  descr: string;
  unit?: string;
}

export interface Observation {
  stat: Station;
  prod?: ObsData[];
}

export interface ObservationResponse {
  data: Observation[];
  descr: DescriptionDict;
}

export interface DataSeries {
  name: string;
  code: string;
  unit?: string;
  timerange?: string;
  level?: string;
  series: SeriesItem[];
}

export interface SeriesItem {
  name: string; // reftime ISO 8601 e.g. 2020-09-07T00:00:00
  value: any;
}

export interface DataExtractionRequest {
  id: number;
  task_id: string;
  name: string;
  submission_date: string;
  end_date: string;
  status: string;
  fileoutput?: string;
  filesize?: number;
  args: RequestArgs;
}

export interface RequestArgs {
  dataset_names: string[];
  filters?: FiltersArg;
  reftime?: ReftimeArg;
}

export interface FiltersArg {
  [key: string]: any[];
}

export interface ReftimeArg {
  from: string;
  to: string;
}

export interface OpenData {
  date: string;
  run: string;
  filename: string;
}

export interface ExchangeBindings {
  exchange: string;
  bindings: Record<string, string[]>;
}
