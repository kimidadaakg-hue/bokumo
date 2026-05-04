"use client";

import { useMemo } from "react";
import type { Shop } from "@/types/shop";

interface Props {
  shops: Shop[];
  region: string;       // 大エリア
  subRegion: string;    // 中エリア
  microRegion: string;  // 小エリア
  setRegion: (r: string) => void;
  setSubRegion: (r: string) => void;
  setMicroRegion: (r: string) => void;
}

// 3階層マッピング: 大エリア → 中エリア → 小エリア(area値の配列)
interface SubArea {
  label: string;
  areas: string[];       // data の area 値にマッチ
  micro?: { label: string; areas: string[] }[];
}

const REGION_MAP: Record<string, SubArea[]> = {
  札幌: [
    {
      label: "中央区",
      areas: ["札幌中央区", "大通", "すすきの", "札幌駅周辺", "中島公園・山鼻", "円山", "宮の森"],
      micro: [
        { label: "大通", areas: ["大通"] },
        { label: "すすきの", areas: ["すすきの"] },
        { label: "札幌駅周辺", areas: ["札幌駅周辺"] },
        { label: "中島公園・山鼻", areas: ["中島公園・山鼻"] },
        { label: "円山", areas: ["円山"] },
        { label: "宮の森", areas: ["宮の森"] },
      ],
    },
    {
      label: "北区",
      areas: ["札幌北区", "札幌北区南部", "札幌北区北部", "麻生・新琴似"],
      micro: [
        { label: "北区南部", areas: ["札幌北区南部"] },
        { label: "北区北部", areas: ["札幌北区北部"] },
        { label: "麻生・新琴似", areas: ["麻生・新琴似"] },
      ],
    },
    { label: "東区", areas: ["札幌東区"] },
    { label: "白石区", areas: ["札幌白石区"] },
    { label: "厚別区", areas: ["札幌厚別区"] },
    {
      label: "豊平区",
      areas: ["札幌豊平区", "平岸", "月寒・美園", "豊平"],
      micro: [
        { label: "平岸", areas: ["平岸"] },
        { label: "月寒・美園", areas: ["月寒・美園"] },
        { label: "豊平", areas: ["豊平"] },
      ],
    },
    { label: "清田区", areas: ["札幌清田区"] },
    { label: "南区", areas: ["札幌南区"] },
    { label: "西区", areas: ["札幌西区"] },
    { label: "手稲区", areas: ["札幌手稲区"] },
  ],
  小樽: [
    {
      label: "小樽",
      areas: ["小樽", "小樽駅周辺", "小樽運河・堺町"],
      micro: [
        { label: "小樽駅周辺", areas: ["小樽駅周辺"] },
        { label: "運河・堺町", areas: ["小樽運河・堺町"] },
      ],
    },
  ],
  道央: [
    { label: "千歳", areas: ["千歳"] },
    { label: "恵庭", areas: ["恵庭"] },
    { label: "江別", areas: ["江別"] },
    { label: "石狩", areas: ["石狩"] },
    { label: "岩見沢", areas: ["岩見沢"] },
    { label: "北広島", areas: ["北広島"] },
    { label: "滝川", areas: ["滝川"] },
    { label: "砂川", areas: ["砂川"] },
    { label: "芦別", areas: ["芦別"] },
    { label: "深川", areas: ["深川"] },
    { label: "美唄", areas: ["美唄"] },
    { label: "三笠", areas: ["三笠"] },
    { label: "赤平", areas: ["赤平"] },
    { label: "倶知安", areas: ["倶知安"] },
    { label: "余市", areas: ["余市"] },
  ],
  道南: [
    {
      label: "函館",
      areas: ["函館", "五稜郭", "函館駅前", "函館ベイエリア", "函館郊外"],
      micro: [
        { label: "五稜郭", areas: ["五稜郭"] },
        { label: "函館駅前", areas: ["函館駅前"] },
        { label: "ベイエリア", areas: ["函館ベイエリア"] },
        { label: "函館郊外", areas: ["函館郊外"] },
      ],
    },
    { label: "室蘭", areas: ["室蘭"] },
    { label: "苫小牧", areas: ["苫小牧"] },
    { label: "伊達", areas: ["伊達"] },
    { label: "登別", areas: ["登別"] },
    { label: "七飯", areas: ["七飯"] },
    { label: "八雲", areas: ["八雲"] },
    { label: "白老", areas: ["白老"] },
    { label: "むかわ", areas: ["むかわ"] },
    { label: "新ひだか", areas: ["新ひだか"] },
    { label: "浦河", areas: ["浦河"] },
  ],
  旭川: [
    {
      label: "旭川",
      areas: ["旭川", "旭川駅周辺", "旭川郊外", "旭川永山", "旭川神楽"],
      micro: [
        { label: "旭川駅周辺", areas: ["旭川駅周辺"] },
        { label: "旭川郊外", areas: ["旭川郊外"] },
        { label: "永山", areas: ["旭川永山"] },
        { label: "神楽", areas: ["旭川神楽"] },
      ],
    },
    { label: "富良野", areas: ["富良野"] },
    { label: "美瑛", areas: ["美瑛"] },
    { label: "東川", areas: ["東川"] },
  ],
  道北: [
    { label: "稚内", areas: ["稚内"] },
    { label: "名寄", areas: ["名寄"] },
    { label: "留萌", areas: ["留萌"] },
    { label: "士別", areas: ["士別"] },
  ],
  帯広: [
    { label: "帯広", areas: ["帯広"] },
    { label: "芽室", areas: ["芽室"] },
    { label: "広尾", areas: ["広尾"] },
  ],
  釧路: [
    { label: "釧路", areas: ["釧路"] },
    { label: "根室", areas: ["根室"] },
    { label: "中標津", areas: ["中標津"] },
    { label: "弟子屈", areas: ["弟子屈"] },
    { label: "羅臼", areas: ["羅臼"] },
    { label: "厚岸", areas: ["厚岸"] },
  ],
  オホーツク: [
    { label: "北見", areas: ["北見"] },
    { label: "網走", areas: ["網走"] },
    { label: "紋別", areas: ["紋別"] },
  ],
};

