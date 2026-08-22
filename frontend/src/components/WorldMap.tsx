import React, { useMemo } from "react";
import { StyleSheet, Text, View } from "react-native";
import Svg, { Circle, Path, Rect } from "react-native-svg";
import { C } from "@/src/theme";
import { Country } from "@/src/types";

// Simplified world continent outlines (equirectangular projection).
// Scaled to a 360x180 viewBox — 1 unit ≈ 1 degree of longitude/latitude.
// Not geographically precise, but visually recognisable as a world map.
const CONTINENTS = [
  // North America
  "M 65,32 L 100,28 L 135,30 L 155,45 L 148,68 L 130,80 L 110,88 L 95,92 L 88,95 L 82,105 L 75,110 L 68,105 L 62,90 L 60,75 L 58,60 L 55,45 Z",
  // Central America
  "M 118,102 L 130,100 L 138,108 L 132,118 L 122,116 Z",
  // South America
  "M 140,115 L 158,112 L 168,125 L 172,140 L 168,158 L 158,170 L 145,168 L 138,152 L 138,135 Z",
  // Africa
  "M 205,95 L 232,90 L 245,98 L 250,120 L 245,140 L 232,155 L 218,158 L 208,148 L 200,130 L 198,110 Z",
  // Europe
  "M 190,58 L 215,52 L 232,55 L 240,68 L 232,82 L 215,85 L 200,82 L 190,75 Z",
  // Middle East
  "M 232,85 L 250,82 L 258,92 L 252,102 L 240,102 L 232,95 Z",
  // Russia / North Asia (long horizontal band)
  "M 215,42 L 275,38 L 315,42 L 335,52 L 325,60 L 285,62 L 245,58 L 215,55 Z",
  // South Asia (India)
  "M 258,95 L 275,92 L 283,105 L 278,120 L 265,120 L 258,108 Z",
  // South East Asia + Indonesia
  "M 285,105 L 305,102 L 315,115 L 320,128 L 315,138 L 300,135 L 288,125 L 285,115 Z",
  // East Asia (China / Japan / Korea)
  "M 285,68 L 315,62 L 330,72 L 325,88 L 310,95 L 295,92 L 288,80 Z",
  // Australia + New Zealand
  "M 305,150 L 330,148 L 342,158 L 335,170 L 315,168 L 305,160 Z",
];

const VIEW_W = 360;
const VIEW_H = 180;

function project(lat: number, lng: number): { x: number; y: number } {
  const x = ((lng + 180) / 360) * VIEW_W;
  const y = ((90 - lat) / 180) * VIEW_H;
  return { x, y };
}

export function WorldMap({ countries }: { countries: Country[] }) {
  const { activeCount, totalCount, byRegion } = useMemo(() => {
    const total = countries.length;
    const active = countries.filter((c) => c.enabled);
    const grp: Record<string, number> = {};
    for (const c of active) grp[c.region] = (grp[c.region] || 0) + 1;
    return { activeCount: active.length, totalCount: total, byRegion: grp };
  }, [countries]);

  return (
    <View style={s.card} testID="world-map">
      <View style={s.head}>
        <View style={{ flex: 1 }}>
          <Text style={s.muted}>TARGET NEGARA · PETA GLOBAL</Text>
          <Text style={s.title}>
            {activeCount} <Text style={s.mutedInline}>/ {totalCount} negara aktif</Text>
          </Text>
        </View>
      </View>

      <View style={s.mapWrap}>
        <Svg viewBox={`0 0 ${VIEW_W} ${VIEW_H}`} width="100%" height={180}>
          <Rect x={0} y={0} width={VIEW_W} height={VIEW_H} fill={C.bg} />
          {/* Grid latitude lines (subtle) */}
          {[45, 90, 135].map((y) => (
            <Path
              key={`h-${y}`}
              d={`M 0 ${y} L ${VIEW_W} ${y}`}
              stroke={C.line}
              strokeWidth={0.25}
              opacity={0.35}
            />
          ))}
          {[90, 180, 270].map((x) => (
            <Path
              key={`v-${x}`}
              d={`M ${x} 0 L ${x} ${VIEW_H}`}
              stroke={C.line}
              strokeWidth={0.25}
              opacity={0.35}
            />
          ))}
          {/* Continent silhouettes */}
          {CONTINENTS.map((d, i) => (
            <Path key={i} d={d} fill={C.cardAlt} stroke={C.line} strokeWidth={0.4} />
          ))}
          {/* Country dots */}
          {countries.map((c) => {
            if (c.lat == null || c.lng == null) return null;
            const { x, y } = project(c.lat, c.lng);
            if (c.enabled) {
              return (
                <React.Fragment key={c.code}>
                  <Circle cx={x} cy={y} r={4} fill={C.amber} opacity={0.25} />
                  <Circle cx={x} cy={y} r={2.2} fill={C.amber} />
                </React.Fragment>
              );
            }
            return <Circle key={c.code} cx={x} cy={y} r={1.4} fill={C.muted} opacity={0.55} />;
          })}
        </Svg>
      </View>

      <View style={s.regionRow}>
        {Object.entries(byRegion).length === 0 ? (
          <Text style={s.muted}>Belum ada negara aktif. Buka Pilih Negara untuk mengaktifkan.</Text>
        ) : (
          Object.entries(byRegion).map(([region, count]) => (
            <View key={region} style={s.regionPill} testID={`region-pill-${region}`}>
              <View style={s.pillDot} />
              <Text style={s.pillText}>
                {region}
                <Text style={s.pillCount}> · {count}</Text>
              </Text>
            </View>
          ))
        )}
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  card: { backgroundColor: C.card, borderWidth: 1, borderColor: C.line, padding: 14, gap: 10 },
  head: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" },
  muted: { color: C.muted, fontSize: 10, letterSpacing: 1, fontWeight: "800" },
  mutedInline: { color: C.muted, fontSize: 14, fontWeight: "700" },
  title: { color: C.amber, fontSize: 20, fontWeight: "900", marginTop: 4 },
  mapWrap: { backgroundColor: C.bg, borderWidth: 1, borderColor: C.line, overflow: "hidden" },
  regionRow: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  regionPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    borderWidth: 1,
    borderColor: C.amber,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  pillDot: { width: 6, height: 6, borderRadius: 6, backgroundColor: C.amber },
  pillText: { color: C.amber, fontSize: 11, fontWeight: "800" },
  pillCount: { color: C.muted, fontWeight: "700" },
});
