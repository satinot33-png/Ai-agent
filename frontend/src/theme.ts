export const C = {
  bg: "#0E1116",
  card: "#161B22",
  cardAlt: "#1B222D",
  line: "#30363D",
  text: "#F0F2F5",
  muted: "#8B949E",
  amber: "#F0883E",
  amberSoft: "#2D221B",
  green: "#3FB950",
  red: "#F85149",
  yellow: "#D29922",
  blue: "#58A6FF",
};

export const AI_ICONS = [
  "account-search",
  "chart-line",
  "earth",
  "package-variant",
  "bullhorn",
  "reply",
  "file-chart-outline",
] as const;

export const SCREENS = [
  "Dashboard",
  "7 AI",
  "Pilih Negara",
  "Server",
  "Interogasi Server",
  "Akses / User",
  "Pengaturan",
] as const;

export type Screen = (typeof SCREENS)[number];