const REGION_ORDER = ["すべて", "札幌", "小樽", "道央", "道南", "旭川", "道北", "帯広", "釧路", "オホーツク"];

// 大エリアに属する全area値を取得
export function getAreasForRegion(region: string, subRegion: string, microRegion: string): string[] | null {
  if (region === "すべて") return null; // null = フィルタなし

  const subs = REGION_MAP[region];
  if (!subs) return null;

  if (subRegion) {
    const sub = subs.find((s) => s.label === subRegion);
    if (!sub) return null;

    if (microRegion && sub.micro) {
      const mic = sub.micro.find((m) => m.label === microRegion);
      if (mic) return mic.areas;
    }
    return sub.areas;
  }

  // 大エリア全体
  return subs.flatMap((s) => s.areas);
}

export default function RegionSelector({
  shops, region, subRegion, microRegion,
  setRegion, setSubRegion, setMicroRegion,
}: Props) {
  // エリア別件数
  const areaCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const s of shops) {
      const a = s.area || "北海道";
      counts[a] = (counts[a] || 0) + 1;
    }
    return counts;
  }, [shops]);

  // 大エリア件数
  const regionCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const [rName, subs] of Object.entries(REGION_MAP)) {
      counts[rName] = subs.reduce((sum, sub) =>
        sum + sub.areas.reduce((s2, a) => s2 + (areaCounts[a] || 0), 0), 0);
    }
    counts["すべて"] = shops.length;
    return counts;
  }, [areaCounts, shops.length]);

  // 中エリアのリスト
  const subAreas = region && region !== "すべて" ? REGION_MAP[region] || [] : [];
  const availableSubs = subAreas.filter((s) =>
    s.areas.some((a) => (areaCounts[a] || 0) > 0)
  );

  // 小エリア (micro) のリスト
  const selectedSub = subAreas.find((s) => s.label === subRegion);
  const microAreas = selectedSub?.micro || [];
  const availableMicros = microAreas.filter((m) =>
    m.areas.some((a) => (areaCounts[a] || 0) > 0)
  );

  // 中エリアの件数
  const subCount = (sub: SubArea) =>
    sub.areas.reduce((sum, a) => sum + (areaCounts[a] || 0), 0);

  // 小エリアの件数
  const microCount = (mic: { areas: string[] }) =>
    mic.areas.reduce((sum, a) => sum + (areaCounts[a] || 0), 0);

  return (
    <section className="bg-white border-b border-bokumo-line">
      <div className="max-w-6xl mx-auto px-4 md:px-6 py-3 md:py-5 space-y-2 md:space-y-3">
        {/* 大エリア */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] md:text-xs tracking-widest text-bokumo-sub mr-1 shrink-0 w-8 md:w-10">AREA</span>
          <div className="flex flex-wrap gap-1.5 md:gap-2">
            {REGION_ORDER.map((r) => {
              const active = region === r;
              const count = regionCounts[r] || 0;
              if (r !== "すべて" && count === 0) return null;
              return (
                <button
                  key={r}
                  onClick={() => { setRegion(r); setSubRegion(""); setMicroRegion(""); }}
                  className={`px-2.5 md:px-4 py-1 md:py-2 text-xs md:text-sm rounded-lg border transition ${
                    active
                      ? "bg-bokumo-accent text-white border-bokumo-accent shadow-sm"
                      : "border-bokumo-line text-bokumo-ink hover:border-bokumo-accent hover:text-bokumo-accent"
                  }`}
                >
                  {r}
                  <span className={`ml-1 md:ml-1.5 text-[10px] md:text-[11px] ${active ? "text-white/70" : "text-bokumo-sub"}`}>
                    {count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* 中エリア */}
        {availableSubs.length > 1 && (
          <div className="flex items-center gap-2">
            <span className="w-10 shrink-0" />
            <div className="flex flex-wrap gap-1.5">
              <button
                onClick={() => { setSubRegion(""); setMicroRegion(""); }}
                className={`px-3 py-1 text-xs rounded-full border transition ${
                  subRegion === ""
                    ? "bg-bokumo-accent text-white border-bokumo-accent"
                    : "border-bokumo-line text-bokumo-sub hover:border-bokumo-accent"
                }`}
              >
                {region}すべて
              </button>
              {availableSubs.map((sub) => {
                const active = subRegion === sub.label;
                const count = subCount(sub);
                return (
                  <button
                    key={sub.label}
                    onClick={() => { setSubRegion(sub.label); setMicroRegion(""); }}
                    className={`px-3 py-1 text-xs rounded-full border transition ${
                      active
                        ? "bg-bokumo-accent text-white border-bokumo-accent"
                        : "border-bokumo-line text-bokumo-sub hover:border-bokumo-accent"
                    }`}
                  >
                    {sub.label}
                    <span className={`ml-1 text-[10px] ${active ? "text-white/60" : "text-bokumo-sub/60"}`}>
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* 小エリア (micro) */}
        {availableMicros.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="w-10 shrink-0" />
            <span className="w-6 shrink-0 text-center text-bokumo-line">└</span>
            <div className="flex flex-wrap gap-1.5">
              <button
                onClick={() => setMicroRegion("")}
                className={`px-3 py-1 text-[11px] rounded-full border transition ${
                  microRegion === ""
                    ? "bg-bokumo-sub text-white border-bokumo-sub"
                    : "border-bokumo-line text-bokumo-sub hover:border-bokumo-sub"
                }`}
              >
                {subRegion}すべて
              </button>
              {availableMicros.map((mic) => {
                const active = microRegion === mic.label;
                const count = microCount(mic);
                return (
                  <button
                    key={mic.label}
                    onClick={() => setMicroRegion(mic.label)}
                    className={`px-3 py-1 text-[11px] rounded-full border transition ${
                      active
                        ? "bg-bokumo-sub text-white border-bokumo-sub"
                        : "border-bokumo-line text-bokumo-sub hover:border-bokumo-sub"
                    }`}
                  >
                    {mic.label}
                    <span className={`ml-1 text-[10px] ${active ? "text-white/60" : "text-bokumo-sub/60"}`}>
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
