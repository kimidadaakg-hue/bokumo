import type { MetadataRoute } from "next";
import shopsData from "@/data/shops.json";
import postsData from "@/data/blog_posts.json";
import type { Shop } from "@/types/shop";
import type { BlogPost } from "@/types/blog";

export const dynamic = "force-static";

const shops = shopsData as Shop[];
const posts = postsData as BlogPost[];
const SITE = "https://boku-mo.com";

export default function sitemap(): MetadataRoute.Sitemap {
  const today = new Date().toISOString().split("T")[0];

  const staticPages: MetadataRoute.Sitemap = [
    { url: `${SITE}/`, lastModified: today, changeFrequency: "daily", priority: 1.0 },
    { url: `${SITE}/about`, lastModified: today, changeFrequency: "monthly", priority: 0.5 },
    { url: `${SITE}/contact`, lastModified: today, changeFrequency: "monthly", priority: 0.5 },
    { url: `${SITE}/privacy`, lastModified: today, changeFrequency: "yearly", priority: 0.3 },
    { url: `${SITE}/blog`, lastModified: today, changeFrequency: "weekly", priority: 0.9 },
  ];

  const blogPages: MetadataRoute.Sitemap = posts.map((p) => ({
    url: `${SITE}/blog/${p.slug}`,
    lastModified: p.publishedAt,
    changeFrequency: "monthly" as const,
    priority: 0.8,
  }));

  const shopPages: MetadataRoute.Sitemap = shops.map((s) => ({
    url: `${SITE}/shop/${s.id}`,
    lastModified: today,
    changeFrequency: "monthly" as const,
    priority: 0.7,
  }));

  return [...staticPages, ...blogPages, ...shopPages];
}
