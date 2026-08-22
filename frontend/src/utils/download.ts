import { File, Paths } from "expo-file-system";
import * as Sharing from "expo-sharing";
import { Platform } from "react-native";
import { API_BASE } from "@/src/api";

export async function downloadPdf(path: string, token: string, filename: string) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, { method: "POST", headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || `Gagal mengunduh PDF (${res.status})`);
  }
  const blob = await res.blob();

  if (Platform.OS === "web") {
    const objUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(objUrl), 1000);
    return { path: filename, method: "web" as const };
  }

  const buffer = await blob.arrayBuffer();
  const file = new File(Paths.cache, filename);
  if (file.exists) file.delete();
  file.create();
  file.write(new Uint8Array(buffer));
  if (await Sharing.isAvailableAsync()) {
    await Sharing.shareAsync(file.uri, {
      mimeType: "application/pdf",
      UTI: "com.adobe.pdf",
      dialogTitle: filename,
    });
  }
  return { path: file.uri, method: "native" as const };
}
