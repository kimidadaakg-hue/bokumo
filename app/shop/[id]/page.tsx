import type { Metadata } from "next";
import Link from "next/link";
import shopsData from "@/data/shops.json";
import type { Shop } from "@/types/shop";

const shops = shopsData as Shop[];

const NEGATIVE_WORDS = [
  "不向き", "遠慮", "お断り", "難しそう",
  "狭い", "激狭", "窮屈", "汚い", "汚れ", "不衛生", "臭い", "暑い", "寒い",
  "うるさい", "騒がしい", "怖い",
  "気分が悪", "ひどく", "ひどい", "ぶっきらぼう", "無愛想", "態度が悪",
  "対応が悪", "接客が悪", "感じが悪", "不親切", "失礼",
  "まずい", "不味い", "しょっぱ", "しつこい", "冷たい", "ぬるい",
  "残念", "ガッカリ", "がっかり", "期待はずれ", "期待外れ",
  "おすすめできません", "オススメできません", "おすすめしない",
  "回転が悪", "待たされ", "遅い", "遅すぎ",
  "不十分", "不満", "最悪", "二度と", "行かない",
  "高い", "高すぎ", "コスパが悪", "割高", "ぼったくり",
];

function filterPositive(evs: string[]): string[] {
  return evs.filter((ev) => !NEGATIVE_WORDS.some((ng) => ev.includes(ng)));
}

