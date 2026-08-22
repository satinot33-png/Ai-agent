import { MaterialCommunityIcons as Icon } from "@expo/vector-icons";
import React, { useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { api } from "@/src/api";
import { Toast } from "@/src/components/Feedback";
import { C } from "@/src/theme";
import { InterrogationResult, User } from "@/src/types";

const TONE: Record<string, "ok" | "warn" | "error"> = {
  OK: "ok",
  WARNING: "warn",
  ERROR: "error",
};

function Row({ label, status }: { label: string; status: string }) {
  const tone = TONE[status] || "warn";
  const color = tone === "ok" ? C.green : tone === "warn" ? C.yellow : C.red;
  return (
    <View style={s.row} testID={`report-${label.toLowerCase().replace(/\s+/g, "-")}`}>
      <Icon
        name={status === "OK" ? "check-circle" : status === "WARNING" ? "alert-circle" : "close-circle"}
        size={20}
        color={color}
      />
      <Text style={s.rowLabel}>{label}</Text>
      <Text style={[s.rowStatus, { color }]}>{status}</Text>
    </View>
  );
}

export function InterrogationPage({ token, user, onLog }: { token: string; user: User; onLog: () => void }) {
  const [result, setResult] = useState<InterrogationResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const run = async () => {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      setResult(await api<InterrogationResult>("/interrogation", { method: "POST", token }));
      onLog();
    } catch (e: any) {
      setError(e.message || "Gagal menjalankan pemeriksaan");
    } finally {
      setBusy(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={s.content} testID="interrogation-scroll">
      <Text style={s.kicker}>SYSTEM / INTERROGATION</Text>
      <Text style={s.pageTitle}>Interogasi Server</Text>
      <Text style={s.muted}>
        Pemeriksaan menyeluruh: koneksi, API, database, status 7 AI, jumlah job dan error terakhir.
      </Text>

      <Pressable
        testID="check-server"
        style={[s.primary, busy && { opacity: 0.6 }]}
        onPress={run}
        disabled={busy}
      >
        {busy ? (
          <ActivityIndicator color={C.bg} />
        ) : (
          <>
            <Icon name="shield-search" size={18} color={C.bg} />
            <Text style={s.primaryText}>CHECK SERVER</Text>
          </>
        )}
      </Pressable>

      {error ? <Toast message={error} tone="error" /> : null}

      {result && (
        <View style={s.card} testID="interrogation-result">
          <Text style={s.section}>RINGKASAN</Text>
          <Row label="Koneksi Server" status={result.connection} />
          <Row label="API" status={result.api} />
          <Row label="Database" status={result.database} />
          <Text style={[s.section, { marginTop: 12 }]}>7 AI</Text>
          {result.ai.map((a) => (
            <Row key={a.agent_id} label={a.name} status={a.status} />
          ))}
          <Text style={[s.section, { marginTop: 12 }]}>JOB</Text>
          <View style={s.metrics}>
            <View style={s.metric}>
              <Text style={s.metricLabel}>AKTIF</Text>
              <Text style={s.metricValue}>{result.active_jobs}</Text>
            </View>
            <View style={s.metric}>
              <Text style={s.metricLabel}>BERHASIL</Text>
              <Text style={[s.metricValue, { color: C.green }]}>{result.successful_jobs}</Text>
            </View>
            <View style={s.metric}>
              <Text style={s.metricLabel}>GAGAL</Text>
              <Text style={[s.metricValue, { color: C.red }]}>{result.failed_jobs}</Text>
            </View>
          </View>
          <Text style={[s.section, { marginTop: 12 }]}>ERROR TERAKHIR</Text>
          <Text style={s.body}>{result.last_error}</Text>
          <Text style={s.muted}>Diperiksa: {new Date(result.checked_at).toLocaleString("id-ID")}</Text>
        </View>
      )}
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content: { padding: 20, paddingBottom: 48, gap: 12 },
  kicker: { color: C.amber, fontSize: 10, letterSpacing: 1.2, fontWeight: "800" },
  pageTitle: { color: C.text, fontSize: 26, fontWeight: "900" },
  muted: { color: C.muted, fontSize: 13, lineHeight: 20 },
  primary: {
    minHeight: 50,
    backgroundColor: C.amber,
    justifyContent: "center",
    alignItems: "center",
    flexDirection: "row",
    gap: 9,
    marginTop: 6,
  },
  primaryText: { color: C.bg, fontWeight: "900", fontSize: 13 },
  card: { backgroundColor: C.card, borderWidth: 1, borderColor: C.line, padding: 16, gap: 10 },
  section: { color: C.text, fontSize: 11, fontWeight: "900", letterSpacing: 1 },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderColor: C.line,
  },
  rowLabel: { color: C.text, flex: 1, fontSize: 14 },
  rowStatus: { fontWeight: "900", fontSize: 12, letterSpacing: 0.5 },
  metrics: { flexDirection: "row", gap: 8 },
  metric: { flex: 1, borderWidth: 1, borderColor: C.line, padding: 10 },
  metricLabel: { color: C.muted, fontSize: 10, letterSpacing: 1, fontWeight: "800" },
  metricValue: { color: C.text, fontSize: 16, fontWeight: "900", marginTop: 4 },
  body: { color: C.text, fontSize: 14 },
});
