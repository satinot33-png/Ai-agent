import * as Linking from "expo-linking";
import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Platform, SafeAreaView, StatusBar, StyleSheet, Text, View } from "react-native";
import { api } from "@/src/api";
import { Drawer } from "@/src/components/Drawer";
import { Header } from "@/src/components/Header";
import { AccessPage } from "@/src/screens/AccessPage";
import { AIPage } from "@/src/screens/AIPage";
import { CountryPage } from "@/src/screens/CountryPage";
import { Dashboard } from "@/src/screens/Dashboard";
import { InterrogationPage } from "@/src/screens/InterrogationPage";
import { Login } from "@/src/screens/Login";
import { ServerPage } from "@/src/screens/ServerPage";
import { SettingsPage } from "@/src/screens/SettingsPage";
import { C, Screen } from "@/src/theme";
import { DashboardData, User } from "@/src/types";
import { storage } from "@/src/utils/storage";

const TOKEN_KEY = "export7ai.session_token";

export default function ControlCenter() {
  const [token, setToken] = useState<string>();
  const [user, setUser] = useState<User>();
  const [dashboard, setDashboard] = useState<DashboardData>();
  const [screen, setScreen] = useState<Screen>("Dashboard");
  const [drawer, setDrawer] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshTick, setRefreshTick] = useState(0);

  const loadDashboard = useCallback(async (t: string) => {
    try {
      setDashboard(await api<DashboardData>("/dashboard", { token: t }));
    } catch (e) {
      // If token invalid, clear it
      const msg = (e as Error).message || "";
      if (msg.toLowerCase().includes("token") || msg.toLowerCase().includes("sesi")) {
        await storage.secureRemove(TOKEN_KEY);
        setToken(undefined);
        setUser(undefined);
      }
    }
  }, []);

  // Boot: try existing token or catch OAuth redirect
  useEffect(() => {
    (async () => {
      try {
        const url =
          Platform.OS === "web"
            ? `${window.location.hash}${window.location.search}`
            : (await Linking.getInitialURL()) || "";
        const sid = url.match(/[?#&]session_id=([^&#]+)/)?.[1];
        if (sid) {
          const r = await api<{ session_token: string; user: User }>("/auth/session", {
            method: "POST",
            body: JSON.stringify({ session_id: decodeURIComponent(sid) }),
          });
          await storage.secureSet(TOKEN_KEY, r.session_token);
          setToken(r.session_token);
          setUser(r.user);
        } else {
          const saved = await storage.secureGet<string | null>(TOKEN_KEY, null);
          if (saved) {
            const me = await api<User>("/auth/me", { token: saved });
            setToken(saved);
            setUser(me);
          }
        }
      } catch {
        await storage.secureRemove(TOKEN_KEY);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  useEffect(() => {
    if (token) loadDashboard(token);
  }, [token, loadDashboard, refreshTick]);

  const handleLogin = async (t: string, u: User) => {
    await storage.secureSet(TOKEN_KEY, t);
    setToken(t);
    setUser(u);
  };

  const handleLogout = async () => {
    if (token) {
      try {
        await api("/auth/logout", { method: "POST", token });
      } catch {
        /* ignore */
      }
    }
    await storage.secureRemove(TOKEN_KEY);
    setToken(undefined);
    setUser(undefined);
    setDashboard(undefined);
    setScreen("Dashboard");
    setDrawer(false);
  };

  const bump = () => setRefreshTick((x) => x + 1);

  if (loading) {
    return (
      <View style={s.splash} testID="app-loading">
        <StatusBar barStyle="light-content" backgroundColor={C.bg} />
        <ActivityIndicator color={C.amber} />
        <Text style={s.muted}>Menghubungkan control center...</Text>
      </View>
    );
  }

  if (!token || !user) {
    return <Login onDone={handleLogin} />;
  }

  const body = (() => {
    switch (screen) {
      case "Dashboard":
        return dashboard ? (
          <Dashboard data={dashboard} go={setScreen} token={token} />
        ) : (
          <View style={s.center}>
            <ActivityIndicator color={C.amber} />
          </View>
        );
      case "7 AI":
        return <AIPage token={token} user={user} onLog={bump} />;
      case "Pilih Negara":
        return <CountryPage token={token} user={user} onLog={bump} />;
      case "Server":
        return <ServerPage token={token} user={user} onLog={bump} />;
      case "Interogasi Server":
        return <InterrogationPage token={token} user={user} onLog={bump} />;
      case "Akses / User":
        return <AccessPage token={token} user={user} onLog={bump} />;
      case "Pengaturan":
        return <SettingsPage token={token} user={user} onLogout={handleLogout} />;
    }
  })();

  return (
    <SafeAreaView style={s.app}>
      <StatusBar barStyle="light-content" backgroundColor={C.bg} />
      <Header screen={screen} user={user} onMenu={() => setDrawer(true)} />
      <View style={{ flex: 1 }}>{body}</View>
      {drawer && (
        <Drawer
          screen={screen}
          user={user}
          onSelect={(item) => {
            setScreen(item);
            setDrawer(false);
          }}
          onClose={() => setDrawer(false)}
          onLogout={handleLogout}
        />
      )}
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  app: { flex: 1, backgroundColor: C.bg },
  splash: { flex: 1, backgroundColor: C.bg, justifyContent: "center", alignItems: "center", gap: 12 },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  muted: { color: C.muted, fontSize: 13 },
});
