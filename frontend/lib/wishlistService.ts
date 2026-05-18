"use client";
/**
 * Wishlist Service — Mock + Real API toggle
 * USE_MOCK=true → localStorage'da çalışır (backend hazır olmadan)
 * USE_MOCK=false → watchlistApi (lib/api.ts) ile gerçek backend
 */

import { watchlistApi } from "@/lib/api";

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";
const STORAGE_KEY = "finshop_wishlist";

// ── Tipler ──────────────────────────────────────────────────────────────────

export interface WishlistItem {
  id: string;
  product_name: string;
  current_price: number;
  reference_price: number;
  image_url?: string;
  product_url?: string;
  seller?: string;
  alert_threshold_pct?: number;
  is_active: boolean;
  created_at: string;
}

export interface WishlistNotification {
  id: string;
  type: string;
  title: string;
  message: string;
  metadata?: {
    product_name?: string;
    old_price?: number;
    new_price?: number;
    discount_pct?: number;
  };
  is_read: boolean;
  created_at: string;
}

// ── Mock helpers ─────────────────────────────────────────────────────────────

function getMockItems(): WishlistItem[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

function saveMockItems(items: WishlistItem[]) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(items)); } catch {}
}

// ── Service ──────────────────────────────────────────────────────────────────

export const wishlistService = {
  async getAll(): Promise<WishlistItem[]> {
    if (USE_MOCK) {
      await delay(200);
      return getMockItems();
    }
    const res = await watchlistApi.list();
    return (res as any).watchlist ?? [];
  },

  async add(product: {
    name: string;
    price: number;
    url?: string;
    image_url?: string;
    seller?: string;
  }): Promise<WishlistItem> {
    if (USE_MOCK) {
      const items = getMockItems();
      const newItem: WishlistItem = {
        id: `mock-${Date.now()}`,
        product_name: product.name,
        current_price: product.price,
        reference_price: product.price,
        image_url: product.url,
        product_url: product.url,
        seller: product.seller,
        is_active: true,
        created_at: new Date().toISOString(),
      };
      saveMockItems([...items, newItem]);
      await delay(150);
      return newItem;
    }
    const res = await watchlistApi.add(product);
    return (res as any).watchlist_item ?? res;
  },

  async remove(id: string): Promise<void> {
    if (USE_MOCK) {
      saveMockItems(getMockItems().filter((i) => i.id !== id));
      await delay(100);
      return;
    }
    await watchlistApi.remove(id);
  },

  isStarred(productName: string): boolean {
    const items = getMockItems();
    if (USE_MOCK) {
      return items.some((i) => i.product_name === productName && i.is_active);
    }
    // Real mode: cache gerektirmez, async değil — optimistik UI için mock cache
    return items.some((i) => i.product_name === productName && i.is_active);
  },

  async getNotifications(limit = 20): Promise<{
    notifications: WishlistNotification[];
    unread_count: number;
  }> {
    if (USE_MOCK) {
      await delay(150);
      return { notifications: [], unread_count: 0 };
    }
    const res = await watchlistApi.notifications(limit);
    return {
      notifications: (res as any).notifications ?? [],
      unread_count: (res as any).unread_count ?? 0,
    };
  },

  async markRead(id: string): Promise<void> {
    if (!USE_MOCK) await watchlistApi.markRead(id);
  },

  async markAllRead(): Promise<void> {
    if (!USE_MOCK) await watchlistApi.markAllRead();
  },
};

function delay(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}
