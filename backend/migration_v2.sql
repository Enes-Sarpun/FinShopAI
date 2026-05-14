-- ================================================================
-- FinShop AI — Migration v2
-- Supabase SQL Editor'de çalıştır (tek seferlik)
-- ================================================================
-- İÇERİK:
--   1. profiles tablosuna ban/warning sütunları
--   2. security_logs tablosu + RLS
--   3. watchlist tablosu + RLS + indeksler + view
--   4. price_history tablosu + RLS
--   5. notifications tablosu + RLS
-- ================================================================


-- ----------------------------------------------------------------
-- 1. profiles — ban ve uyarı sütunları (SecurityAgent için)
-- ----------------------------------------------------------------

ALTER TABLE public.profiles
    ADD COLUMN IF NOT EXISTS is_banned     BOOLEAN   DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS ban_reason    TEXT,
    ADD COLUMN IF NOT EXISTS banned_at     TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS warning_count INTEGER   DEFAULT 0;


-- ----------------------------------------------------------------
-- 2. security_logs — ihlal kayıtları (SecurityAgent._log_violation)
-- ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.security_logs (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        REFERENCES auth.users(id) ON DELETE SET NULL,
    content     TEXT,
    risk_level  TEXT        DEFAULT 'low',
    action      TEXT        DEFAULT 'allow',
    violations  TEXT,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT now()
);

ALTER TABLE public.security_logs ENABLE ROW LEVEL SECURITY;

-- Servis key ile yazılabilir, kullanıcı kendi log'larını okuyamaz
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'security_logs' AND policyname = 'Service can insert security_logs'
    ) THEN
        CREATE POLICY "Service can insert security_logs"
            ON public.security_logs FOR INSERT WITH CHECK (true);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'security_logs' AND policyname = 'Service can read security_logs'
    ) THEN
        CREATE POLICY "Service can read security_logs"
            ON public.security_logs FOR SELECT USING (true);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_security_logs_user
    ON public.security_logs (user_id, created_at DESC);


-- ----------------------------------------------------------------
-- 3. watchlist — takip listesi (WatchlistAgent)
-- ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.watchlist (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    product_name        VARCHAR(500) NOT NULL,
    product_url         TEXT,
    image_url           TEXT,
    seller              VARCHAR(100),
    search_query        VARCHAR(500),
    reference_price     DECIMAL(10,2) NOT NULL,
    current_price       DECIMAL(10,2),
    alert_threshold_pct DECIMAL(5,2) DEFAULT 3.0 CHECK (alert_threshold_pct > 0),
    is_active           BOOLEAN DEFAULT TRUE,
    last_checked_at     TIMESTAMP WITH TIME ZONE,
    last_notified_at    TIMESTAMP WITH TIME ZONE,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE public.watchlist ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'watchlist' AND policyname = 'Users can manage own watchlist'
    ) THEN
        CREATE POLICY "Users can manage own watchlist"
            ON public.watchlist FOR ALL USING (auth.uid() = user_id);
    END IF;
END $$;

-- updated_at trigger (update_updated_at fonksiyonu supabase_schema.sql'de tanımlı)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'update_watchlist_updated_at'
    ) THEN
        CREATE TRIGGER update_watchlist_updated_at
            BEFORE UPDATE ON public.watchlist
            FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_watchlist_user_active
    ON public.watchlist (user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_watchlist_last_checked
    ON public.watchlist (last_checked_at);


-- ----------------------------------------------------------------
-- 4. price_history — fiyat geçmişi (WatchlistAgent._save_price_history)
-- ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.price_history (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    watchlist_id UUID REFERENCES public.watchlist(id) ON DELETE CASCADE,
    price        DECIMAL(10,2) NOT NULL,
    checked_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE public.price_history ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'price_history' AND policyname = 'Users can manage own price history'
    ) THEN
        CREATE POLICY "Users can manage own price history"
            ON public.price_history FOR ALL USING (auth.uid() = user_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_price_history_watchlist_time
    ON public.price_history (watchlist_id, checked_at DESC);


-- ----------------------------------------------------------------
-- 5. notifications — bildirimler (WatchlistAgent._create_notification)
-- ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.notifications (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    type        VARCHAR(50) DEFAULT 'price_drop',
    title       VARCHAR(255) NOT NULL,
    message     TEXT NOT NULL,
    metadata    JSONB,
    is_read     BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'notifications' AND policyname = 'Users can manage own notifications'
    ) THEN
        CREATE POLICY "Users can manage own notifications"
            ON public.notifications FOR ALL USING (auth.uid() = user_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_notifications_user_unread
    ON public.notifications (user_id, is_read);


-- ----------------------------------------------------------------
-- 6. watchlist_with_trend VIEW
-- ----------------------------------------------------------------

CREATE OR REPLACE VIEW public.watchlist_with_trend AS
SELECT
    w.*,
    COUNT(ph.id) FILTER (
        WHERE ph.checked_at >= NOW() - INTERVAL '7 days'
    ) AS history_count_7d,
    MIN(ph.price) FILTER (
        WHERE ph.checked_at >= NOW() - INTERVAL '7 days'
    ) AS min_price_7d,
    MAX(ph.price) FILTER (
        WHERE ph.checked_at >= NOW() - INTERVAL '7 days'
    ) AS max_price_7d
FROM public.watchlist w
LEFT JOIN public.price_history ph ON ph.watchlist_id = w.id
WHERE w.is_active = TRUE
GROUP BY w.id;
