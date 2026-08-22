import { MaterialCommunityIcons as Icon } from "@expo/vector-icons";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { api } from "@/src/api";
import { MultiSelect } from "@/src/components/MultiSelect";
import { OtpSheet } from "@/src/components/OtpSheet";
import { Status } from "@/src/components/Status";
import { ConfirmSheet, Toast } from "@/src/components/Feedback";
import { C } from "@/src/theme";
import { AIAgent, Country, Province, User } from "@/src/types";

type FormState = {
  name: string;
  username: string;
  email: string;
  whatsapp: string;
  password: string;
  role: "SUPER ADMIN" | "ADMIN" | "KARYAWAN";
  allowed_ais: string[];
  allowed_countries: string[];
  allowed_provinces: string[];
  access_start: string;
  access_end: string;
  enabled: boolean;
};

const EMPTY: FormState = {
  name: "",
  username: "",
  email: "",
  whatsapp: "",
  password: "",
  role: "KARYAWAN",
  allowed_ais: [],
  allowed_countries: [],
  allowed_provinces: [],
  access_start: "",
  access_end: "",
  enabled: true,
};

const ROLE_OPTIONS: FormState["role"][] = ["SUPER ADMIN", "ADMIN", "KARYAWAN"];

export function AccessPage({ token, user, onLog }: { token: string; user: User; onLog: () => void }) {
  const isAdmin = ["SUPER ADMIN", "ADMIN"].includes(String(user.role).toUpperCase());
  const isSuper = String(user.role).toUpperCase() === "SUPER ADMIN";
  const [users, setUsers] = useState<User[]>([]);
  const [ais, setAis] = useState<AIAgent[]>([]);
  const [countries, setCountries] = useState<Country[]>([]);
  const [provinces, setProvinces] = useState<Province[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [editing, setEditing] = useState<string | undefined>();
  const [form, setForm] = useState<FormState>(EMPTY);
  const [toDelete, setToDelete] = useState<User | null>(null);
  const [otp, setOtp] = useState<{
    open: boolean;
    username: string;
    whatsapp?: string;
    provider?: string;
    hint?: string | null;
    userId?: string;
  }>({ open: false, username: "" });

  const load = useCallback(async () => {
    setError("");
    try {
      const [u, a, c, p] = await Promise.all([
        api<User[]>("/users", { token }),
        api<AIAgent[]>("/ai", { token }),
        api<Country[]>("/countries", { token }),
        api<Province[]>("/provinces", { token }),
      ]);
      setUsers(u);
      setAis(a);
      setCountries(c);
      setProvinces(p);
    } catch (e: any) {
      setError(e.message || "Gagal memuat data akses");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const resetForm = () => {
    setEditing(undefined);
    setForm(EMPTY);
  };

  const startEdit = (item: User) => {
    setEditing(item.user_id);
    setForm({
      name: item.name || "",
      username: item.username || "",
      email: item.email || "",
      whatsapp: item.whatsapp || "",
      password: "",
      role: (["SUPER ADMIN", "ADMIN", "KARYAWAN"].includes(String(item.role)) ? item.role : "KARYAWAN") as any,
      allowed_ais: item.allowed_ais || [],
      allowed_countries: item.allowed_countries || [],
      allowed_provinces: item.allowed_provinces || [],
      access_start: item.access_start || "",
      access_end: item.access_end || "",
      enabled: item.enabled !== false,
    });
  };

  const validate = (): string | null => {
    if (form.name.trim().length < 2) return "Nama minimal 2 karakter.";
    if (!/^[a-zA-Z0-9_.-]{3,40}$/.test(form.username)) return "Username 3-40 karakter (huruf/angka/_/.-)";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) return "Format email tidak valid.";
    if (form.whatsapp.replace(/\D/g, "").length < 8) return "Nomor WhatsApp minimal 8 digit.";
    if (!editing && form.password.length < 8) return "Password minimal 8 karakter.";
    if (editing && form.password && form.password.length < 8) return "Password baru minimal 8 karakter.";
    if (form.access_start && form.access_end && form.access_start > form.access_end)
      return "Tanggal akhir harus setelah tanggal mulai.";
    return null;
  };

  const save = async () => {
    const v = validate();
    if (v) {
      setError(v);
      return;
    }
    setError("");
    setOk("");
    setBusy(true);
    try {
      const payload: any = {
        name: form.name.trim(),
        email: form.email.trim(),
        whatsapp: form.whatsapp.trim(),
        role: form.role,
        allowed_ais: form.allowed_ais,
        allowed_countries: form.allowed_countries,
        allowed_provinces: form.allowed_provinces,
        access_start: form.access_start || null,
        access_end: form.access_end || null,
        enabled: form.enabled,
      };
      if (editing) {
        if (form.password) payload.password = form.password;
        await api(`/users/${editing}`, { method: "PATCH", token, body: JSON.stringify(payload) });
        setOk("Data user diperbarui.");
      } else {
        payload.username = form.username.trim();
        payload.password = form.password;
        const res = await api<{ user: User; otp: { code?: string | null; provider: string; delivered_to: string } }>(
          "/users",
          { method: "POST", token, body: JSON.stringify(payload) },
        );
        setOk("User baru dibuat. OTP dikirim ke WhatsApp untuk aktivasi.");
        setOtp({
          open: true,
          username: res.user.username || "",
          whatsapp: res.user.whatsapp,
          provider: res.otp.provider,
          hint: res.otp.code || null,
          userId: res.user.user_id,
        });
      }
      resetForm();
      await load();
      onLog();
    } catch (e: any) {
      setError(e.message || "Gagal menyimpan user");
    } finally {
      setBusy(false);
    }
  };

  const toggle = async (item: User) => {
    setError("");
    try {
      await api(`/users/${item.user_id}/status`, {
        method: "PATCH",
        token,
        body: JSON.stringify({ enabled: item.enabled === false }),
      });
      await load();
      onLog();
    } catch (e: any) {
      setError(e.message || "Gagal mengubah status");
    }
  };

  const confirmDelete = async () => {
    if (!toDelete) return;
    const id = toDelete.user_id!;
    setToDelete(null);
    try {
      await api(`/users/${id}`, { method: "DELETE", token });
      await load();
      onLog();
    } catch (e: any) {
      setError(e.message || "Gagal menghapus user");
    }
  };

  const aiOptions = useMemo(() => ais.map((a) => ({ key: a.agent_id, label: a.name, sub: a.function })), [ais]);
  const countryOptions = useMemo(
    () => countries.map((c) => ({ key: c.code, label: c.name, sub: c.region })),
    [countries],
  );
  const provinceOptions = useMemo(() => provinces.map((p) => ({ key: p.name, label: p.name })), [provinces]);

  if (!isAdmin) {
    return (
      <ScrollView contentContainerStyle={s.content}>
        <Text style={s.kicker}>ACCESS CONTROL</Text>
        <Text style={s.pageTitle}>Akses / User</Text>
        <Text style={s.muted}>Anda tidak memiliki izin untuk mengelola user.</Text>
      </ScrollView>
    );
  }

  if (loading) {
    return (
      <View style={s.center} testID="access-loading">
        <ActivityIndicator color={C.amber} />
        <Text style={s.muted}>Memuat data akses...</Text>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1 }}>
      <ScrollView contentContainerStyle={s.content} testID="access-scroll" keyboardShouldPersistTaps="handled">
        <Text style={s.kicker}>ACCESS CONTROL / RBAC</Text>
        <Text style={s.pageTitle}>{editing ? "Edit User" : "User Baru"}</Text>
        <Text style={s.muted}>
          Semua field wajib diisi. Password disimpan terhash di server, tidak pernah dikirim balik ke aplikasi.
        </Text>

        <View style={s.form}>
          <Field label="Nama Lengkap" testID="user-input-name" value={form.name} onChange={(v) => setForm({ ...form, name: v })} />
          <Field
            label="Username"
            testID="user-input-username"
            value={form.username}
            onChange={(v) => setForm({ ...form, username: v })}
            editable={!editing}
            autoCap="none"
            hint={editing ? "Username tidak dapat diubah." : undefined}
          />
          <Field
            label="Email"
            testID="user-input-email"
            value={form.email}
            onChange={(v) => setForm({ ...form, email: v })}
            keyboard="email-address"
            autoCap="none"
          />
          <Field
            label="Nomor WhatsApp"
            testID="user-input-whatsapp"
            value={form.whatsapp}
            onChange={(v) => setForm({ ...form, whatsapp: v })}
            keyboard="phone-pad"
            placeholder="+62..."
          />
          <Field
            label={editing ? "Password Baru (kosongkan jika tidak diubah)" : "Password (min. 8 karakter)"}
            testID="user-input-password"
            value={form.password}
            onChange={(v) => setForm({ ...form, password: v })}
            secure
            autoCap="none"
          />

          <Text style={s.label}>ROLE / HAK AKSES</Text>
          <View style={s.roleRow}>
            {ROLE_OPTIONS.map((r) => {
              const disabled = r === "SUPER ADMIN" && !isSuper;
              return (
                <Pressable
                  testID={`role-${r.replace(" ", "-")}`}
                  key={r}
                  disabled={disabled}
                  onPress={() => setForm({ ...form, role: r })}
                  style={[s.role, form.role === r && s.roleActive, disabled && { opacity: 0.4 }]}
                >
                  <Text style={[s.smallText, form.role === r && { color: C.amber }]}>{r}</Text>
                </Pressable>
              );
            })}
          </View>

          <View style={s.dateRow}>
            <View style={{ flex: 1 }}>
              <Field
                label="Akses Mulai (YYYY-MM-DD)"
                testID="user-input-access-start"
                value={form.access_start}
                onChange={(v) => setForm({ ...form, access_start: v })}
                placeholder="2026-01-01"
                autoCap="none"
              />
            </View>
            <View style={{ flex: 1 }}>
              <Field
                label="Akses Berakhir"
                testID="user-input-access-end"
                value={form.access_end}
                onChange={(v) => setForm({ ...form, access_end: v })}
                placeholder="2026-12-31"
                autoCap="none"
              />
            </View>
          </View>

          <MultiSelect
            testID="user-ais"
            label="AI YANG DIIZINKAN"
            values={aiOptions}
            selected={form.allowed_ais}
            onToggle={(k) =>
              setForm((f) => ({
                ...f,
                allowed_ais: f.allowed_ais.includes(k) ? f.allowed_ais.filter((x) => x !== k) : [...f.allowed_ais, k],
              }))
            }
            onAll={() => setForm({ ...form, allowed_ais: ais.map((a) => a.agent_id) })}
            onClear={() => setForm({ ...form, allowed_ais: [] })}
            formatter={(k) => ais.find((a) => a.agent_id === k)?.name || k}
          />

          <MultiSelect
            testID="user-countries"
            label="NEGARA YANG DIIZINKAN"
            values={countryOptions}
            selected={form.allowed_countries}
            onToggle={(k) =>
              setForm((f) => ({
                ...f,
                allowed_countries: f.allowed_countries.includes(k)
                  ? f.allowed_countries.filter((x) => x !== k)
                  : [...f.allowed_countries, k],
              }))
            }
            onAll={() => setForm({ ...form, allowed_countries: countries.map((c) => c.code) })}
            onClear={() => setForm({ ...form, allowed_countries: [] })}
            formatter={(k) => countries.find((c) => c.code === k)?.name || k}
          />

          <MultiSelect
            testID="user-provinces"
            label="PROVINSI (INDONESIA)"
            values={provinceOptions}
            selected={form.allowed_provinces}
            onToggle={(k) =>
              setForm((f) => ({
                ...f,
                allowed_provinces: f.allowed_provinces.includes(k)
                  ? f.allowed_provinces.filter((x) => x !== k)
                  : [...f.allowed_provinces, k],
              }))
            }
            onAll={() => setForm({ ...form, allowed_provinces: provinces.map((p) => p.name) })}
            onClear={() => setForm({ ...form, allowed_provinces: [] })}
          />

          <View style={s.switchRow}>
            <Text style={s.label}>AKUN AKTIF</Text>
            <Pressable
              testID="user-input-enabled"
              onPress={() => setForm({ ...form, enabled: !form.enabled })}
              style={[s.switch, form.enabled && s.switchOn]}
            >
              <View style={[s.knob, form.enabled && s.knobOn]} />
            </Pressable>
          </View>

          {error ? <Toast message={error} tone="error" /> : null}
          {ok ? <Toast message={ok} tone="success" /> : null}

          <View style={s.formActions}>
            {editing ? (
              <Pressable testID="cancel-edit" style={s.ghost} onPress={resetForm}>
                <Text style={s.ghostText}>BATAL EDIT</Text>
              </Pressable>
            ) : null}
            <Pressable testID="save-user" style={[s.primary, busy && { opacity: 0.6 }]} onPress={save} disabled={busy}>
              {busy ? (
                <ActivityIndicator color={C.bg} />
              ) : (
                <Text style={s.primaryText}>{editing ? "SIMPAN PERUBAHAN" : "SIMPAN USER"}</Text>
              )}
            </Pressable>
          </View>
        </View>

        <Text style={s.section}>DAFTAR USER ({users.length})</Text>
        {users.map((item) => (
          <View style={s.userRow} key={item.user_id} testID={`user-${item.user_id}`}>
            <View style={{ flex: 1, gap: 4 }}>
              <View style={s.rowBetween}>
                <Text style={s.userName}>{item.name}</Text>
                <Status on={item.enabled !== false} text={item.enabled !== false ? "ON" : "OFF"} />
              </View>
              <Text style={s.userMeta}>
                @{item.username} · {item.role}
              </Text>
              <Text style={s.muted} numberOfLines={1}>
                {item.email} · {item.whatsapp || "-"}
              </Text>
              <Text style={s.muted}>
                AI: {(item.allowed_ais || []).length} · Negara: {(item.allowed_countries || []).length} · Provinsi:{" "}
                {(item.allowed_provinces || []).length}
              </Text>
              {(item.access_start || item.access_end) && (
                <Text style={s.muted}>
                  Akses: {item.access_start || "—"} → {item.access_end || "—"}
                </Text>
              )}
              {(item as any).pending_activation ? (
                <Pressable
                  testID={`resend-otp-${item.user_id}`}
                  onPress={async () => {
                    try {
                      const res = await api<{ delivery: { code?: string | null; provider: string; delivered_to: string } }>(
                        `/users/${item.user_id}/otp/resend`,
                        { method: "POST", token },
                      );
                      setOtp({
                        open: true,
                        username: item.username || "",
                        whatsapp: item.whatsapp,
                        provider: res.delivery.provider,
                        hint: res.delivery.code || null,
                        userId: item.user_id,
                      });
                    } catch (e: any) {
                      setError(e.message || "Gagal kirim ulang OTP");
                    }
                  }}
                  style={s.pendingBadge}
                >
                  <Icon name="whatsapp" size={13} color="#25D366" />
                  <Text style={s.pendingText}>PENDING OTP · KIRIM ULANG</Text>
                </Pressable>
              ) : null}
            </View>
            <View style={s.userActions}>
              <Pressable testID={`toggle-user-${item.user_id}`} onPress={() => toggle(item)} style={s.iconBtn}>
                <Icon
                  name={item.enabled !== false ? "toggle-switch" : "toggle-switch-off-outline"}
                  size={22}
                  color={item.enabled !== false ? C.green : C.muted}
                />
              </Pressable>
              <Pressable testID={`edit-user-${item.user_id}`} onPress={() => startEdit(item)} style={s.iconBtn}>
                <Icon name="pencil-outline" size={20} color={C.amber} />
              </Pressable>
              {item.user_id !== user.user_id ? (
                <Pressable
                  testID={`delete-user-${item.user_id}`}
                  onPress={() => setToDelete(item)}
                  style={s.iconBtn}
                >
                  <Icon name="trash-can-outline" size={20} color={C.red} />
                </Pressable>
              ) : null}
            </View>
          </View>
        ))}

        <ConfirmSheet
          open={!!toDelete}
          title={`Hapus ${toDelete?.name || ""}?`}
          body="User akan dihapus permanen dari database dan tercatat di audit log."
          confirmText="HAPUS"
          danger
          onConfirm={confirmDelete}
          onCancel={() => setToDelete(null)}
        />
        <OtpSheet
          open={otp.open}
          username={otp.username}
          whatsapp={otp.whatsapp}
          provider={otp.provider}
          hint={otp.hint}
          onClose={() => setOtp((o) => ({ ...o, open: false }))}
          onVerified={async () => {
            setOtp((o) => ({ ...o, open: false }));
            setOk("Akun berhasil diaktivasi.");
            await load();
            onLog();
          }}
          onResend={async () => {
            if (!otp.userId) return undefined;
            const res = await api<{ delivery: { code?: string | null; provider: string } }>(
              `/users/${otp.userId}/otp/resend`,
              { method: "POST", token },
            );
            return { code: res.delivery.code || undefined, provider: res.delivery.provider };
          }}
        />
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function Field(props: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  testID: string;
  secure?: boolean;
  keyboard?: "default" | "email-address" | "phone-pad";
  placeholder?: string;
  autoCap?: "none" | "sentences";
  editable?: boolean;
  hint?: string;
}) {
  return (
    <View style={{ gap: 4 }}>
      <Text style={s.label}>{props.label}</Text>
      <TextInput
        testID={props.testID}
        value={props.value}
        onChangeText={props.onChange}
        secureTextEntry={props.secure}
        keyboardType={props.keyboard}
        placeholder={props.placeholder || ""}
        placeholderTextColor={C.muted}
        autoCapitalize={props.autoCap || "sentences"}
        autoCorrect={false}
        editable={props.editable !== false}
        style={[s.input, props.editable === false && { opacity: 0.55 }]}
      />
      {props.hint ? <Text style={s.hint}>{props.hint}</Text> : null}
    </View>
  );
}

const s = StyleSheet.create({
  content: { padding: 20, paddingBottom: 64, gap: 12 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: C.bg, gap: 8 },
  kicker: { color: C.amber, fontSize: 10, letterSpacing: 1.2, fontWeight: "800" },
  pageTitle: { color: C.text, fontSize: 24, fontWeight: "900" },
  muted: { color: C.muted, fontSize: 12, lineHeight: 18 },
  hint: { color: C.muted, fontSize: 11, fontStyle: "italic" },
  form: { backgroundColor: C.card, borderWidth: 1, borderColor: C.line, padding: 14, gap: 10 },
  input: {
    backgroundColor: C.bg,
    borderWidth: 1,
    borderColor: C.line,
    color: C.text,
    padding: 12,
    fontSize: 14,
  },
  label: { color: C.muted, fontSize: 10, fontWeight: "800", letterSpacing: 1 },
  roleRow: { flexDirection: "row", gap: 6 },
  role: { borderWidth: 1, borderColor: C.line, padding: 10, flex: 1, alignItems: "center" },
  roleActive: { borderColor: C.amber, backgroundColor: C.amberSoft },
  smallText: { color: C.muted, fontSize: 11, fontWeight: "900" },
  dateRow: { flexDirection: "row", gap: 8 },
  switchRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 4 },
  switch: {
    width: 52,
    height: 30,
    borderRadius: 30,
    backgroundColor: C.line,
    justifyContent: "center",
    padding: 3,
  },
  switchOn: { backgroundColor: C.amber },
  knob: { width: 24, height: 24, borderRadius: 24, backgroundColor: C.muted },
  knobOn: { alignSelf: "flex-end", backgroundColor: C.bg },
  formActions: { flexDirection: "row", gap: 8, marginTop: 8 },
  ghost: { flex: 1, minHeight: 50, borderWidth: 1, borderColor: C.line, alignItems: "center", justifyContent: "center" },
  ghostText: { color: C.muted, fontWeight: "900", fontSize: 12 },
  primary: { flex: 2, minHeight: 50, backgroundColor: C.amber, alignItems: "center", justifyContent: "center" },
  primaryText: { color: C.bg, fontWeight: "900", fontSize: 13 },
  section: { color: C.text, fontSize: 12, fontWeight: "900", letterSpacing: 1, marginTop: 6 },
  userRow: {
    backgroundColor: C.card,
    borderWidth: 1,
    borderColor: C.line,
    padding: 14,
    flexDirection: "row",
    gap: 10,
  },
  rowBetween: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  userName: { color: C.text, fontSize: 15, fontWeight: "900" },
  userMeta: { color: C.amber, fontSize: 12, fontWeight: "700" },
  userActions: { justifyContent: "space-between", gap: 6 },
  iconBtn: { padding: 4 },
  pendingBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    borderWidth: 1,
    borderColor: "#25D366",
    paddingHorizontal: 8,
    paddingVertical: 4,
    alignSelf: "flex-start",
    marginTop: 4,
  },
  pendingText: { color: "#25D366", fontSize: 10, fontWeight: "900", letterSpacing: 0.5 },
});
