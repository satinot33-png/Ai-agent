import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { C } from "@/src/theme";

export function Toast({ message, tone = "info" }: { message: string; tone?: "info" | "error" | "success" }) {
  if (!message) return null;
  const color = tone === "error" ? C.red : tone === "success" ? C.green : C.blue;
  return (
    <View testID="toast" style={[s.wrap, { borderColor: color }]}>
      <View style={[s.bar, { backgroundColor: color }]} />
      <Text style={s.text}>{message}</Text>
    </View>
  );
}

export function ConfirmSheet({
  open,
  title,
  body,
  confirmText,
  danger,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  body: string;
  confirmText: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <View style={s.sheetWrap} testID="confirm-sheet">
      <Pressable style={s.sheetBackdrop} onPress={onCancel} />
      <View style={s.sheet}>
        <Text style={s.sheetTitle}>{title}</Text>
        <Text style={s.sheetBody}>{body}</Text>
        <View style={s.row}>
          <Pressable testID="confirm-cancel" style={s.btnGhost} onPress={onCancel}>
            <Text style={s.btnGhostText}>BATAL</Text>
          </Pressable>
          <Pressable
            testID="confirm-yes"
            style={[s.btnPrimary, danger && { backgroundColor: C.red }]}
            onPress={onConfirm}
          >
            <Text style={[s.btnPrimaryText, danger && { color: "#fff" }]}>{confirmText}</Text>
          </Pressable>
        </View>
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  wrap: {
    flexDirection: "row",
    backgroundColor: C.card,
    borderWidth: 1,
    padding: 12,
    marginHorizontal: 20,
    marginTop: 8,
  },
  bar: { width: 3, marginRight: 10 },
  text: { color: C.text, flex: 1, fontSize: 13 },
  sheetWrap: { ...StyleSheet.absoluteFillObject, justifyContent: "flex-end", zIndex: 30 },
  sheetBackdrop: { ...StyleSheet.absoluteFillObject, backgroundColor: "rgba(0,0,0,.7)" },
  sheet: { backgroundColor: C.card, borderTopWidth: 2, borderColor: C.amber, padding: 22, gap: 12 },
  sheetTitle: { color: C.text, fontSize: 18, fontWeight: "900" },
  sheetBody: { color: C.muted, fontSize: 14, lineHeight: 20 },
  row: { flexDirection: "row", gap: 10, marginTop: 8 },
  btnGhost: {
    flex: 1,
    minHeight: 48,
    borderWidth: 1,
    borderColor: C.line,
    justifyContent: "center",
    alignItems: "center",
  },
  btnGhostText: { color: C.muted, fontWeight: "800", fontSize: 12 },
  btnPrimary: {
    flex: 1,
    minHeight: 48,
    backgroundColor: C.amber,
    justifyContent: "center",
    alignItems: "center",
  },
  btnPrimaryText: { color: C.bg, fontWeight: "900", fontSize: 12 },
});
