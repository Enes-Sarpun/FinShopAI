"use client";
import { useEffect, useState } from "react";
import { Star, TrendingDown, ExternalLink, Trash2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { useTranslation } from "react-i18next";
import { wishlistService, type WishlistItem } from "@/lib/wishlistService";
import toast from "react-hot-toast";

function formatTL(n: number) {
  return new Intl.NumberFormat("tr-TR").format(Math.round(n)) + " ₺";
}

function ItemRow({ item, onRemove }: { item: WishlistItem; onRemove: (id: string) => void }) {
  const { t } = useTranslation();
  const discount =
    item.reference_price > 0
      ? Math.round(((item.reference_price - item.current_price) / item.reference_price) * 100)
      : 0;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="flex items-center gap-3 p-2.5 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/60 group transition-colors"
    >
      {/* Görsel */}
      <div className="w-11 h-11 rounded-xl overflow-hidden bg-gray-100 dark:bg-gray-800 flex-shrink-0">
        {item.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={item.image_url} alt={item.product_name} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Star className="w-4 h-4 text-gray-300 dark:text-gray-600" />
          </div>
        )}
      </div>

      {/* Bilgi */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-800 dark:text-gray-100 truncate">{item.product_name}</p>
        <div className="flex items-baseline gap-1.5 mt-0.5">
          <span className="text-sm font-bold text-gray-900 dark:text-gray-100 font-numeric">
            {formatTL(item.current_price)}
          </span>
          {discount > 0 && (
            <>
              <span className="text-xs text-gray-400 line-through font-numeric">{formatTL(item.reference_price)}</span>
              <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">-%{discount}</span>
            </>
          )}
        </div>
      </div>

      {/* Aksiyonlar */}
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
        {item.product_url && (
          <a
            href={item.product_url}
            target="_blank"
            rel="noopener noreferrer"
            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-blue-500 transition-colors"
            title={t("wishlist.goToProduct")}
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        )}
        <button
          onClick={() => onRemove(item.id)}
          className="p-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-500 transition-colors"
          title={t("wishlist.untrack")}
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>
    </motion.div>
  );
}

function SkeletonRow() {
  return (
    <div className="flex items-center gap-3 p-2.5">
      <div className="skeleton w-11 h-11 rounded-xl flex-shrink-0" />
      <div className="flex-1 space-y-1.5">
        <div className="skeleton h-3 w-3/4 rounded" />
        <div className="skeleton h-3 w-1/3 rounded" />
      </div>
    </div>
  );
}

export default function WishlistWidget() {
  const { t } = useTranslation();
  const [items, setItems] = useState<WishlistItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    setLoading(true);
    try {
      const data = await wishlistService.getAll();
      setItems(data.filter((i) => i.is_active));
    } catch {
      // sessiz hata
    } finally {
      setLoading(false);
    }
  }

  async function handleRemove(id: string) {
    try {
      await wishlistService.remove(id);
      setItems((prev) => prev.filter((i) => i.id !== id));
      toast(t("wishlist.removed"), { icon: "☆" });
    } catch {
      toast.error(t("wishlist.error"));
    }
  }

  const onDiscount = items.filter(
    (i) => i.current_price < i.reference_price
  );

  return (
    <div className="card">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-yellow-50 dark:bg-yellow-900/30 flex items-center justify-center flex-shrink-0">
            <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
          </div>
          <h3 className="font-semibold text-gray-900 dark:text-gray-100 text-sm">{t("wishlist.title")}</h3>
        </div>
        {onDiscount.length > 0 && (
          <span className="text-xs bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 px-2.5 py-1 rounded-full font-medium flex items-center gap-1">
            <TrendingDown className="w-3 h-3" />
            {t("wishlist.onSale", { count: onDiscount.length })}
          </span>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div className="space-y-1">
          <SkeletonRow />
          <SkeletonRow />
          <SkeletonRow />
        </div>
      )}

      {/* Boş durum */}
      {!loading && items.length === 0 && (
        <div className="text-center py-6">
          <div className="w-12 h-12 bg-gray-50 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-3">
            <Star className="w-6 h-6 text-gray-300 dark:text-gray-600" />
          </div>
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {t("wishlist.empty")}
          </p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mb-3">
            {t("wishlist.emptyDesc")}
          </p>
          <Link
            href="/chat"
            className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 transition-colors"
          >
            {t("wishlist.startChat")}
          </Link>
        </div>
      )}

      {/* Liste */}
      {!loading && items.length > 0 && (
        <>
          {/* İstatistik özet */}
          <div className="grid grid-cols-2 gap-2.5 mb-3">
            <div className="bg-gray-50 dark:bg-gray-800/60 rounded-xl p-3">
              <p className="text-xl font-bold text-gray-900 dark:text-gray-100">{items.length}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{t("wishlist.tracked")}</p>
            </div>
            <div className="bg-gray-50 dark:bg-gray-800/60 rounded-xl p-3">
              <p className="text-xl font-bold text-emerald-600 dark:text-emerald-400">{onDiscount.length}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{t("wishlist.onSaleShort")}</p>
            </div>
          </div>

          {/* Ürün listesi (max 4) */}
          <div className="space-y-0.5">
            <AnimatePresence mode="popLayout">
              {items.slice(0, 4).map((item) => (
                <ItemRow key={item.id} item={item} onRemove={handleRemove} />
              ))}
            </AnimatePresence>
          </div>

          {items.length > 4 && (
            <p className="text-center text-xs text-gray-400 dark:text-gray-500 mt-2 pt-2 border-t border-gray-100 dark:border-gray-700/50">
              {t("wishlist.moreItems", { count: items.length - 4 })}
            </p>
          )}
        </>
      )}
    </div>
  );
}
