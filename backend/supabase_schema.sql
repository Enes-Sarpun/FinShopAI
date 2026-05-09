-- ================================================================
-- FinShop AI - Supabase Database Schema
-- SQL Editor'de sırayla çalıştır
-- ================================================================

-- ----------------------------------------------------------------
-- 1. TABLOLAR
-- ----------------------------------------------------------------

-- Kullanıcı profilleri (auth.users ile bağlantılı)
CREATE TABLE public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    avatar_url TEXT,
    auth_provider VARCHAR(50),
    kvkk_accepted BOOLEAN DEFAULT FALSE,
    kvkk_accepted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Karakter analizi profilleri
CREATE TABLE public.personality_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    spending_type VARCHAR(50),                              -- tutumlu | dengeli | savruk
    risk_score INTEGER CHECK (risk_score BETWEEN 1 AND 10),
    impulsive_score INTEGER CHECK (impulsive_score BETWEEN 1 AND 10),
    saving_score INTEGER CHECK (saving_score BETWEEN 1 AND 10),
    research_score INTEGER CHECK (research_score BETWEEN 1 AND 10),
    raw_answers JSONB,
    llm_analysis TEXT,
    strengths TEXT[],
    weaknesses TEXT[],
    recommendations TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Bütçe takibi
CREATE TABLE public.budgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    monthly_income DECIMAL(10,2),
    monthly_fixed_expenses DECIMAL(10,2),
    savings_goal DECIMAL(10,2),
    available_budget DECIMAL(10,2),
    currency VARCHAR(10) DEFAULT 'TRY',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Harcamalar
CREATE TABLE public.expenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    category VARCHAR(100),
    amount DECIMAL(10,2),
    description TEXT,
    expense_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- AI sohbet geçmişi
CREATE TABLE public.chat_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    role VARCHAR(20),        -- user | assistant
    agent_used VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Ürün önerileri
CREATE TABLE public.product_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    query TEXT,
    product_name VARCHAR(500),
    product_url TEXT,
    price DECIMAL(10,2),
    quality_score INTEGER,
    sentiment_score DECIMAL(3,2),
    recommendation_reason TEXT,
    is_within_budget BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Mock ürün veritabanı (e-ticaret simülasyonu)
CREATE TABLE public.mock_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(500),
    category VARCHAR(100),
    price DECIMAL(10,2),
    description TEXT,
    image_url TEXT,
    rating DECIMAL(3,2),
    review_count INTEGER,
    seller VARCHAR(100),
    tags TEXT[]
);

-- Mock yorumlar
CREATE TABLE public.mock_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES public.mock_products(id) ON DELETE CASCADE,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    sentiment VARCHAR(20),   -- positive | neutral | negative
    created_at TIMESTAMP DEFAULT NOW()
);


-- ----------------------------------------------------------------
-- 2. ROW LEVEL SECURITY (RLS) AKTİF ET
-- ----------------------------------------------------------------

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.personality_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.budgets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.expenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.product_recommendations ENABLE ROW LEVEL SECURITY;
-- mock_products ve mock_reviews herkese açık, RLS gerekmez


-- ----------------------------------------------------------------
-- 3. RLS POLİCY'LERİ
-- ----------------------------------------------------------------

-- profiles
CREATE POLICY "Users can view own profile"
    ON public.profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON public.profiles FOR UPDATE
    USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
    ON public.profiles FOR INSERT
    WITH CHECK (auth.uid() = id);

-- personality_profiles
CREATE POLICY "Users can view own personality"
    ON public.personality_profiles FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own personality"
    ON public.personality_profiles FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- budgets
CREATE POLICY "Users can manage own budget"
    ON public.budgets FOR ALL
    USING (auth.uid() = user_id);

-- expenses
CREATE POLICY "Users can manage own expenses"
    ON public.expenses FOR ALL
    USING (auth.uid() = user_id);

-- chat_history
CREATE POLICY "Users can manage own chat history"
    ON public.chat_history FOR ALL
    USING (auth.uid() = user_id);

-- product_recommendations
CREATE POLICY "Users can manage own recommendations"
    ON public.product_recommendations FOR ALL
    USING (auth.uid() = user_id);


-- ----------------------------------------------------------------
-- 4. PROFILE AUTO-CREATE TRIGGER
-- Yeni kullanıcı kayıt olduğunda profiles tablosuna otomatik ekle
-- ----------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, full_name, avatar_url, auth_provider)
    VALUES (
        NEW.id,
        NEW.email,
        NEW.raw_user_meta_data->>'full_name',
        NEW.raw_user_meta_data->>'avatar_url',
        NEW.raw_app_meta_data->>'provider'
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();


-- ----------------------------------------------------------------
-- 5. updated_at OTO-GÜNCELLEME TRIGGER
-- ----------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER update_budgets_updated_at
    BEFORE UPDATE ON public.budgets
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();
