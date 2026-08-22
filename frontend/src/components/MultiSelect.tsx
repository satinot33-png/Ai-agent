import { MaterialCommunityIcons as Icon } from "@expo/vector-icons";
import React from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { C } from "@/src/theme";

export function MultiSelect({
  label,
  values,
  selected,
  onToggle,
  onAll,
  onClear,
  formatter,
  testID,
}: {
  label: string;
  values: { key: string; label: string; sub?: string }[];
  selected: string[];
  onToggle: (v: string) => void;
  onAll?: () => void;
  onClear?: () => void;
  formatter?: (v: string) => string;
  testID: string;
}) {
  return (
    <View style={s.wrap} testID={testID}>
      <View style={s.head}>
        <Text style={s.label}>{label}</Text>
        <View style={{ flexDirection: "row", gap: 8 }}>
          {onAll && (
            <Pressable testID={`${testID}-all`} onPress={onAll}>
              <Text style={s.link}>SEMUA</Text>
            </Pressable>
          )}
          {onClear && (
            <Pressable testID={`${testID}-clear`} onPress={onClear}>
              <Text style={[s.link, { color: C.red }]}>HAPUS</Text>
            </Pressable>
          )}
        </View>
      </View>
      <ScrollView style={{ maxHeight: 210 }} nestedScrollEnabled>
        {values.length === 0 ? (
          <Text style={s.muted}>Daftar kosong.</Text>
        ) : (
          values.map((v) => {
            const on = selected.includes(v.key);
            return (
              <Pressable
                key={v.key}
                testID={`${testID}-${v.key}`}
                onPress={() => onToggle(v.key)}
                style={[s.row, on && s.rowOn]}
              >
                <View style={[s.check, on && s.checkOn]}>
                  {on ? <Icon name="check" size={13} color={C.bg} /> : null}
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={s.rowText}>{v.label}</Text>
                  {v.sub ? <Text style={s.muted}>{v.sub}</Text> : null}
                </View>
              </Pressable>
            );
          })
        )}
      </ScrollView>
      {selected.length > 0 ? (
        <Text style={s.count}>
          {selected.length} dipilih
          {formatter ? ` · ${selected.slice(0, 3).map(formatter).join(", ")}` : ""}
          {selected.length > 3 ? "..." : ""}
        </Text>
      ) : (
        <Text style={s.count}>Belum ada pilihan</Text>
      )}
    </View>
  );
}

const s = StyleSheet.create({
  wrap: { borderWidth: 1, borderColor: C.line, backgroundColor: C.bg, padding: 8, gap: 6 },
  head: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: 4 },
  label: { color: C.muted, fontSize: 10, fontWeight: "800", letterSpacing: 1 },
  link: { color: C.amber, fontSize: 10, fontWeight: "900" },
  row: {
    flexDirection: "row",
    alignItems: "center",
    padding: 10,
    gap: 10,
    borderBottomWidth: 1,
    borderColor: "transparent",
  },
  rowOn: { backgroundColor: C.amberSoft },
  rowText: { color: C.text, fontSize: 14, fontWeight: "700" },
  check: {
    width: 20,
    height: 20,
    borderWidth: 1,
    borderColor: C.line,
    alignItems: "center",
    justifyContent: "center",
  },
  checkOn: { backgroundColor: C.amber, borderColor: C.amber },
  muted: { color: C.muted, fontSize: 12, padding: 8 },
  count: { color: C.amber, fontSize: 11, fontWeight: "800", paddingHorizontal: 4 },
});
