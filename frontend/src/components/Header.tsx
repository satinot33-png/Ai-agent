import { MaterialCommunityIcons as Icon } from "@expo/vector-icons";
import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { C, Screen } from "@/src/theme";
import { User } from "@/src/types";

export function Header({ screen, user, onMenu }: { screen: Screen; user: User; onMenu: () => void }) {
  const initial = (user.name || user.username || "U")[0].toUpperCase();
  return (
    <View style={s.wrap}>
      <Pressable testID="open-drawer" onPress={onMenu} style={s.iconBtn} hitSlop={8}>
        <Icon name="menu" size={26} color={C.text} />
      </Pressable>
      <View style={{ flex: 1 }}>
        <Text style={s.kicker}>EXPORT 7 AI</Text>
        <Text testID="screen-title" style={s.title}>{screen}</Text>
      </View>
      <View style={s.avatar} testID="user-avatar">
        <Text style={s.avatarText}>{initial}</Text>
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  wrap: {
    height: 78,
    borderBottomWidth: 1,
    borderColor: C.line,
    paddingHorizontal: 16,
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: C.bg,
  },
  iconBtn: { width: 44, justifyContent: "center" },
  kicker: { color: C.amber, fontSize: 10, letterSpacing: 1.2, fontWeight: "800" },
  title: { color: C.text, fontSize: 18, fontWeight: "800", marginTop: 3 },
  avatar: { width: 34, height: 34, backgroundColor: C.amber, alignItems: "center", justifyContent: "center", borderRadius: 6 },
  avatarText: { color: C.bg, fontWeight: "900" },
});
