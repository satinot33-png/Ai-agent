import { MaterialCommunityIcons as Icon } from "@expo/vector-icons";
import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { api } from "@/src/api";
import { Toast } from "@/src/components/Feedback";
import { C } from "@/src/theme";
import { ActivityLog, User } from "@/src/types";

export function SettingsPage({
  token,
  user,
  onLogout,
}: {
  token: string;
  user: User;
  onLogout: () => void;
}) {
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setLogs(await api<ActivityLog[]>("/activity", { token }));
    } catch (e: any) {
      setError(e.message || "Gagal memuat aktivitas");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <ScrollView contentContainerStyle={s.content} testID="settings-scroll">
      <Text style={s.kicker}>PROFILE / SETTINGS</Text>
      <Text style={s.pageTitle}>Pengaturan</Text>

      <View style={s.card}>
        <Text style={s.section}>AKUN ANDA</Text>
        <Row label="Nama" value={user.name} />
        <Row label="Username" value={user.username || "-"} />
        <Row label="Email" value={user.email || "-"} />
        <Row label="WhatsApp" value={user.whatsapp || "-"} />
        <Row label="Role" value={String(user.role)} highlight />
        <Row label="Provider" value={String(user.auth_provider || "-")} />
        <Pressable testID="account-logout" style={s.logout} onPress={onLogout}>
          <Icon name="logout" size={18} color={C.red} />
          <Text style={{ color: C.red, fontWeight: "900" }}>KELUAR</Text>
        </Pressable>
      </View>

      <View style={s.card}>
        <Text style={s.section}>AUDIT LOG (50 TERAKHIR)</Text>
        {loading ? (
          <ActivityIndicator color={C.amber} />
        ) : error ? (
          <Toast message={error} tone="error" />
        ) : logs.length === 0 ? (
          <Text style={s.muted}>Belum ada aktivitas.</Text>
        ) : (
          logs.map((l) => (
            <View style={s.log} key={l.log_id}>
              <Text style={s.logAction}>{l.action}</Text>
              <Text style={s.muted}>{l.detail}</Text>
              <Text style={[s.muted, { fontSize: 11 }]}>
                {l.actor} · {new Date(l.created_at).toLocaleString("id-ID")}
              </Text>
            </View>
          ))
        )}
      </View>
    </ScrollView>
  );
}

function Row({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <View style={s.row}>
      <Text style={s.label}>{label}</Text>
      <Text style={[s.value, highlight && { color: C.amber }]}>{value}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  content: { padding: 20, paddingBottom: 48, gap: 12 },
  kicker: { color: C.amber, fontSize: 10, letterSpacing: 1.2, fontWeight: "800" },
  pageTitle: { color: C.text, fontSize: 26, fontWeight: "900" },
  card: { backgroundColor: C.card, borderWidth: 1, borderColor: C.line, padding: 16, gap: 10 },
  section: { color: C.text, fontSize: 11, fontWeight: "900", letterSpacing: 1 },
  row: { flexDirection: "row", justifyContent: "space-between", paddingVertical: 8, borderBottomWidth: 1, borderColor: C.line },
  label: { color: C.muted, fontSize: 12 },
  value: { color: C.text, fontSize: 13, fontWeight: "800", flexShrink: 1, textAlign: "right", maxWidth: "60%" },
  logout: { flexDirection: "row", gap: 8, alignItems: "center", justifyContent: "center", padding: 12, borderWidth: 1, borderColor: C.red, marginTop: 4 },
  muted: { color: C.muted, fontSize: 12, lineHeight: 18 },
  log: { borderBottomWidth: 1, borderColor: C.line, paddingVertical: 8, gap: 3 },
  logAction: { color: C.text, fontSize: 13, fontWeight: "800" },
});
