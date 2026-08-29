// Role & permission helpers. Server is source of truth (see /api/permissions),
// but we keep a mirror here so guards work while the request is in flight.

export const ROLE_ALIASES: Record<string, "SUPER ADMIN" | "ADMIN" | "KARYAWAN"> = {
  "SUPER ADMIN": "SUPER ADMIN",
  SUPERADMIN: "SUPER ADMIN",
  SUPER_ADMIN: "SUPER ADMIN",
  "SUPER-ADMIN": "SUPER ADMIN",
  ADMIN: "ADMIN",
  KARYAWAN: "KARYAWAN",
  STAFF: "KARYAWAN",
  OPERATOR: "ADMIN",
  USER: "KARYAWAN",
};

export type CanonicalRole = "SUPER ADMIN" | "ADMIN" | "KARYAWAN";

export function normalizeRole(value: unknown): CanonicalRole {
  if (!value) return "KARYAWAN";
  const raw = String(value)
    .trim()
    .toUpperCase()
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ");
  if (ROLE_ALIASES[raw]) return ROLE_ALIASES[raw];
  const compact = raw.replace(/\s/g, "");
  return ROLE_ALIASES[compact] || "KARYAWAN";
}

export type PermissionKey =
  | "manage_users"
  | "manage_ai"
  | "manage_countries"
  | "control_server"
  | "view_activity"
  | "send_reports"
  | "assign_super_admin";

const MATRIX: Record<CanonicalRole, Record<PermissionKey, boolean>> = {
  "SUPER ADMIN": {
    manage_users: true, manage_ai: true, manage_countries: true,
    control_server: true, view_activity: true, send_reports: true,
    assign_super_admin: true,
  },
  ADMIN: {
    manage_users: true, manage_ai: true, manage_countries: true,
    control_server: true, view_activity: true, send_reports: true,
    assign_super_admin: false,
  },
  KARYAWAN: {
    manage_users: false, manage_ai: false, manage_countries: false,
    control_server: false, view_activity: true, send_reports: true,
    assign_super_admin: false,
  },
};

export function hasPermission(
  user: { role?: string | null; permissions?: Partial<Record<PermissionKey, boolean>> | null } | null | undefined,
  perm: PermissionKey,
): boolean {
  if (!user) return false;
  if (user.permissions && user.permissions[perm] !== undefined) return !!user.permissions[perm];
  return MATRIX[normalizeRole(user.role)][perm];
}

export function isRole(user: { role?: string | null } | null | undefined, role: CanonicalRole): boolean {
  if (!user) return false;
  return normalizeRole(user.role) === role;
}
