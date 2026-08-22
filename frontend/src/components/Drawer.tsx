import { MaterialCommunityIcons as Icon } from "@expo/vector-icons";
import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { C, Screen, SCREENS } from "@/src/theme";
import { User } from "@/src/types";

const ICONS: Record<Screen, string> = {
  Dashboard: "view-dashboard-outline",
  "7 AI": "robot-outline",
  "Pilih Negara": "earth",
  Server: "server-network",
  "Interogasi Server": "shield-search",
  "Akses / User": "account-multiple-outline",
  Pengaturan: "cog-outline",
};

export function Drawer({
  screen,
  user,
  onSelect,
  onClose,
  onLogout,
}: {
  screen: Screen;
  user: User;
  onSelect: (s: Screen) => void;
  onClose: () => void;
  onLogout: () => void;
}) {
  return (
    <View style={s.overlay}>
      <Pressable testID="drawer-backdrop" style={s.backdrop} onPress={onClose} />
      <View style={s.drawer}>
        <Text style={s.brand}>
          EXPORT <Text style={{ color: C.amber }}>7 AI</Text>
        </Text>
        <Text style={s.role}>{user.role}</Text>
        <View style={{ marginTop: 20, gap: 4 }}>
          {SCREENS.map((item) => (
            <Pressable
              testID={`menu-${item}`}
              key={item}
              onPress={() => onSelect(item)}
              style={[s.item, item === screen && s.itemActive]}
            >
              <Icon
                name={ICONS[item] as any}
                size={20}
                color={item === screen ? C.amber : C.muted}
              />
              <Text style={[s.itemText, item === screen && { color: C.amber }]}>{item}</Text>
            </Pressable>
          ))}
        </View>
        <View style={s.bottom}>
          <Text style={s.muted}>{user.email || user.username}</Text>
          <Pressable testID="logout-btn" onPress={onLogout} style={s.logout}>
            <Icon name="logout" size={18} color={C.red} />
            <Text style={{ color: C.red, fontWeight: "800" }}>KELUAR</Text>
          </Pressable>
        </View>
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  overlay: { ...StyleSheet.absoluteFillObject, flexDirection: "row", zIndex: 20 },
  backdrop: { flex: 1, backgroundColor: "rgba(0,0,0,.7)" },
  drawer: {
    width: 285,
    backgroundColor: C.card,
    padding: 22,
    paddingTop: 48,
    borderRightWidth: 1,
    borderColor: C.line,
  },
  brand: { color: C.text, fontSize: 22, fontWeight: "900" },
  role: { color: C.amber, fontSize: 11, fontWeight: "900", letterSpacing: 1, marginTop: 6 },
  item: {
    minHeight: 48,
    paddingHorizontal: 12,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    borderRadius: 6,
  },
  itemActive: { backgroundColor: C.amberSoft, borderLeftWidth: 2, borderLeftColor: C.amber },
  itemText: { color: C.text, fontSize: 14, fontWeight: "700" },
  bottom: { marginTop: "auto", gap: 14, borderTopWidth: 1, borderColor: C.line, paddingTop: 16 },
  muted: { color: C.muted, fontSize: 12 },
  logout: { flexDirection: "row", alignItems: "center", gap: 8 },
});
