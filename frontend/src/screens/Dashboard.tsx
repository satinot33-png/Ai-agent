import { MaterialCommunityIcons as Icon } from "@expo/vector-icons";
import React from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { Status } from "@/src/components/Status";
import { AI_ICONS, C, Screen } from "@/src/theme";
import { DashboardData } from "@/src/types";

export function Dashboard({ data, go }: { data: DashboardData; go: (s: Screen) => void }) {
  const active = data.ais.filter((x) => x.enabled).length;
  const activeCountries = data.countries.filter((c) => c.enabled);
  const metrics: [string, string][] = [
    ["CPU", `${data.server.cpu}%`],
    ["RAM", `${data.server.ram}%`],
    ["STORAGE", `${data.server.storage}%`],
    ["UPTIME", data.server.uptime],
    ["AI AKTIF", `${active}/7`],
    ["JOB AKTIF", `${data.server.active_jobs}`],
  ];
  return (
    <ScrollView contentContainerStyle={s.content} testID="dashboard-scroll">
      <Text style={s.kicker}>OVERVIEW / LIVE</Text>
      <View style={s.titleRow}>
        <View style={{ flex: 1 }}>
          <Text style={s.pageTitle}>Command center</Text>
          <Text style={s.muted}>Pantau operasi ekspor secara real-time.</Text>
        </View>
        <Status
          on={data.server.server_online}
          text={data.server.server_online ? "ONLINE" : "OFFLINE"}
        />
      </View>

      <View style={s.card}>
        <View style={s.titleRow}>
          <View>
            <Text style={s.muted}>SERVER CORE</Text>
            <Text style={s.cardTitle}>{data.server.domain}</Text>
          </View>
          <Icon name="server-network" size={30} color={C.amber} />
        </View>
        <View style={s.metrics}>
          {metrics.map(([a, b]) => (
            <View style={s.metric} key={a}>
              <Text style={s.metricLabel}>{a}</Text>
              <Text style={s.metricValue}>{b}</Text>
            </View>
          ))}
        </View>
      </View>

      <View style={s.titleRow}>
        <Text style={s.section}>AI NETWORK</Text>
        <Pressable testID="go-ai" onPress={() => go("7 AI")}>
          <Text style={s.link}>KELOLA →</Text>
        </Pressable>
      </View>
      <View style={s.aiGrid}>
        {data.ais.map((ai, i) => (
          <View style={s.aiMini} key={ai.agent_id} testID={`dash-ai-${ai.agent_id}`}>
            <Icon name={AI_ICONS[i] as any} size={21} color={ai.enabled ? C.amber : C.muted} />
            <Text style={s.aiName}>{ai.name}</Text>
            <Text style={s.aiFn} numberOfLines={1}>
              {ai.function}
            </Text>
            <Status on={ai.enabled} text={ai.enabled ? "ON" : "OFF"} />
          </View>
        ))}
      </View>

      <View style={s.titleRow}>
        <Text style={s.section}>TARGET NEGARA ({activeCountries.length})</Text>
        <Pressable testID="go-country" onPress={() => go("Pilih Negara")}>
          <Text style={s.link}>UBAH →</Text>
        </Pressable>
      </View>
      <View style={s.wrap}>
        {activeCountries.length === 0 ? (
          <Text style={s.muted}>Belum ada negara aktif.</Text>
        ) : (
          activeCountries.slice(0, 20).map((c) => (
            <View style={s.chip} key={c.code}>
              <Text style={s.chipText}>{c.name}</Text>
            </View>
          ))
        )}
      </View>

      <Text style={s.section}>AKTIVITAS TERBARU</Text>
      {data.logs.length === 0 ? (
        <Text style={s.muted}>Belum ada aktivitas.</Text>
      ) : (
        data.logs.map((l) => (
          <View style={s.log} key={l.log_id}>
            <Text style={s.body}>{l.action}</Text>
            <Text style={s.muted}>
              {l.detail} · {l.actor}
            </Text>
          </View>
        ))
      )}
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content: { padding: 20, paddingBottom: 48, gap: 14 },
  kicker: { color: C.amber, fontSize: 10, letterSpacing: 1.2, fontWeight: "800" },
  titleRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  pageTitle: { color: C.text, fontSize: 26, fontWeight: "900", marginVertical: 4 },
  muted: { color: C.muted, fontSize: 13, lineHeight: 20 },
  card: { backgroundColor: C.card, borderWidth: 1, borderColor: C.line, padding: 16, gap: 10 },
  cardTitle: { color: C.text, fontSize: 16, fontWeight: "800", marginTop: 2 },
  metrics: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 14 },
  metric: { flexBasis: "30%", flexGrow: 1, borderWidth: 1, borderColor: C.line, padding: 10 },
  metricLabel: { color: C.muted, fontSize: 10, letterSpacing: 1, fontWeight: "800" },
  metricValue: { color: C.text, fontSize: 16, fontWeight: "900", marginTop: 4 },
  section: { color: C.text, fontSize: 12, fontWeight: "900", letterSpacing: 1, marginTop: 6 },
  link: { color: C.amber, fontSize: 11, fontWeight: "900" },
  aiGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  aiMini: {
    width: "31%",
    minHeight: 108,
    backgroundColor: C.card,
    borderWidth: 1,
    borderColor: C.line,
    padding: 10,
    gap: 6,
  },
  aiName: { color: C.text, fontSize: 11, fontWeight: "800" },
  aiFn: { color: C.amber, fontSize: 10, fontWeight: "700" },
  wrap: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: { borderWidth: 1, borderColor: C.amber, paddingHorizontal: 10, paddingVertical: 6 },
  chipText: { color: C.amber, fontSize: 12, fontWeight: "700" },
  log: { borderBottomWidth: 1, borderColor: C.line, paddingBottom: 10, gap: 4 },
  body: { color: C.text, fontSize: 14, fontWeight: "700" },
});
