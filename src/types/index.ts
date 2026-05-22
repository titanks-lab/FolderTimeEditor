export interface FileTimes {
  creation_time: number | null;
  last_write_time: number | null;
  last_access_time: number | null;
}

export interface FileInfo {
  name: string;
  path: string;
  is_dir: boolean;
  size: number;
  creation_time: number | null;
  last_write_time: number | null;
  last_access_time: number | null;
  owner: string;
}

export interface TimeSetting {
  enabled: boolean;
  date: string;     // '2026-05-21'
  time: string;     // '14:30'
}

export interface PreviewChange {
  path: string;
  attribute: string;
  old_value: string;
  new_value: string;
}

export interface AppSettings {
  creation: TimeSetting;
  modification: TimeSetting;
  access: TimeSetting;
  sync: boolean;
  owner_enabled: boolean;
  owner: string;
}
