import { MaterialCommunityIcons as Icon } from "@expo/vector-icons";
import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { api } from "@/src/api";
import { Status } from "@/src/components/Status";
import { ConfirmSheet, Toast } from "@/src/components/Feedback";
import { C } from "@/src/theme";
import { ServerState, User } from "@/src/types";

export function ServerPage({ token, user, onLog }: { token: string; user: User; onLog: () => void }) {
  const isAdmin = ["SUPER ADMIN", "ADMIN"].includes(String(user.role).toUpperCase());
  const [state, setState] = useState<ServerState | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [confirmAction, setConfirmAction] = useState<"off" | "restart" | null>(null);

  const load = useCallback(async () => {
    setError("");
    try {
      setState(await api<ServerState>("/server", { token }));
    } catch (e: any) {
      setError(e.message || "Gagal memuat status server");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const runAction = async (action: "on" | "off" | "restart") => {
    if (busy) return;
    setConfirmAction(null);
    setBusy(true);
    setError("");
    try {
      setState(await api<ServerState>("/server/action", {
        method: "POST",
        token,
        body: JSON.stringify({ action }),
      }));
      onLog();
    } catch (e: any) {
      setError(e.message || "Gagal menjalankan aksi server");
    } finally {
      setBusy(false);
    }
  };

  if (loading || !state) {
    return (
      <View style={s.center} testID="server-loading">
        <ActivityIndicator color={C.amber} />
        <Text style={s.muted}>Memuat status server...</Text>
      </View>
    );
  }

  const metrics: [string, string][] = [
    ["CPU", `${state.cpu}%`],
    ["RAM", `${state.ram}%`],
    ["STORAGE", `${state.storage}%`],
    ["UPTIME", state.uptime],
    ["JOB AKTIF", `${state.active_jobs}`],
    ["JOB SUKSES", `${state.successful_jobs}`],
    ["JOB GAGAL", `${state.failed_jobs}`],
    ["API", state.api_online ? "OK" : "DOWN"],
  ];

  return (
    <ScrollView contentContainerStyle={s.content} testID="server-scroll">
      <Text style={s.kicker}>SERVER / CORE</Text>
      <Text style={s.pageTitle}>Kontrol Server</Text>

      <View style={s.card}>
        <View style={s.rowBetween}>
          <View>
            <Text style={s.muted}>ENDPOINT</Text>
            <Text style={s.cardTitle}>{state.domain}</Text>
          </View>
          <Status on={state.server_online} text={state.server_online ? "ONLINE" : "OFFLINE"} />
        </View>
        <View style={s.metrics}>
          {metrics.map(([label, value]) => (
            <View style={s.metric} key={label}>
              <Text style={s.metricLabel}>{label}</Text>
              <Text style={s.metricValue}>{value}</Text>
            </View>
          ))}
        </View>
        {state.last_error ? (
          <View style={s.errorBox}>
            <Text style={s.muted}>ERROR TERAKHIR</Text>
            <Text style={s.errorText}>{state.last_error}</Text>
          </View>
        ) : null}
      </View>

      {error ? <Toast message={error} tone="error" /> : null}

      {isAdmin ? (
        <View style={s.actionsCol}>
          <Text style={s.section}>AKSI ADMIN</Text>
          <Pressable
            testID="server-on"
            style={[s.actionBtn, { borderColor: C.green }]}
            onPress={() => runAction("on")}
            disabled={busy}
          >
            <Icon name="power" size={22} color={C.green} />
            <View style={{ flex: 1 }}>
              <Text style={[s.actionTitle, { color: C.green }]}>SERVER ON</Text>
              <Text style={s.muted}>Aktifkan seluruh layanan server.</Text>
            </View>
            {busy && <ActivityIndicator color={C.green} />}
          </Pressable>
          <Pressable
            testID="server-restart"
            style={[s.actionBtn, { borderColor: C.yellow }]}
            onPress={() => setConfirmAction("restart")}
            disabled={busy}
          >
            <Icon name="restart" size={22} color={C.yellow} />
            <View style={{ flex: 1 }}>
              <Text style={[s.actionTitle, { color: C.yellow }]}>RESTART SERVER</Text>
              <Text style={s.muted}>Muat ulang layanan tanpa mematikan permanen.</Text>
            </View>
          </Pressable>
          <Pressable
            testID="server-off"
            style={[s.actionBtn, { borderColor: C.red }]}
            onPress={() => setConfirmAction("off")}
            disabled={busy}
          >
            <Icon name="power-off" size={22} color={C.red} />
            <View style={{ flex: 1 }}>
              <Text style={[s.actionTitle, { color: C.red }]}>SERVER OFF</Text>
              <Text style={s.muted}>Matikan server. Semua job akan berhenti.</Text>
            </View>
          </Pressable>
        </View>
      ) : (
        <Text style={s.muted}>Hanya SUPER ADMIN / ADMIN yang dapat mengendalikan server.</Text>
      )}

      <ConfirmSheet
        open={confirmAction === "off"}
        title="Matikan server?"
        body="Semua AI dan job aktif akan berhenti. Aksi ini akan tercatat di audit log."
        confirmText="MATIKAN"
        danger
        onConfirm={() => runAction("off")}
        onCancel={() => setConfirmAction(null)}
      />
      <ConfirmSheet
        open={confirmAction === "restart"}
        title="Restart server?"
        body="Layanan akan dimuat ulang. Job aktif dapat terganggu sesaat."
        confirmText="RESTART"
        onConfirm={() => runAction("restart")}
        onCancel={() => setConfirmAction(null)}
      />
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content: { padding: 20, paddingBottom: 48, gap: 14 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: C.bg, gap: 8 },
  kicker: { color: C.amber, fontSize: 10, letterSpacing: 1.2, fontWeight: "800" },
  pageTitle: { color: C.text, fontSize: 26, fontWeight: "900" },
  muted: { color: C.muted, fontSize: 13, lineHeight: 20 },
  card: { backgroundColor: C.card, borderWidth: 1, borderColor: C.line, padding: 16, gap: 12 },
  rowBetween: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  cardTitle: { color: C.text, fontSize: 16, fontWeight: "800", marginTop: 2 },
  metrics: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  metric: { flexBasis: "30%", flexGrow: 1, borderWidth: 1, borderColor: C.line, padding: 10 },
  metricLabel: { color: C.muted, fontSize: 10, letterSpacing: 1, fontWeight: "800" },
  metricValue: { color: C.text, fontSize: 15, fontWeight: "900", marginTop: 4 },
  errorBox: { borderWidth: 1, borderColor: C.line, padding: 10, gap: 4 },
  errorText: { color: C.text, fontSize: 13 },
  actionsCol: { gap: 10 },
  section: { color: C.text, fontSize: 11, fontWeight: "900", letterSpacing: 1, marginTop: 6 },
  actionBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    borderWidth: 1,
    padding: 14,
    backgroundColor: C.card,
  },
  actionTitle: { fontSize: 13, fontWeight: "900", letterSpacing: 0.5 },
});
