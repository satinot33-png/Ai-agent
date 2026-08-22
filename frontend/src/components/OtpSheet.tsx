import { MaterialCommunityIcons as Icon } from "@expo/vector-icons";
import React, { useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { api } from "@/src/api";
import { Toast } from "@/src/components/Feedback";
import { C } from "@/src/theme";

type Props = {
  open: boolean;
  username: string;
  whatsapp?: string;
  provider?: string;
  hint?: string | null;
  onVerified?: (session?: string) => void;
  onResend: () => Promise<{ code?: string | null; provider?: string } | undefined>;
  onClose: () => void;
  requestSession?: boolean;
};

export function OtpSheet({
  open,
  username,
  whatsapp,
  provider,
  hint,
  onVerified,
  onResend,
  onClose,
  requestSession,
}: Props) {
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [devHint, setDevHint] = useState<string | null>(hint || null);

  React.useEffect(() => {
    setDevHint(hint || null);
    setCode("");
    setError("");
    setOk("");
  }, [hint, open]);

  if (!open) return null;

  const verify = async () => {
    if (code.length < 4) {
      setError("Kode OTP minimal 4 digit.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const res = await api<{ session_token: string }>("/auth/verify-otp", {
        method: "POST",
        body: JSON.stringify({ username, code }),
      });
      setOk("Verifikasi berhasil.");
      onVerified?.(requestSession ? res.session_token : undefined);
    } catch (e: any) {
      setError(e.message || "Gagal memverifikasi OTP");
    } finally {
      setBusy(false);
    }
  };

  const resend = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await onResend();
      if (res?.code) setDevHint(res.code);
      setOk("OTP baru telah dikirim.");
    } catch (e: any) {
      setError(e.message || "Gagal mengirim ulang OTP");
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={s.wrap} testID="otp-sheet">
      <Pressable style={s.backdrop} onPress={onClose} />
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <View style={s.sheet}>
          <View style={s.header}>
            <Icon name="whatsapp" size={26} color="#25D366" />
            <View style={{ flex: 1 }}>
              <Text style={s.title}>Verifikasi OTP WhatsApp</Text>
              <Text style={s.muted}>
                Kode telah dikirim ke {whatsapp || "nomor WhatsApp terdaftar"} · via {provider || "mock"}
              </Text>
            </View>
            <Pressable onPress={onClose} testID="otp-close">
              <Icon name="close" size={22} color={C.muted} />
            </Pressable>
          </View>

          {devHint ? (
            <View style={s.hintBox}>
              <Text style={s.hintLabel}>MOCK OTP (dev mode)</Text>
              <Text style={s.hintCode}>{devHint}</Text>
              <Text style={s.muted}>Set WA_PROVIDER=fonnte di backend/.env untuk kirim ke WA sungguhan.</Text>
            </View>
          ) : null}

          <TextInput
            testID="otp-input"
            value={code}
            onChangeText={(v) => setCode(v.replace(/\D/g, "").slice(0, 6))}
            placeholder="6 digit kode"
            placeholderTextColor={C.muted}
            keyboardType="number-pad"
            style={s.input}
            autoFocus
          />

          {error ? <Toast message={error} tone="error" /> : null}
          {ok ? <Toast message={ok} tone="success" /> : null}

          <View style={s.actions}>
            <Pressable testID="otp-resend" onPress={resend} disabled={busy} style={s.ghost}>
              <Text style={s.ghostText}>{busy ? "..." : "KIRIM ULANG"}</Text>
            </Pressable>
            <Pressable testID="otp-verify" onPress={verify} disabled={busy} style={s.primary}>
              {busy ? <ActivityIndicator color={C.bg} /> : <Text style={s.primaryText}>VERIFIKASI</Text>}
            </Pressable>
          </View>
        </View>
      </KeyboardAvoidingView>
    </View>
  );
}

const s = StyleSheet.create({
  wrap: { ...StyleSheet.absoluteFillObject, justifyContent: "flex-end", zIndex: 40 },
  backdrop: { ...StyleSheet.absoluteFillObject, backgroundColor: "rgba(0,0,0,.7)" },
  sheet: { backgroundColor: C.card, borderTopWidth: 2, borderColor: C.amber, padding: 22, gap: 12 },
  header: { flexDirection: "row", alignItems: "center", gap: 12 },
  title: { color: C.text, fontSize: 17, fontWeight: "900" },
  muted: { color: C.muted, fontSize: 12, lineHeight: 18 },
  hintBox: { borderWidth: 1, borderColor: C.amber, backgroundColor: C.amberSoft, padding: 12, gap: 4 },
  hintLabel: { color: C.amber, fontSize: 10, fontWeight: "900", letterSpacing: 1 },
  hintCode: { color: C.text, fontSize: 24, fontWeight: "900", letterSpacing: 6 },
  input: {
    backgroundColor: C.bg,
    borderWidth: 1,
    borderColor: C.line,
    color: C.text,
    padding: 14,
    fontSize: 20,
    letterSpacing: 8,
    textAlign: "center",
    fontWeight: "800",
  },
  actions: { flexDirection: "row", gap: 10 },
  ghost: { flex: 1, minHeight: 48, borderWidth: 1, borderColor: C.line, alignItems: "center", justifyContent: "center" },
  ghostText: { color: C.muted, fontWeight: "900", fontSize: 12 },
  primary: { flex: 2, minHeight: 48, backgroundColor: C.amber, alignItems: "center", justifyContent: "center" },
  primaryText: { color: C.bg, fontWeight: "900", fontSize: 13 },
});
