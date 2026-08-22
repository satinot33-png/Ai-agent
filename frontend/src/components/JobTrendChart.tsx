import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { C } from "@/src/theme";

export type JobStat = {
  date: string;
  successful: number;
  failed: number;
  active: number;
};

const HEIGHT = 110;
const WEEKDAY = ["Min", "Sen", "Sel", "Rab", "Kam", "Jum", "Sab"];

function short(dateISO: string) {
  const d = new Date(dateISO + "T00:00:00");
  if (isNaN(d.getTime())) return dateISO.slice(5);
  return WEEKDAY[d.getDay()];
}

export function JobTrendChart({ stats }: { stats: JobStat[] }) {
  const totalSuccess = stats.reduce((s, x) => s + x.successful, 0);
  const totalFail = stats.reduce((s, x) => s + x.failed, 0);
  const grand = Math.max(1, ...stats.map((x) => x.successful + x.failed));
  const successPct = totalSuccess + totalFail === 0
    ? 0
    : Math.round((totalSuccess * 100) / (totalSuccess + totalFail));

  return (
    <View style={s.card} testID="job-trend-chart">
      <View style={s.head}>
        <View>
          <Text style={s.muted}>TREN JOB · 7 HARI TERAKHIR</Text>
          <Text style={s.title}>
            {totalSuccess.toLocaleString("id-ID")} sukses
            <Text style={s.mutedInline}> / </Text>
            <Text style={{ color: C.red }}>{totalFail.toLocaleString("id-ID")} gagal</Text>
          </Text>
        </View>
        <View style={s.badge}>
          <Text style={s.badgeText}>{successPct}%</Text>
          <Text style={s.badgeLabel}>SUKSES</Text>
        </View>
      </View>

      <View style={s.chartRow}>
        {stats.length === 0 ? (
          <Text style={s.muted}>Belum ada data statistik.</Text>
        ) : (
          stats.map((row) => {
            const total = row.successful + row.failed;
            const successH = Math.max(2, (row.successful / grand) * HEIGHT);
            const failH = Math.max(0, (row.failed / grand) * HEIGHT);
            return (
              <View key={row.date} style={s.col} testID={`bar-${row.date}`}>
                <Text style={s.colTotal}>{total}</Text>
                <View style={s.stack}>
                  {failH > 0 ? (
                    <View style={[s.barFail, { height: failH }]} testID={`bar-fail-${row.date}`} />
                  ) : null}
                  <View style={[s.barSuccess, { height: successH }]} testID={`bar-ok-${row.date}`} />
                </View>
                <Text style={s.colLabel}>{short(row.date)}</Text>
              </View>
            );
          })
        )}
      </View>

      <View style={s.legend}>
        <View style={s.legendItem}>
          <View style={[s.legendDot, { backgroundColor: C.green }]} />
          <Text style={s.legendText}>Sukses</Text>
        </View>
        <View style={s.legendItem}>
          <View style={[s.legendDot, { backgroundColor: C.red }]} />
          <Text style={s.legendText}>Gagal</Text>
        </View>
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  card: { backgroundColor: C.card, borderWidth: 1, borderColor: C.line, padding: 14, gap: 12 },
  head: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-end" },
  muted: { color: C.muted, fontSize: 10, letterSpacing: 1, fontWeight: "800" },
  mutedInline: { color: C.muted, fontWeight: "700" },
  title: { color: C.green, fontSize: 15, fontWeight: "900", marginTop: 4 },
  badge: { alignItems: "center", borderWidth: 1, borderColor: C.amber, paddingHorizontal: 12, paddingVertical: 6 },
  badgeText: { color: C.amber, fontSize: 18, fontWeight: "900", lineHeight: 20 },
  badgeLabel: { color: C.amber, fontSize: 8, fontWeight: "800", letterSpacing: 1 },
  chartRow: {
    flexDirection: "row",
    alignItems: "flex-end",
    justifyContent: "space-between",
    height: HEIGHT + 40,
    gap: 6,
  },
  col: { flex: 1, alignItems: "center", justifyContent: "flex-end", gap: 4 },
  colTotal: { color: C.text, fontSize: 10, fontWeight: "800" },
  stack: { justifyContent: "flex-end", alignItems: "center", width: "100%" },
  barSuccess: { width: "88%", backgroundColor: C.green, minHeight: 2 },
  barFail: { width: "88%", backgroundColor: C.red },
  colLabel: { color: C.muted, fontSize: 10, fontWeight: "700" },
  legend: { flexDirection: "row", gap: 16, justifyContent: "center", borderTopWidth: 1, borderColor: C.line, paddingTop: 8 },
  legendItem: { flexDirection: "row", alignItems: "center", gap: 6 },
  legendDot: { width: 8, height: 8, borderRadius: 8 },
  legendText: { color: C.muted, fontSize: 11, fontWeight: "700" },
});
