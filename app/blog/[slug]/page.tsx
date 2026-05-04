import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getAllPosts, getPostBySlug, getShopsForPost } from "@/lib/blog";

export function generateStaticParams() {
  return getAllPosts().map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = getPostBySlug(slug);
  if (!post) {
    return { title: "記事が見つかりません | BOKUMO" };
  }
  return {
    title: `${post.title} | BOKUMO`,
    description: post.description,
    alternates: {
      canonical: `https://boku-mo.com/blog/${post.slug}`,
    },
    openGraph: {
      title: post.title,
      description: post.description,
      url: `https://boku-mo.com/blog/${post.slug}`,
      type: "article",
      publishedTime: post.publishedAt,
    },
  };
}

function Stars({ score }: { score: number }) {
  return (
    <span className="text-bokumo-accent tracking-tight" aria-label={`子連れ安心度 ${score}`}>
      {"★".repeat(score)}
      <span className="text-bokumo-line">{"★".repeat(5 - score)}</span>
    </span>
  );
}

export default async function BlogPostPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const post = getPostBySlug(slug);
  if (!post) notFound();

  const shops = getShopsForPost(post.filter);

  return (
    <main className="min-h-screen bg-bokumo-bg">
      <article className="max-w-3xl mx-auto px-6 py-10">
        <Link
          href="/blog"
          className="inline-flex items-center text-sm text-bokumo-sub hover:text-bokumo-accent transition mb-6"
        >
          ← 記事一覧に戻る
        </Link>

        <header className="mb-8">
          <p className="text-xs text-bokumo-sub mb-2">{post.category} · {post.publishedAt}</p>
          <h1
            className="text-2xl md:text-4xl text-bokumo-ink font-bold leading-tight"
            style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}
          >
            {post.title}
          </h1>
        </header>

        <div className="bg-white rounded-2xl shadow-card border border-bokumo-line/50 p-6 md:p-8 mb-8">
          <p className="text-sm md:text-base text-bokumo-ink/80 leading-relaxed">
            {post.intro}
          </p>
        </div>

        {/* お店リスト */}
        <ol className="space-y-6">
          {shops.map((s, i) => (
            <li key={s.id} className="bg-white rounded-2xl shadow-card border border-bokumo-line/50 overflow-hidden">
              <Link href={`/shop/${s.id}`} className="block hover:bg-bokumo-pink-light/20 transition">
                {s.image_url && (
                  <div className="aspect-[16/9] bg-bokumo-pink-light overflow-hidden">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={s.image_url}
                      alt={s.name}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                  </div>
                )}
                <div className="p-5">
                  <div className="flex items-center gap-2 text-xs text-bokumo-sub mb-1">
                    <span className="font-bold text-bokumo-accent">{i + 1}.</span>
                    <span>{s.area} · {s.genre}</span>
                    <Stars score={s.score} />
                  </div>
                  <h2 className="text-lg font-bold text-bokumo-ink mb-2" style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}>
                    {s.name}
                  </h2>
                  {s.address && (
                    <p className="text-xs text-bokumo-ink/60 mb-2">{s.address}</p>
                  )}
                  {s.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-2">
                      {s.tags.map((t) => (
                        <span
                          key={t}
                          className="text-[10px] px-2 py-0.5 rounded-full bg-bokumo-pink-light border border-bokumo-line text-bokumo-ink/70"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                  {s.rating && s.rating_count ? (
                    <p className="text-xs text-bokumo-ink/60">
                      Google評価 ★{s.rating} ({s.rating_count}件)
                    </p>
                  ) : null}
                  <p className="mt-3 text-xs text-bokumo-accent font-bold">
                    詳しくはこちら →
                  </p>
                </div>
              </Link>
            </li>
          ))}
        </ol>

        {shops.length === 0 && (
          <p className="text-center text-bokumo-sub py-10">
            条件に合うお店が現時点でありません。
          </p>
        )}

        <div className="mt-12 text-center">
          <Link
            href="/blog"
            className="inline-block text-sm text-bokumo-sub hover:text-bokumo-accent transition mr-6"
          >
            ← 記事一覧
          </Link>
          <Link
            href="/"
            className="inline-block text-sm text-bokumo-sub hover:text-bokumo-accent transition"
          >
            BOKUMO トップ
          </Link>
        </div>
      </article>
    </main>
  );
}
