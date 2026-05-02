import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "プライバシーポリシー | BOKUMO",
  description: "BOKUMO（ボクモ）のプライバシーポリシー。個人情報の取り扱いについて。",
};

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-bokumo-bg">
      <div className="max-w-3xl mx-auto px-6 py-12">
        <Link
          href="/"
          className="inline-flex items-center text-sm text-bokumo-sub hover:text-bokumo-accent transition mb-8"
        >
          ← トップに戻る
        </Link>

        <div className="bg-white rounded-2xl shadow-card border border-bokumo-line/50 p-6 md:p-10">
          <h1
            className="text-2xl md:text-3xl text-bokumo-ink font-bold mb-8"
            style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}
          >
            プライバシーポリシー
          </h1>

          <div className="space-y-6 text-sm text-bokumo-ink/80 leading-relaxed">
            <section>
              <h2 className="text-base font-bold text-bokumo-ink mb-2">1. 個人情報の取得について</h2>
              <p>
                BOKUMO（以下「当サイト」）では、お問い合わせやお店の提案・口コミ投稿の際に、お名前やメールアドレスなどの個人情報をご提供いただく場合があります。これらの情報は、ご連絡への対応およびサービス改善の目的にのみ使用いたします。
              </p>
            </section>

            <section>
              <h2 className="text-base font-bold text-bokumo-ink mb-2">2. 個人情報の第三者提供について</h2>
              <p>
                当サイトでは、法令に基づく場合を除き、お預かりした個人情報を第三者に提供することはありません。
              </p>
            </section>

            <section>
              <h2 className="text-base font-bold text-bokumo-ink mb-2">3. 広告について</h2>
              <p>
                当サイトでは、第三者配信の広告サービス（Google AdSense）を利用する場合があります。広告配信事業者は、ユーザーの興味に応じた広告を表示するために Cookie を使用することがあります。Cookie の使用を望まない場合は、ブラウザの設定で無効にすることができます。
              </p>
              <p className="mt-2">
                Google AdSense に関する詳細は、
                <a
                  href="https://policies.google.com/technologies/ads?hl=ja"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-bokumo-accent hover:underline"
                >
                  Google の広告に関するポリシー
                </a>
                をご覧ください。
              </p>
            </section>

            <section>
              <h2 className="text-base font-bold text-bokumo-ink mb-2">4. アフィリエイトプログラムについて</h2>
              <p>
                当サイトは、株式会社バリューコマースが運営する「バリューコマース アフィリエイト」を含む、各種アフィリエイトプログラムに参加しています。当サイト内に掲載している食べログ・ホットペッパーグルメ等の外部サービスへのリンクから、ユーザーが商品購入や予約等の成果に至った場合、当サイトに紹介料が支払われることがあります。掲載している店舗情報は当サイト独自の編集方針で選定したものであり、報酬の有無によって順位や評価を変更することはありません。
              </p>
            </section>

            <section>
              <h2 className="text-base font-bold text-bokumo-ink mb-2">5. アクセス解析ツールについて</h2>
              <p>
                当サイトでは、Google アナリティクスなどのアクセス解析ツールを使用する場合があります。これらのツールは、トラフィックデータの収集のために Cookie を使用しています。このデータは匿名で収集されており、個人を特定するものではありません。
              </p>
            </section>

            <section>
              <h2 className="text-base font-bold text-bokumo-ink mb-2">6. 掲載情報について</h2>
              <p>
                当サイトに掲載されている店舗情報・口コミは、公開されている情報をもとに編集したものです。情報の正確性には十分注意しておりますが、最新の状況と異なる場合があります。お出かけの際は、各店舗に直接ご確認ください。
              </p>
            </section>

            <section>
              <h2 className="text-base font-bold text-bokumo-ink mb-2">7. 免責事項</h2>
              <p>
                当サイトの情報を利用したことによるいかなる損害についても、当サイトは責任を負いかねます。ご利用は自己責任でお願いいたします。
              </p>
            </section>

            <section>
              <h2 className="text-base font-bold text-bokumo-ink mb-2">8. プライバシーポリシーの変更</h2>
              <p>
                当サイトは、必要に応じて本ポリシーを変更することがあります。変更後のポリシーは、当ページに掲載された時点から効力を持つものとします。
              </p>
            </section>

            <p className="text-xs text-bokumo-sub pt-4 border-t border-bokumo-line">
              制定日: 2026年4月16日
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
