import { MaterialCommunityIcons as Icon } from "@expo/vector-icons";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { api } from "@/src/api";
import { Status } from "@/src/components/Status";
import { Toast } from "@/src/components/Feedback";
import { C } from "@/src/theme";
import { Country, User } from "@/src/types";
import { hasPermission } from "@/src/utils/roles";

type Props = { token: string; user: User; onLog: () => void };

export function CountryPage({ token, user, onLog }: Props) {
  const isAdmin = hasPermission(user, "manage_countries");
  const [countries, setCountries] = useState<Country[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string>("");
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [region, setRegion] = useState<string>("Semua");

  const load = useCallback(async () => {
    setError("");
    try {
      setCountries(await api<Country[]>("/countries", { token }));
    } catch (e: any) {
      setError(e.message || "Gagal memuat daftar negara");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const regions = useMemo(() => {
    const set = new Set<string>();
    countries.forEach((c) => set.add(c.region));
    return ["Semua", ...Array.from(set).sort()];
  }, [countries]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return countries.filter((c) => {
      if (region !== "Semua" && c.region !== region) return false;
      if (!q) return true;
      return c.name.toLowerCase().includes(q) || c.code.toLowerCase().includes(q);
    });
  }, [countries, query, region]);

  const activeCount = countries.filter((c) => c.enabled).length;
  const filteredActive = filtered.filter((c) => c.enabled).length;

  const toggle = async (c: Country) => {
    if (!isAdmin || busy) return;
    setBusy(c.code);
    setError("");
    const prev = countries;
    setCountries((list) => list.map((x) => (x.code === c.code ? { ...x, enabled: !c.enabled } : x)));
    try {
      const updated = await api<Country>(`/countries/${c.code}`, {
        method: "PATCH",
        token,
        body: JSON.stringify({ enabled: !c.enabled }),
      });
      setCountries((list) => list.map((x) => (x.code === updated.code ? updated : x)));
      onLog();
    } catch (e: any) {
      setCountries(prev);
      setError(e.message || "Gagal mengubah negara");
    } finally {
      setBusy("");
    }
  };

  const bulk = async (enabled: boolean) => {
    if (!isAdmin || busy) return;
    setBusy("bulk");
    setError("");
    try {
      const list = await api<Country[]>("/countries/bulk", {
        method: "POST",
        token,
        body: JSON.stringify({ enabled }),
      });
      setCountries(list);
      onLog();
    } catch (e: any) {
      setError(e.message || "Gagal memperbarui semua negara");
    } finally {
      setBusy("");
    }
  };

  if (loading) {
    return (
      <View style={s.center} testID="country-loading">
        <ActivityIndicator color={C.amber} />
        <Text style={s.muted}>Memuat daftar negara...</Text>
      </View>
    );
  }

  return (
    <View style={{ flex: 1 }}>
      <View style={s.header}>
        <Text style={s.kicker}>TARGET MARKET / COUNTRY</Text>
        <Text style={s.pageTitle}>Pilih Negara</Text>
        <Text style={s.muted}>
          {activeCount} dari {countries.length} negara aktif · Semua data disimpan di server.
        </Text>
        <View style={s.searchWrap}>
          <Icon name="magnify" size={18} color={C.muted} />
          <TextInput
            testID="country-search"
            value={query}
            onChangeText={setQuery}
            placeholder="Cari negara..."
            placeholderTextColor={C.muted}
            autoCapitalize="none"
            style={s.search}
          />
          {query ? (
            <Pressable onPress={() => setQuery("")} testID="clear-search">
              <Icon name="close-circle" size={18} color={C.muted} />
            </Pressable>
          ) : null}
        </View>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={s.chipsRow}>
          {regions.map((r) => (
            <Pressable
              testID={`region-${r}`}
              key={r}
              onPress={() => setRegion(r)}
              style={[s.regionChip, region === r && s.regionChipActive]}
            >
              <Text style={[s.regionText, region === r && { color: C.amber }]}>{r}</Text>
            </Pressable>
          ))}
        </ScrollView>
        {isAdmin && (
          <View style={s.actions}>
            <Pressable testID="country-select-all" style={s.small} onPress={() => bulk(true)} disabled={!!busy}>
              <Text style={s.smallText}>PILIH SEMUA</Text>
            </Pressable>
            <Pressable testID="country-clear-all" style={s.small} onPress={() => bulk(false)} disabled={!!busy}>
              <Text style={s.smallText}>HAPUS SEMUA</Text>
            </Pressable>
          </View>
        )}
        {error ? <Toast message={error} tone="error" /> : null}
      </View>

      <ScrollView contentContainerStyle={s.list} testID="country-scroll">
        <Text style={s.section}>
          {filtered.length} HASIL · {filteredActive} AKTIF
        </Text>
        {filtered.length === 0 ? (
          <Text style={s.muted}>Tidak ada negara sesuai pencarian.</Text>
        ) : (
          filtered.map((c) => {
            const isBusy = busy === c.code;
            return (
              <Pressable
                key={c.code}
                testID={`country-row-${c.code}`}
                onPress={() => toggle(c)}
                disabled={!isAdmin || !!busy}
                style={[s.row, c.enabled && s.rowActive]}
              >
                <View style={s.codeBadge}>
                  <Text style={s.codeText}>{c.code}</Text>
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={s.rowName}>{c.name}</Text>
                  <Text style={s.muted}>{c.region}</Text>
                </View>
                <Status on={c.enabled} text={c.enabled ? "ON" : "OFF"} />
                <View style={[s.check, c.enabled && s.checkOn]}>
                  {isBusy ? (
                    <ActivityIndicator size="small" color={c.enabled ? C.bg : C.amber} />
                  ) : c.enabled ? (
                    <Icon name="check" size={16} color={C.bg} />
                  ) : null}
                </View>
              </Pressable>
            );
          })
        )}
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  center: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: C.bg, gap: 8 },
  header: { padding: 20, gap: 10, borderBottomWidth: 1, borderColor: C.line, backgroundColor: C.bg },
  kicker: { color: C.amber, fontSize: 10, letterSpacing: 1.2, fontWeight: "800" },
  pageTitle: { color: C.text, fontSize: 26, fontWeight: "900" },
  muted: { color: C.muted, fontSize: 13, lineHeight: 20 },
  searchWrap: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    borderWidth: 1,
    borderColor: C.line,
    backgroundColor: C.card,
    paddingHorizontal: 12,
    marginTop: 4,
  },
  search: { flex: 1, color: C.text, padding: 12, fontSize: 14 },
  chipsRow: { gap: 8, paddingVertical: 4 },
  regionChip: {
    height: 36,
    paddingHorizontal: 14,
    borderWidth: 1,
    borderColor: C.line,
    justifyContent: "center",
    flexShrink: 0,
  },
  regionChipActive: { borderColor: C.amber, backgroundColor: C.amberSoft },
  regionText: { color: C.muted, fontSize: 12, fontWeight: "800" },
  actions: { flexDirection: "row", gap: 8, marginTop: 4 },
  small: { borderWidth: 1, borderColor: C.amber, padding: 12, flex: 1, alignItems: "center" },
  smallText: { color: C.amber, fontSize: 11, fontWeight: "900" },
  list: { padding: 20, paddingBottom: 48, gap: 8 },
  section: { color: C.text, fontSize: 11, fontWeight: "900", letterSpacing: 1 },
  row: {
    backgroundColor: C.card,
    borderWidth: 1,
    borderColor: C.line,
    padding: 12,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  rowActive: { borderColor: C.amber, backgroundColor: C.amberSoft },
  codeBadge: {
    width: 42,
    height: 42,
    borderWidth: 1,
    borderColor: C.line,
    alignItems: "center",
    justifyContent: "center",
  },
  codeText: { color: C.text, fontWeight: "900", fontSize: 13 },
  rowName: { color: C.text, fontSize: 15, fontWeight: "800" },
  check: {
    width: 28,
    height: 28,
    borderWidth: 1,
    borderColor: C.line,
    alignItems: "center",
    justifyContent: "center",
  },
  checkOn: { backgroundColor: C.amber, borderColor: C.amber },
});
