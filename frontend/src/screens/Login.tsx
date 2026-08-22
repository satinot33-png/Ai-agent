import { MaterialCommunityIcons as Icon } from "@expo/vector-icons";
import * as Linking from "expo-linking";
import * as WebBrowser from "expo-web-browser";
import React, { useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { api } from "@/src/api";
import { OtpSheet } from "@/src/components/OtpSheet";
import { C } from "@/src/theme";
import { User } from "@/src/types";
import { Toast } from "@/src/components/Feedback";

WebBrowser.maybeCompleteAuthSession();

type Props = { onDone: (token: string, user: User) => Promise<void> | void };

export function Login({ onDone }: Props) {
  const [mode, setMode] = useState<"password" | "google">("password");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [otp, setOtp] = useState<{ open: boolean; provider?: string; hint?: string | null }>({ open: false });

  const loginPassword = async () => {
    setError("");
    if (!username.trim() || !password) {
      setError("Isi username dan password.");
      return;
    }
    setBusy(true);
    try {
      const data = await api<{ session_token: string; user: User }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username: username.trim(), password }),
      });
      await onDone(data.session_token, data.user);
    } catch (e: any) {
      const msg = e.message || "Login gagal";
      if (/aktivasi|aktifasi|belum diaktivasi|OTP/i.test(msg)) {
        setError("Akun belum diaktivasi. Verifikasi OTP di bawah.");
        try {
          const res = await api<{ delivery: { code?: string | null; provider: string } }>(
            "/auth/resend-otp",
            { method: "POST", body: JSON.stringify({ username: username.trim() }) },
          );
          setOtp({ open: true, provider: res.delivery.provider, hint: res.delivery.code || null });
        } catch {
          setOtp({ open: true });
        }
      } else {
        setError(msg);
      }
    } finally {
      setBusy(false);
    }
  };

  const loginGoogle = async () => {
    setError("");
    setBusy(true);
    try {
      const redirect = Platform.OS === "web" ? `${window.location.origin}/` : Linking.createURL("");
      if (Platform.OS === "web") {
        window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirect)}`;
        return;
      }
      let eventUrl = "";
      const listener = Linking.addEventListener("url", (e) => {
        eventUrl = e.url;
      });
      const result = await WebBrowser.openAuthSessionAsync(
        `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirect)}`,
        redirect,
      );
      listener.remove();
      const callback =
        result.type === "success" ? result.url : eventUrl || (await Linking.getInitialURL()) || "";
      const id = callback.match(/[?#&]session_id=([^&#]+)/)?.[1];
      if (!id) throw new Error("Sesi Google belum diterima.");
      const data = await api<{ session_token: string; user: User }>("/auth/session", {
        method: "POST",
        body: JSON.stringify({ session_id: decodeURIComponent(id) }),
      });
      await onDone(data.session_token, data.user);
    } catch (e: any) {
      setError(e.message || "Login Google gagal");
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={s.root}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={s.scroll} keyboardShouldPersistTaps="handled">
          <Icon name="orbit" size={38} color={C.amber} />
          <Text style={s.kicker}>EXPORT OPERATIONS / CONTROL CENTER</Text>
          <Text style={s.title}>Export 7 AI</Text>
          <Text style={s.copy}>
            Kendalikan operasi 7 AI, target pasar, dan kesehatan server dari satu tempat.
          </Text>

          <View style={s.tabs}>
            <Pressable
              testID="tab-password"
              onPress={() => setMode("password")}
              style={[s.tab, mode === "password" && s.tabActive]}
            >
              <Text style={[s.tabText, mode === "password" && { color: C.amber }]}>USERNAME</Text>
            </Pressable>
            <Pressable
              testID="tab-google"
              onPress={() => setMode("google")}
              style={[s.tab, mode === "google" && s.tabActive]}
            >
              <Text style={[s.tabText, mode === "google" && { color: C.amber }]}>GOOGLE</Text>
            </Pressable>
          </View>

          {mode === "password" ? (
            <View style={s.card}>
              <Text style={s.cardTitle}>Akses terproteksi</Text>
              <Text style={s.muted}>Gunakan akun yang dibuat oleh admin.</Text>
              <TextInput
                testID="login-username"
                value={username}
                onChangeText={setUsername}
                placeholder="Username"
                placeholderTextColor={C.muted}
                autoCapitalize="none"
                autoCorrect={false}
                style={s.input}
              />
              <TextInput
                testID="login-password"
                value={password}
                onChangeText={setPassword}
                placeholder="Password"
                placeholderTextColor={C.muted}
                secureTextEntry
                style={s.input}
              />
              <Pressable testID="login-submit" style={s.primary} onPress={loginPassword} disabled={busy}>
                {busy ? (
                  <ActivityIndicator color={C.bg} />
                ) : (
                  <Text style={s.primaryText}>MASUK</Text>
                )}
              </Pressable>
              <Text style={s.hint}>Contoh: superadmin / SuperAdmin@2026</Text>
            </View>
          ) : (
            <View style={s.card}>
              <Text style={s.cardTitle}>Masuk dengan Google</Text>
              <Text style={s.muted}>Gunakan akun Google yang terdaftar sebagai operator.</Text>
              <Pressable testID="google-login-button" style={s.primary} onPress={loginGoogle} disabled={busy}>
                {busy ? (
                  <ActivityIndicator color={C.bg} />
                ) : (
                  <>
                    <Icon name="google" size={18} color={C.bg} />
                    <Text style={s.primaryText}>MASUK DENGAN GOOGLE</Text>
                  </>
                )}
              </Pressable>
            </View>
          )}
          {error ? <Toast message={error} tone="error" /> : null}
        </ScrollView>
      </KeyboardAvoidingView>
      <OtpSheet
        open={otp.open}
        username={username.trim()}
        provider={otp.provider}
        hint={otp.hint}
        requestSession
        onClose={() => setOtp({ open: false })}
        onVerified={async (session) => {
          setOtp({ open: false });
          if (session) {
            const me = await api<User>("/auth/me", { token: session });
            await onDone(session, me);
          }
        }}
        onResend={async () => {
          const res = await api<{ delivery: { code?: string | null; provider: string } }>(
            "/auth/resend-otp",
            { method: "POST", body: JSON.stringify({ username: username.trim() }) },
          );
          return { code: res.delivery.code || undefined, provider: res.delivery.provider };
        }}
      />
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  scroll: { padding: 28, paddingTop: 48, gap: 12 },
  kicker: { color: C.amber, fontSize: 10, letterSpacing: 1.2, fontWeight: "800", marginTop: 12 },
  title: { color: C.text, fontSize: 36, fontWeight: "900", marginTop: 4 },
  copy: { color: C.muted, fontSize: 15, lineHeight: 22, marginTop: 8 },
  tabs: { flexDirection: "row", marginTop: 24, borderWidth: 1, borderColor: C.line },
  tab: { flex: 1, paddingVertical: 12, alignItems: "center" },
  tabActive: { backgroundColor: C.amberSoft, borderBottomWidth: 2, borderColor: C.amber },
  tabText: { color: C.muted, fontWeight: "900", fontSize: 11, letterSpacing: 1 },
  card: { backgroundColor: C.card, borderWidth: 1, borderColor: C.line, padding: 20, gap: 12, marginTop: 12 },
  cardTitle: { color: C.text, fontSize: 16, fontWeight: "800" },
  muted: { color: C.muted, fontSize: 13, lineHeight: 20 },
  input: {
    backgroundColor: C.bg,
    borderWidth: 1,
    borderColor: C.line,
    color: C.text,
    padding: 14,
    fontSize: 15,
  },
  primary: {
    minHeight: 50,
    backgroundColor: C.amber,
    justifyContent: "center",
    alignItems: "center",
    flexDirection: "row",
    gap: 9,
    marginTop: 6,
  },
  primaryText: { color: C.bg, fontWeight: "900", fontSize: 13 },
  hint: { color: C.muted, fontSize: 11, marginTop: 4 },
});