export function generateStaticParams() {
  return shops.map((shop) => ({ id: String(shop.id) }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const shop = shops.find((s) => String(s.id) === id);
  if (!shop) {
    return { title: "お店が見つかりません | BOKUMO" };
  }
  const tagText = shop.tags.length > 0 ? shop.tags.join("・") + "。" : "";
  return {
    title: `${shop.name}（${shop.area}）| BOKUMO`,
    description: `${shop.name}は${shop.area}の${shop.genre}。${tagText}子連れで行ける北海道の飲食店ガイド BOKUMO（ボクモ）。`,
    openGraph: {
      title: `${shop.name} | BOKUMO`,
      description: `${shop.area}の${shop.genre}。${tagText}`,
      images: shop.image_url ? [{ url: shop.image_url }] : undefined,
    },
  };
}

function Stars({ score }: { score: number }) {
  return (
    <span
      className="text-bokumo-accent tracking-tight text-lg"
      aria-label={`子連れ安心度 ${score}`}
    >
      {"★".repeat(score)}
      <span className="text-bokumo-line">{"★".repeat(5 - score)}</span>
    </span>
  );
}

export default async function ShopDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const shop = shops.find((s) => String(s.id) === id);

  if (!shop) {
    return (
      <main className="min-h-screen bg-bokumo-bg flex items-center justify-center">
        <div className="text-center">
          <p className="text-bokumo-sub text-lg mb-4">
            お店が見つかりませんでした
          </p>
          <Link
            href="/"
            className="text-bokumo-accent hover:underline text-sm"
          >
            ← 一覧に戻る
          </Link>
        </div>
      </main>
    );
  }

  const evidence = filterPositive(shop.evidence || []);

  // 同じエリア / 同じジャンル の関連店舗 (自分以外、最大6件ずつ)
  const sameArea = shops
    .filter((s) => s.id !== shop.id && s.area === shop.area)
    .slice(0, 6);
  const sameGenre = shops
    .filter((s) => s.id !== shop.id && s.genre === shop.genre && s.area !== shop.area)
    .slice(0, 6);

  // 詳細紹介文を組み立て (SEO用にユニーク性を出す)
  const introParts: string[] = [];
  introParts.push(`${shop.name}は、北海道${shop.area}にある${shop.genre}のお店です。`);
  if (shop.address) introParts.push(`所在地は${shop.address}。`);
  if (shop.rating && shop.rating_count) {
    introParts.push(`Googleでの評価は★${shop.rating}（${shop.rating_count}件のレビュー）。`);
  }
  if (shop.tags.length > 0) {
    introParts.push(`${shop.tags.join("・")}を備え、小さなお子様連れのご家族にもおすすめできます。`);
  }
  const introText = introParts.join("");

  return (
    <main className="min-h-screen bg-bokumo-bg">
      {/* 戻るリンク */}
      <div className="max-w-3xl mx-auto px-6 pt-6">
        <Link
          href="/"
          className="inline-flex items-center text-sm text-bokumo-sub hover:text-bokumo-accent transition"
        >
          ← 一覧に戻る
        </Link>
      </div>

      {/* メインコンテンツ */}
      <article className="max-w-3xl mx-auto px-6 py-6">
        {/* 写真 */}
        {shop.image_url && (
          <div className="aspect-[16/9] bg-bokumo-pink-light rounded-2xl overflow-hidden shadow-card mb-6">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={shop.image_url}
              alt={shop.name}
              className="w-full h-full object-cover"
            />
          </div>
        )}

        {/* 店舗情報 */}
        <div className="bg-white rounded-2xl shadow-card border border-bokumo-line/50 p-6 md:p-8">
          {/* エリア・ジャンル・スコア */}
          <div className="flex items-center justify-between gap-2 mb-2">
            <span className="text-xs text-bokumo-sub tracking-widest">
              {shop.area} ・ {shop.genre}
            </span>
            <Stars score={shop.score} />
          </div>

          {/* 店名 */}
          <h1
            className="text-2xl md:text-3xl text-bokumo-ink font-bold leading-tight"
            style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}
          >
            {shop.name}
          </h1>

          {/* タグ */}
          <div className="mt-4 flex flex-wrap gap-2">
            {shop.tags.map((t) => (
              <span
                key={t}
                className="text-xs px-3 py-1 rounded-full bg-bokumo-pink-light border border-bokumo-line text-bokumo-ink/70"
              >
                {t}
              </span>
            ))}
          </div>

          {/* 紹介文 */}
          <div className="mt-6">
            <h2
              className="text-sm font-bold text-bokumo-ink mb-2"
              style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}
            >
              お店について
            </h2>
            <p className="text-sm text-bokumo-ink/70 leading-relaxed">
              {introText}
            </p>
            {shop.description && (
              <p className="mt-3 text-sm text-bokumo-ink/70 leading-relaxed">
                {shop.description}
              </p>
            )}
          </div>

          {/* 店舗情報 */}
          <div className="mt-6">
            <h2
              className="text-sm font-bold text-bokumo-ink mb-3"
              style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}
            >
              店舗情報
            </h2>
            <dl className="text-sm text-bokumo-ink/80 space-y-2">
              {shop.address && (
                <div className="flex gap-3">
                  <dt className="text-bokumo-sub w-20 shrink-0">住所</dt>
                  <dd>{shop.address}</dd>
                </div>
              )}
              {shop.phone && (
                <div className="flex gap-3">
                  <dt className="text-bokumo-sub w-20 shrink-0">電話</dt>
                  <dd>
                    <a href={`tel:${shop.phone}`} className="text-bokumo-accent hover:underline">
                      {shop.phone}
                    </a>
                  </dd>
                </div>
              )}
              {shop.rating !== undefined && shop.rating > 0 && (
                <div className="flex gap-3">
                  <dt className="text-bokumo-sub w-20 shrink-0">評価</dt>
                  <dd>
                    ★ {shop.rating}
                    {shop.rating_count ? ` (${shop.rating_count}件)` : ""}
                  </dd>
                </div>
              )}
              {shop.hours && shop.hours.length > 0 && (
                <div className="flex gap-3">
                  <dt className="text-bokumo-sub w-20 shrink-0">営業時間</dt>
                  <dd>
                    <ul className="space-y-0.5">
                      {shop.hours.map((h, i) => (
                        <li key={i}>{h}</li>
                      ))}
                    </ul>
                  </dd>
                </div>
              )}
              {shop.website && (
                <div className="flex gap-3">
                  <dt className="text-bokumo-sub w-20 shrink-0">公式サイト</dt>
                  <dd>
                    <a
                      href={shop.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-bokumo-accent hover:underline break-all"
                    >
                      {shop.website}
                    </a>
                  </dd>
                </div>
              )}
            </dl>
          </div>

          {/* 口コミ */}
          {evidence.length > 0 && (
            <div className="mt-6">
              <h2
                className="text-sm font-bold text-bokumo-accent mb-3"
                style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}
              >
                口コミ
              </h2>
              <div className="space-y-2">
                {evidence.map((ev, i) => (
                  <div
                    key={i}
                    className="bg-bokumo-pink-light/50 rounded-lg px-4 py-3"
                  >
                    <p className="text-sm text-bokumo-ink/70 leading-relaxed">
                      「{ev}」
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* アクションボタン */}
          <div className="mt-8 space-y-3">
            {shop.hotpepper_url && (
              <a
                href={shop.hotpepper_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center w-full py-3 text-sm rounded-full bg-[#e60012] text-white hover:opacity-90 transition font-bold"
              >
                ホットペッパーで予約する →
              </a>
            )}
            {/* 食べログ検索リンク - LinkSwitchが自動でアフィリエイトリンクに変換する */}
            <a
              href={`https://tabelog.com/rstLst/?sk=${encodeURIComponent(`${shop.name} ${shop.area}`)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center w-full py-3 text-sm rounded-full bg-[#fbb03b] text-white hover:opacity-90 transition font-bold"
            >
              食べログで詳細・口コミを見る →
            </a>
            <a
              href={shop.tabelog_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center w-full py-3 text-sm rounded-full bg-bokumo-accent text-white hover:opacity-90 transition font-bold"
            >
              Googleマップで見る →
            </a>
            <div className="flex gap-3">
              <a
                href="https://docs.google.com/forms/d/e/1FAIpQLSdG-VGN1WEj53rtg9OkX0ehH88nGK3ZKJPkOnfq174kyeUQOA/viewform"
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 flex items-center justify-center py-2.5 text-xs rounded-full bg-white border border-bokumo-line text-bokumo-ink hover:border-bokumo-accent hover:text-bokumo-accent transition"
              >
                お店を提案する
              </a>
              <a
                href="https://docs.google.com/forms/d/e/1FAIpQLSfhF2zUpZVfjcUQu-NQaFqraAi7UwNQ8CMc_U8rD-CnDFVPnA/viewform"
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 flex items-center justify-center py-2.5 text-xs rounded-full bg-white border border-bokumo-line text-bokumo-ink hover:border-bokumo-accent hover:text-bokumo-accent transition"
              >
                口コミを送る
              </a>
            </div>
          </div>
        </div>

        {/* 同じエリアの他のお店 */}
        {sameArea.length > 0 && (
          <section className="mt-10">
            <h2
              className="text-base font-bold text-bokumo-ink mb-4"
              style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}
            >
              {shop.area}の他の子連れOKなお店
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {sameArea.map((s) => (
                <Link
                  key={s.id}
                  href={`/shop/${s.id}`}
                  className="bg-white rounded-xl border border-bokumo-line/50 p-3 hover:border-bokumo-accent transition"
                >
                  <p className="text-sm font-bold text-bokumo-ink line-clamp-2">
                    {s.name}
                  </p>
                  <p className="text-xs text-bokumo-sub mt-1">{s.genre}</p>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* 同じジャンルの他のお店 */}
        {sameGenre.length > 0 && (
          <section className="mt-10">
            <h2
              className="text-base font-bold text-bokumo-ink mb-4"
              style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}
            >
              北海道の子連れOKな{shop.genre}
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {sameGenre.map((s) => (
                <Link
                  key={s.id}
                  href={`/shop/${s.id}`}
                  className="bg-white rounded-xl border border-bokumo-line/50 p-3 hover:border-bokumo-accent transition"
                >
                  <p className="text-sm font-bold text-bokumo-ink line-clamp-2">
                    {s.name}
                  </p>
                  <p className="text-xs text-bokumo-sub mt-1">{s.area}</p>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* フッターリンク */}
        <div className="mt-10 text-center">
          <Link
            href="/"
            className="text-sm text-bokumo-sub hover:text-bokumo-accent transition"
          >
            ← BOKUMO トップに戻る
          </Link>
        </div>
      </article>
    </main>
  );
}
