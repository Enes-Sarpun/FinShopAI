-- ═══════════════════════════════════════════════════════════════════
-- security_logs tablosu — SecurityAgent violation log'ları için
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS security_logs (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id     UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    content     TEXT,
    risk_level  TEXT DEFAULT 'low',
    action      TEXT DEFAULT 'allow',
    violations  TEXT,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- RLS
ALTER TABLE security_logs ENABLE ROW LEVEL SECURITY;

-- Sadece servis key ile yazılabilir (kullanıcı okuyamaz)
CREATE POLICY "Service can insert security_logs"
    ON security_logs FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Service can read security_logs"
    ON security_logs FOR SELECT
    USING (true);

-- İndeks: kullanıcıya göre hızlı sorgulama
CREATE INDEX IF NOT EXISTS idx_security_logs_user
    ON security_logs(user_id, created_at DESC);
