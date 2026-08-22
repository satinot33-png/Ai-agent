import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { C } from "@/src/theme";

export function Status({ on, text, tone }: { on: boolean; text: string; tone?: "ok" | "warn" | "error" }) {
  const color = tone === "warn" ? C.yellow : tone === "error" ? C.red : on ? C.green : C.red;
  return (
    <View style={s.wrap} testID={`status-${text.toLowerCase()}`}>
      <View style={[s.dot, { backgroundColor: color }]} />
      <Text style={[s.text, { color }]}>{text}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  wrap: { flexDirection: "row", gap: 6, alignItems: "center" },
  dot: { width: 8, height: 8, borderRadius: 8 },
  text: { fontSize: 11, fontWeight: "900", letterSpacing: 0.5 },
});
