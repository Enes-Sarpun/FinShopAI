-- ================================================================
-- FinShop AI — Migration v3
-- Supabase SQL Editor'de çalıştır (tek seferlik)
-- ================================================================
-- İÇERİK:
--   1. profiles tablosuna occupation ve extra_info sütunları
-- ================================================================

ALTER TABLE public.profiles
    ADD COLUMN IF NOT EXISTS occupation  TEXT,
    ADD COLUMN IF NOT EXISTS extra_info  TEXT;
