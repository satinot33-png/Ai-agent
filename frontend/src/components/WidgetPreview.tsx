import { MaterialCommunityIcons as Icon } from "@expo/vector-icons";
import React, { useCallback, useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { api } from "@/src/api";
import { C } from "@/src/theme";

type WidgetStatus = {
  server_online: boolean;
  active_ai: string;
  jobs_today: { successful: number; failed: number };
  active_jobs: number;
  recent_errors: number;
  generated_at: string;
};

export function WidgetPreview({ token }: { token: string }) {
  const [data, setData] = useState<WidgetStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setData(await api<WidgetStatus>("/widget/status", { token }));
      setError("");
    } catch (e: any) {
      setError(e.message || "Gagal memuat widget");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, [load]);

  if (loading) return null;
  if (error || !data) return null;

  const total = data.jobs_today.successful + data.jobs_today.failed;
  const okColor = data.server_online ? C.green : C.red;

  return (
    <View style={s.wrap} testID="widget-preview">
      <View style={s.head}>
        <Text style={s.label}>WIDGET HOME SCREEN · PREVIEW</Text>
        <Pressable testID="widget-refresh" onPress={load}>
          <Icon name="refresh" size={16} color={C.amber} />
        </Pressable>
      </View>
      <View style={s.widget}>
        <View style={s.widgetHead}>
          <Icon name="orbit" size={16} color={C.amber} />
          <Text style={s.widgetBrand}>EXPORT 7 AI</Text>
          <View style={[s.pulseDot, { backgroundColor: okColor }]} />
        </View>
        <View style={s.widgetRow}>
          <View style={s.widgetCol}>
            <Text style={s.widgetVal}>{data.active_ai}</Text>
            <Text style={s.widgetSub}>AI AKTIF</Text>
          </View>
          <View style={s.widgetSep} />
          <View style={s.widgetCol}>
            <Text style={s.widgetVal}>{data.active_jobs}</Text>
            <Text style={s.widgetSub}>JOB AKTIF</Text>
          </View>
          <View style={s.widgetSep} />
          <View style={s.widgetCol}>
            <Text style={s.widgetVal}>{total}</Text>
            <Text style={s.widgetSub}>JOB HARI INI</Text>
          </View>
        </View>
        <View style={s.widgetFooter}>
          <Text style={[s.widgetStatus, { color: okColor }]}>
            {data.server_online ? "SERVER ONLINE" : "SERVER OFFLINE"}
          </Text>
          {data.recent_errors > 0 ? (
            <Text style={s.widgetError}>{data.recent_errors} error 5 mnt terakhir</Text>
          ) : (
            <Text style={s.widgetOk}>
              ✓ {data.jobs_today.successful} sukses · {data.jobs_today.failed} gagal
            </Text>
          )}
        </View>
      </View>
      <View style={s.helpBox}>
        <Icon name="information-outline" size={16} color={C.amber} />
        <Text style={s.helpText}>
          Widget iOS/Android akan menarik data dari{" "}
          <Text style={s.mono}>/api/widget/status</Text> setiap ~30 menit. Perlu build native
          (Publish → Deploy → Generate Build) — widget tidak berjalan di Expo Go.
        </Text>
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  wrap: { gap: 10 },
  head: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  label: { color: C.muted, fontSize: 10, letterSpacing: 1, fontWeight: "800" },
  widget: {
    backgroundColor: "#12161C",
    borderWidth: 1,
    borderColor: C.amber,
    borderRadius: 22,
    padding: 14,
    gap: 12,
    shadowColor: C.amber,
    shadowOpacity: 0.4,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 8 },
    elevation: 6,
  },
  widgetHead: { flexDirection: "row", alignItems: "center", gap: 8 },
  widgetBrand: { color: C.text, fontSize: 12, fontWeight: "900", letterSpacing: 1, flex: 1 },
  pulseDot: { width: 10, height: 10, borderRadius: 10 },
  widgetRow: { flexDirection: "row", alignItems: "center" },
  widgetCol: { flex: 1, alignItems: "center", gap: 4 },
  widgetSep: { width: 1, alignSelf: "stretch", backgroundColor: C.line, marginVertical: 4 },
  widgetVal: { color: C.amber, fontSize: 26, fontWeight: "900", letterSpacing: 0.5 },
  widgetSub: { color: C.muted, fontSize: 9, fontWeight: "800", letterSpacing: 1 },
  widgetFooter: {
    borderTopWidth: 1,
    borderColor: C.line,
    paddingTop: 8,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  widgetStatus: { fontSize: 10, fontWeight: "900", letterSpacing: 0.5 },
  widgetError: { color: C.red, fontSize: 11, fontWeight: "800" },
  widgetOk: { color: C.muted, fontSize: 11, fontWeight: "700" },
  helpBox: {
    flexDirection: "row",
    gap: 8,
    borderWidth: 1,
    borderColor: C.line,
    backgroundColor: C.amberSoft,
    padding: 10,
  },
  helpText: { color: C.text, fontSize: 12, flex: 1, lineHeight: 18 },
  mono: { color: C.amber, fontWeight: "800" },
});
