import { MaterialCommunityIcons as Icon } from "@expo/vector-icons";
import React, { useCallback, useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { api } from "@/src/api";
import { C } from "@/src/theme";

export type AlertSummary = {
  window_minutes: number;
  error_count: number;
  warning_count: number;
  latest?: {
    event_id: string;
    agent_id: string;
    agent_name: string;
    level: "error" | "warning";
    message: string;
    created_at: string;
  } | null;
  events: any[];
};

export function AlertBanner({
  token,
  onOpen,
  pollMs = 15000,
}: {
  token: string;
  onOpen?: () => void;
  pollMs?: number;
}) {
  const [data, setData] = useState<AlertSummary | null>(null);
  const [dismissed, setDismissed] = useState<string>("");

  const load = useCallback(async () => {
    try {
      const res = await api<AlertSummary>("/alerts?minutes=5", { token });
      setData(res);
    } catch {
      /* transient */
    }
  }, [token]);

  useEffect(() => {
    load();
    const id = setInterval(load, pollMs);
    return () => clearInterval(id);
  }, [load, pollMs]);

  if (!data || data.error_count === 0) return null;
  if (data.latest?.event_id === dismissed) return null;

  const latest = data.latest;
  const tone = data.error_count > 0 ? "error" : "warning";
  const color = tone === "error" ? C.red : C.yellow;

  return (
    <Pressable
      testID="alert-banner"
      onPress={onOpen}
      style={[s.wrap, { borderColor: color }]}
    >
      <View style={[s.stripe, { backgroundColor: color }]} />
      <View style={{ flex: 1, gap: 2 }}>
        <View style={s.row}>
          <Icon
            name={tone === "error" ? "alert-octagon" : "alert"}
            size={18}
            color={color}
          />
          <Text style={[s.title, { color }]}>
            {data.error_count} ERROR · {data.warning_count} WARNING · 5 MENIT TERAKHIR
          </Text>
        </View>
        {latest ? (
          <Text style={s.msg} numberOfLines={2}>
            {latest.agent_name} · {latest.message}
          </Text>
        ) : null}
        <Text style={s.hint}>Tap untuk lihat 7 AI · Live Feed</Text>
      </View>
      <Pressable
        testID="alert-dismiss"
        onPress={(e) => {
          e.stopPropagation();
          setDismissed(latest?.event_id || "");
        }}
        hitSlop={10}
      >
        <Icon name="close" size={18} color={color} />
      </Pressable>
    </Pressable>
  );
}

const s = StyleSheet.create({
  wrap: {
    backgroundColor: "#2A1418",
    borderWidth: 1,
    padding: 12,
    paddingLeft: 14,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  stripe: { width: 3, alignSelf: "stretch", marginRight: 6 },
  row: { flexDirection: "row", alignItems: "center", gap: 8 },
  title: { fontSize: 11, fontWeight: "900", letterSpacing: 0.5, flexShrink: 1 },
  msg: { color: C.text, fontSize: 13, fontWeight: "700" },
  hint: { color: C.muted, fontSize: 11, marginTop: 2 },
});
