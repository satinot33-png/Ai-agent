export type Role = "SUPER ADMIN" | "ADMIN" | "KARYAWAN";

export type User = {
  user_id?: string;
  name: string;
  username?: string;
  email?: string;
  whatsapp?: string;
  role: Role | string;
  enabled?: boolean;
  allowed_ais?: string[];
  allowed_countries?: string[];
  allowed_provinces?: string[];
  access_start?: string | null;
  access_end?: string | null;
  picture?: string;
  auth_provider?: string;
};

export type AIAgent = {
  agent_id: string;
  name: string;
  function: string;
  enabled: boolean;
  job_status: string;
  last_activity: string;
};

export type Country = {
  code: string;
  name: string;
  region: string;
  enabled: boolean;
};

export type Province = {
  code: string;
  name: string;
  country_code: string;
};

export type ServerState = {
  server_online: boolean;
  domain: string;
  api_online: boolean;
  cpu: number;
  ram: number;
  storage: number;
  uptime: string;
  active_jobs: number;
  successful_jobs: number;
  failed_jobs: number;
  last_error: string;
};

export type ActivityLog = {
  log_id: string;
  actor: string;
  actor_role?: string;
  action: string;
  detail: string;
  created_at: string;
};

export type DashboardData = {
  server: ServerState;
  ais: AIAgent[];
  countries: Country[];
  logs: ActivityLog[];
  user: User;
};

export type InterrogationResult = {
  connection: "OK" | "ERROR";
  api: "OK" | "ERROR";
  database: "OK" | "ERROR" | "WARNING";
  ai: { agent_id: string; name: string; status: "OK" | "WARNING" | "ERROR" }[];
  active_jobs: number;
  successful_jobs: number;
  failed_jobs: number;
  last_error: string;
  checked_at: string;
};
