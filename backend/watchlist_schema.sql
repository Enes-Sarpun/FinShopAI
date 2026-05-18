-- ================================================================
-- FinShop AI — Watchlist & Notifications Schema  (v2)
-- Supabase SQL Editor'de mevcut şemanın üstüne çalıştır
-- ================================================================

-- ----------------------------------------------------------------
-- 1. TABLOLAR
-- ----------------------------------------------------------------

-- Takip listesi (yıldızlı ürünler)
CREATE TABLE IF NOT EXISTS public.watchlist (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    product_name        VARCHAR(500) NOT NULL,
    product_url         TEXT,
    image_url           TEXT,
    seller              VARCHAR(100),
    search_query        VARCHAR(500),            -- SerpAPI'de kullanılacak arama terimi

    reference_price     DECIMAL(10,2) NOT NULL,  -- Ekleme / son alarm anındaki fiyat
    current_price       DECIMAL(10,2),           -- Son kontrol edilen fiyat

    -- [v2] Per-ürün alarm eşiği (varsayılan: %3)
    alert_threshold_pct DECIMAL(5,2) DEFAULT 3.0 CHECK (alert_threshold_pct > 0),

    is_active           BOOLEAN DEFAULT TRUE,    -- FALSE = soft delete
    last_checked_at     TIMESTAMP WITH TIME ZONE,

    -- [v2] Spam koruması için son bildirim zamanı
    last_notified_at    TIMESTAMP WITH TIME ZONE,

    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- [v2] Fiyat geçmişi — her kontrol sonucu bir satır
CREATE TABLE IF NOT EXISTS public.price_history (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    watchlist_id UUID REFERENCES public.watchlist(id) ON DELETE CASCADE,
    price        DECIMAL(10,2) NOT NULL,
    checked_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Bildirimler (fiyat alarmları + gelecekte başka türler)
CREATE TABLE IF NOT EXISTS public.notifications (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    type        VARCHAR(50) DEFAULT 'price_drop',  -- price_drop | system | promo
    title       VARCHAR(255) NOT NULL,
    message     TEXT NOT NULL,
    metadata    JSONB,                             -- watchlist_id, eski/yeni fiyat vb.
    is_read     BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);


-- ----------------------------------------------------------------
-- 2. ROW LEVEL SECURITY
-- ----------------------------------------------------------------

ALTER TABLE public.watchlist      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.price_history  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications  ENABLE ROW LEVEL SECURITY;


-- ----------------------------------------------------------------
-- 3. RLS POLİCY'LERİ
-- ----------------------------------------------------------------

CREATE POLICY "Users can manage own watchlist"
    ON public.watchlist FOR ALL
    USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own price history"
    ON public.price_history FOR ALL
    USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own notifications"
    ON public.notifications FOR ALL
    USING (auth.uid() = user_id);


-- ----------------------------------------------------------------
-- 4. updated_at OTO-GÜNCELLEME TRIGGER (watchlist)
-- ----------------------------------------------------------------

CREATE TRIGGER update_watchlist_updated_at
    BEFORE UPDATE ON public.watchlist
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();


-- ----------------------------------------------------------------
-- 5. İNDEKSLER (performans)
-- ----------------------------------------------------------------

-- Kullanıcının aktif takip listesini hızlı getir
CREATE INDEX IF NOT EXISTS idx_watchlist_user_active
    ON public.watchlist (user_id, is_active);

-- Okunmamış bildirimleri hızlı say
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread
    ON public.notifications (user_id, is_read);

-- Fiyat geçmişini watchlist_id + tarih bazlı sorgula
CREATE INDEX IF NOT EXISTS idx_price_history_watchlist_time
    ON public.price_history (watchlist_id, checked_at DESC);

-- Scheduler için: son kontrol zamanına göre sıralama
CREATE INDEX IF NOT EXISTS idx_watchlist_last_checked
    ON public.watchlist (last_checked_at);


-- ----------------------------------------------------------------
-- 6. YARDIMCI VIEW: Aktif Watchlist + Son Fiyat
-- ----------------------------------------------------------------

CREATE OR REPLACE VIEW public.watchlist_with_trend AS
SELECT
    w.*,
    -- Son 7 günlük kayıt sayısı (trend için yeterli veri var mı?)
    COUNT(ph.id) FILTER (
        WHERE ph.checked_at >= NOW() - INTERVAL '7 days'
    ) AS history_count_7d,
    -- Son 7 günlük minimum fiyat
    MIN(ph.price) FILTER (
        WHERE ph.checked_at >= NOW() - INTERVAL '7 days'
    ) AS min_price_7d,
    -- Son 7 günlük maksimum fiyat
    MAX(ph.price) FILTER (
        WHERE ph.checked_at >= NOW() - INTERVAL '7 days'
    ) AS max_price_7d
FROM public.watchlist w
LEFT JOIN public.price_history ph ON ph.watchlist_id = w.id
WHERE w.is_active = TRUE
GROUP BY w.id;
