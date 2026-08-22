import { MaterialCommunityIcons as Icon } from "@expo/vector-icons";
import React, { useCallback, useEffect, useState } from "react";
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
import { Toast } from "@/src/components/Feedback";
import { C } from "@/src/theme";
import { Recipient } from "@/src/types";

type Props = {
  open: boolean;
  token: string;
  mode: "summary" | "detailed";
  onClose: () => void;
  onSent: (r: { recipient: string; message_id?: string }) => void;
};

export function EmailReportSheet({ open, token, mode, onClose, onSent }: Props) {
  const [recipients, setRecipients] = useState<Recipient[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [addOpen, setAddOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newNote, setNewNote] = useState("");

  const load = useCallback(async () => {
    try {
      const rows = await api<Recipient[]>("/settings/recipients", { token });
      setRecipients(rows);
      if (rows.length && !selected) setSelected(rows[0].recipient_id);
      if (rows.length === 0) setAddOpen(true);
    } catch (e: any) {
      setError(e.message || "Gagal memuat penerima");
    }
  }, [token, selected]);

  useEffect(() => {
    if (open) {
      load();
      setError("");
      setOk("");
    }
  }, [open, load]);

  if (!open) return null;

  const send = async () => {
    if (!selected) {
      setError("Pilih penerima terlebih dulu.");
      return;
    }
    setBusy(true);
    setError("");
    setOk("");
    try {
      const res = await api<{ recipient: string; message_id?: string; subject: string }>(
        "/interrogation/email",
        {
          method: "POST",
          token,
          body: JSON.stringify({ recipient_id: selected, mode, note: note.trim() || undefined }),
        },
      );
      setOk(`Email terkirim ke ${res.recipient}. Subject: ${res.subject}`);
      onSent({ recipient: res.recipient, message_id: res.message_id });
    } catch (e: any) {
      setError(e.message || "Gagal mengirim email");
    } finally {
      setBusy(false);
    }
  };

  const addRecipient = async () => {
    setError("");
    if (newName.trim().length < 2) {
      setError("Nama minimal 2 karakter.");
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(newEmail)) {
      setError("Format email tidak valid.");
      return;
    }
    setBusy(true);
    try {
      const rcp = await api<Recipient>("/settings/recipients", {
        method: "POST",
        token,
        body: JSON.stringify({ name: newName.trim(), email: newEmail.trim(), note: newNote.trim() || undefined }),
      });
      setRecipients((prev) => [...prev, rcp]);
      setSelected(rcp.recipient_id);
      setNewName("");
      setNewEmail("");
      setNewNote("");
      setAddOpen(false);
      setOk("Penerima berhasil ditambahkan.");
    } catch (e: any) {
      setError(e.message || "Gagal menambah penerima");
    } finally {
      setBusy(false);
    }
  };

  const removeRecipient = async (id: string) => {
    try {
      await api(`/settings/recipients/${id}`, { method: "DELETE", token });
      setRecipients((prev) => prev.filter((r) => r.recipient_id !== id));
      if (selected === id) setSelected("");
    } catch (e: any) {
      setError(e.message || "Gagal menghapus penerima");
    }
  };

  return (
    <View style={s.wrap} testID="email-sheet">
      <Pressable style={s.backdrop} onPress={onClose} />
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <View style={s.sheet}>
          <View style={s.head}>
            <Icon name="email-fast-outline" size={26} color={C.amber} />
            <View style={{ flex: 1 }}>
              <Text style={s.title}>Kirim Laporan ke Email</Text>
              <Text style={s.muted}>PDF {mode === "summary" ? "Ringkas" : "Detail 24 Jam"} akan dilampirkan.</Text>
            </View>
            <Pressable testID="email-close" onPress={onClose}>
              <Icon name="close" size={22} color={C.muted} />
            </Pressable>
          </View>

          <View style={s.section}>
            <View style={s.sectionHead}>
              <Text style={s.label}>PENERIMA</Text>
              <Pressable testID="add-recipient-toggle" onPress={() => setAddOpen((v) => !v)}>
                <Text style={s.link}>{addOpen ? "TUTUP" : "+ TAMBAH"}</Text>
              </Pressable>
            </View>
            {addOpen ? (
              <View style={s.addBox}>
                <TextInput
                  testID="recipient-name"
                  value={newName}
                  onChangeText={setNewName}
                  placeholder="Nama (mis. Pak Direktur)"
                  placeholderTextColor={C.muted}
                  style={s.input}
                />
                <TextInput
                  testID="recipient-email"
                  value={newEmail}
                  onChangeText={setNewEmail}
                  placeholder="email@perusahaan.com"
                  placeholderTextColor={C.muted}
                  keyboardType="email-address"
                  autoCapitalize="none"
                  style={s.input}
                />
                <TextInput
                  testID="recipient-note"
                  value={newNote}
                  onChangeText={setNewNote}
                  placeholder="Catatan (opsional)"
                  placeholderTextColor={C.muted}
                  style={s.input}
                />
                <Pressable testID="save-recipient" onPress={addRecipient} disabled={busy} style={s.ghost}>
                  {busy ? <ActivityIndicator color={C.amber} /> : <Text style={s.ghostText}>SIMPAN PENERIMA</Text>}
                </Pressable>
              </View>
            ) : null}

            <ScrollView style={{ maxHeight: 180 }}>
              {recipients.length === 0 ? (
                <Text style={s.muted}>Belum ada penerima. Tambahkan minimal satu.</Text>
              ) : (
                recipients.map((r) => (
                  <Pressable
                    key={r.recipient_id}
                    testID={`recipient-${r.recipient_id}`}
                    onPress={() => setSelected(r.recipient_id)}
                    style={[s.recipient, selected === r.recipient_id && s.recipientOn]}
                  >
                    <View style={[s.radio, selected === r.recipient_id && s.radioOn]}>
                      {selected === r.recipient_id ? <View style={s.radioDot} /> : null}
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={s.recipientName}>{r.name}</Text>
                      <Text style={s.muted} numberOfLines={1}>
                        {r.email} {r.note ? `· ${r.note}` : ""}
                      </Text>
                    </View>
                    <Pressable
                      testID={`delete-recipient-${r.recipient_id}`}
                      onPress={() => removeRecipient(r.recipient_id)}
                    >
                      <Icon name="trash-can-outline" size={18} color={C.red} />
                    </Pressable>
                  </Pressable>
                ))
              )}
            </ScrollView>
          </View>

          <TextInput
            testID="email-note"
            value={note}
            onChangeText={setNote}
            placeholder="Catatan singkat untuk penerima (opsional, max 280)"
            placeholderTextColor={C.muted}
            multiline
            maxLength={280}
            style={[s.input, { minHeight: 60, textAlignVertical: "top" }]}
          />

          {error ? <Toast message={error} tone="error" /> : null}
          {ok ? <Toast message={ok} tone="success" /> : null}

          <View style={s.actions}>
            <Pressable testID="email-cancel" onPress={onClose} style={s.ghost}>
              <Text style={s.ghostText}>TUTUP</Text>
            </Pressable>
            <Pressable
              testID="email-send"
              onPress={send}
              disabled={busy || !selected}
              style={[s.primary, (busy || !selected) && { opacity: 0.5 }]}
            >
              {busy ? (
                <ActivityIndicator color={C.bg} />
              ) : (
                <>
                  <Icon name="send" size={16} color={C.bg} />
                  <Text style={s.primaryText}>KIRIM SEKARANG</Text>
                </>
              )}
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
  sheet: { backgroundColor: C.card, borderTopWidth: 2, borderColor: C.amber, padding: 20, gap: 12, maxHeight: 640 },
  head: { flexDirection: "row", alignItems: "center", gap: 12 },
  title: { color: C.text, fontSize: 17, fontWeight: "900" },
  muted: { color: C.muted, fontSize: 12, lineHeight: 18 },
  label: { color: C.muted, fontSize: 10, letterSpacing: 1, fontWeight: "800" },
  link: { color: C.amber, fontSize: 11, fontWeight: "900" },
  section: { borderWidth: 1, borderColor: C.line, backgroundColor: C.bg, padding: 10, gap: 8 },
  sectionHead: { flexDirection: "row", justifyContent: "space-between" },
  addBox: { gap: 8, paddingBottom: 8, borderBottomWidth: 1, borderColor: C.line },
  input: {
    backgroundColor: C.card,
    borderWidth: 1,
    borderColor: C.line,
    color: C.text,
    padding: 10,
    fontSize: 13,
  },
  recipient: {
    flexDirection: "row",
    alignItems: "center",
    padding: 10,
    gap: 10,
    borderWidth: 1,
    borderColor: "transparent",
  },
  recipientOn: { backgroundColor: C.amberSoft, borderColor: C.amber },
  radio: {
    width: 18,
    height: 18,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: C.line,
    alignItems: "center",
    justifyContent: "center",
  },
  radioOn: { borderColor: C.amber },
  radioDot: { width: 10, height: 10, borderRadius: 10, backgroundColor: C.amber },
  recipientName: { color: C.text, fontSize: 14, fontWeight: "800" },
  actions: { flexDirection: "row", gap: 10 },
  ghost: { flex: 1, minHeight: 48, borderWidth: 1, borderColor: C.line, alignItems: "center", justifyContent: "center" },
  ghostText: { color: C.muted, fontWeight: "900", fontSize: 12 },
  primary: { flex: 2, minHeight: 48, backgroundColor: C.amber, flexDirection: "row", gap: 8, alignItems: "center", justifyContent: "center" },
  primaryText: { color: C.bg, fontWeight: "900", fontSize: 13 },
});
