import { MaterialCommunityIcons as Icon } from "@expo/vector-icons";
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { api } from "@/src/api";
import { Status } from "@/src/components/Status";
import { Toast } from "@/src/components/Feedback";
import { AI_ICONS, C } from "@/src/theme";
import { AIAgent, User } from "@/src/types";

type Props = { token: string; user: User; onLog: () => void };

export function AIPage({ token, user, onLog }: Props) {
  const isAdmin = ["SUPER ADMIN", "ADMIN"].includes(String(user.role).toUpperCase());
  const [ais, setAis] = useState<AIAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string>("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const data = await api<AIAgent[]>("/ai", { token });
      setAis(data);
    } catch (e: any) {
      setError(e.message || "Gagal memuat data AI");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const toggle = async (agent: AIAgent) => {
    if (busy) return;
    setBusy(agent.agent_id);
    setError("");
    const previous = ais;
    // Optimistic UI
    setAis((prev) => prev.map((a) => (a.agent_id === agent.agent_id ? { ...a, enabled: !agent.enabled } : a)));
    try {
      const updated = await api<AIAgent>(`/ai/${agent.agent_id}`, {
        method: "PATCH",
        token,
        body: JSON.stringify({ enabled: !agent.enabled }),
      });
      setAis((prev) => prev.map((a) => (a.agent_id === updated.agent_id ? updated : a)));
      onLog();
    } catch (e: any) {
      setAis(previous); // revert
      setError(e.message || "Gagal mengubah status AI");
    } finally {
      setBusy("");
    }
  };

  const bulk = async (enabled: boolean) => {
    if (busy) return;
    setBusy("bulk");
    setError("");
    try {
      const updated = await api<AIAgent[]>("/ai/bulk", {
        method: "POST",
        token,
        body: JSON.stringify({ enabled }),
      });
      setAis(updated);
      onLog();
    } catch (e: any) {
      setError(e.message || "Gagal mengubah semua AI");
    } finally {
      setBusy("");
    }
  };

  if (loading) {
    return (
      <View style={s.center} testID="ai-loading">
        <ActivityIndicator color={C.amber} />
        <Text style={s.muted}>Memuat 7 AI dari server...</Text>
      </View>
    );
  }

  return (
    <ScrollView
      contentContainerStyle={s.content}
      testID="ai-scroll"
      refreshControl={<RefreshControl refreshing={busy === "bulk"} onRefresh={load} tintColor={C.amber} />}
    >
      <Text style={s.kicker}>AI NETWORK / 7 AGENTS</Text>
      <Text style={s.pageTitle}>Kontrol 7 AI</Text>
      <Text style={s.muted}>
        {isAdmin
          ? "Setiap perubahan tersimpan langsung ke database dan tercatat di audit log."
          : "Anda melihat status AI secara read-only."}
      </Text>

      {isAdmin && (
        <View style={s.actions}>
          <Pressable
            testID="enable-all-ai"
            onPress={() => bulk(true)}
            disabled={!!busy}
            style={[s.small, busy && s.disabled]}
          >
            {busy === "bulk" ? <ActivityIndicator color={C.amber} /> : <Text style={s.smallText}>AKTIFKAN SEMUA</Text>}
          </Pressable>
          <Pressable
            testID="disable-all-ai"
            onPress={() => bulk(false)}
            disabled={!!busy}
            style={[s.small, busy && s.disabled]}
          >
            <Text style={s.smallText}>MATIKAN SEMUA</Text>
          </Pressable>
        </View>
      )}

      {error ? <Toast message={error} tone="error" /> : null}

      {ais.map((ai, i) => {
        const isBusy = busy === ai.agent_id;
        return (
          <View style={s.aiCard} key={ai.agent_id} testID={`ai-card-${ai.agent_id}`}>
            <View style={[s.aiIcon, { backgroundColor: ai.enabled ? C.amberSoft : C.cardAlt }]}>
              <Icon name={AI_ICONS[i] as any} size={22} color={ai.enabled ? C.amber : C.muted} />
            </View>
            <View style={{ flex: 1, gap: 4 }}>
              <View style={s.titleRow}>
                <Text style={s.cardTitle}>{ai.name}</Text>
                <Status on={ai.enabled} text={ai.enabled ? "ON" : "OFF"} />
              </View>
              <Text style={s.function}>{ai.function}</Text>
              <Text style={s.muted} numberOfLines={2}>
                {ai.job_status} · {ai.last_activity}
              </Text>
            </View>
            {isAdmin && (
              <Pressable
                testID={`toggle-${ai.agent_id}`}
                onPress={() => toggle(ai)}
                disabled={!!busy}
                style={[s.toggle, ai.enabled && s.toggleOn, isBusy && { opacity: 0.6 }]}
              >
                {isBusy ? (
                  <ActivityIndicator size="small" color={ai.enabled ? C.bg : C.amber} />
                ) : (
                  <View style={[s.knob, ai.enabled && s.knobOn]} />
                )}
              </Pressable>
            )}
          </View>
        );
      })}
    </ScrollView>
  );
}

const s = StyleSheet.create({
  content: { padding: 20, paddingBottom: 48, gap: 12 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: C.bg, gap: 8 },
  kicker: { color: C.amber, fontSize: 10, letterSpacing: 1.2, fontWeight: "800" },
  pageTitle: { color: C.text, fontSize: 26, fontWeight: "900", marginVertical: 4 },
  muted: { color: C.muted, fontSize: 13, lineHeight: 20 },
  titleRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  cardTitle: { color: C.text, fontSize: 15, fontWeight: "900" },
  actions: { flexDirection: "row", gap: 8, marginTop: 4 },
  small: {
    borderWidth: 1,
    borderColor: C.amber,
    padding: 12,
    flex: 1,
    minWidth: 130,
    alignItems: "center",
  },
  smallText: { color: C.amber, fontSize: 11, fontWeight: "900", letterSpacing: 0.5 },
  disabled: { opacity: 0.5 },
  aiCard: {
    backgroundColor: C.card,
    borderWidth: 1,
    borderColor: C.line,
    padding: 14,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  aiIcon: { width: 44, height: 44, alignItems: "center", justifyContent: "center" },
  function: { color: C.amber, fontSize: 12, fontWeight: "800" },
  toggle: {
    width: 52,
    height: 30,
    borderRadius: 30,
    backgroundColor: C.line,
    justifyContent: "center",
    padding: 3,
  },
  toggleOn: { backgroundColor: C.amber },
  knob: { width: 24, height: 24, borderRadius: 24, backgroundColor: C.muted },
  knobOn: { alignSelf: "flex-end", backgroundColor: C.bg },
});
