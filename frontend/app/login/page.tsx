"use client";
import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  ShoppingBag, Mail, Lock, User, ArrowRight, Eye, EyeOff, ArrowLeft,
  Gift, Star, Sparkles, Tag, ShoppingCart, Heart, Zap, Package,
  CreditCard, Percent, Diamond,
} from "lucide-react";
import { authApi } from "@/lib/api";

/* ─────────────────────────────────────────────────────────
   YÜZEN ARKA PLAN İKONLARI
───────────────────────────────────────────────────────── */
const BG_ICONS = [
  // [Icon, x%, y%, boyut, opaklık, süre(s), gecikme(s), döndürme]
  { Icon: ShoppingBag,  x: 8,  y: 12, size: 28, op: 0.18, dur: 7,  del: 0,   rot: -15 },
  { Icon: Gift,         x: 82, y: 8,  size: 32, op: 0.15, dur: 9,  del: 1.2, rot: 12  },
  { Icon: Star,         x: 20, y: 75, size: 22, op: 0.20, dur: 6,  del: 0.5, rot: 20  },
  { Icon: Sparkles,     x: 90, y: 65, size: 26, op: 0.16, dur: 8,  del: 2,   rot: -8  },
  { Icon: Tag,          x: 5,  y: 50, size: 24, op: 0.14, dur: 10, del: 1.8, rot: 25  },
  { Icon: ShoppingCart, x: 75, y: 82, size: 30, op: 0.17, dur: 7.5,del: 0.8, rot: -20 },
  { Icon: Heart,        x: 50, y: 6,  size: 20, op: 0.13, dur: 11, del: 3,   rot: 10  },
  { Icon: Zap,          x: 60, y: 88, size: 22, op: 0.18, dur: 6.5,del: 2.5, rot: -30 },
  { Icon: Package,      x: 35, y: 20, size: 26, op: 0.12, dur: 9,  del: 1,   rot: 15  },
  { Icon: CreditCard,   x: 15, y: 88, size: 28, op: 0.14, dur: 8,  del: 4,   rot: -10 },
  { Icon: Percent,      x: 92, y: 35, size: 24, op: 0.16, dur: 7,  del: 0.3, rot: 18  },
  { Icon: Diamond,      x: 45, y: 92, size: 20, op: 0.13, dur: 10, del: 2.2, rot: -22 },
  { Icon: Gift,         x: 70, y: 18, size: 22, op: 0.15, dur: 8.5,del: 3.5, rot: 8   },
  { Icon: Star,         x: 30, y: 55, size: 18, op: 0.12, dur: 7,  del: 1.5, rot: -5  },
  { Icon: ShoppingBag,  x: 88, y: 50, size: 24, op: 0.14, dur: 9.5,del: 0.7, rot: 22  },
] as const;

function FloatingIcons() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden="true">
      {BG_ICONS.map(({ Icon, x, y, size, op, dur, del, rot }, i) => (
        <motion.div
          key={i}
          className="absolute"
          style={{ left: `${x}%`, top: `${y}%`, opacity: op }}
          animate={{
            y: [0, -18, 6, -12, 0],
            x: [0, 8, -6, 10, 0],
            rotate: [rot, rot + 15, rot - 10, rot + 5, rot],
          }}
          transition={{
            duration: dur,
            delay: del,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        >
          <Icon width={size} height={size} strokeWidth={1.5} className="text-white" />
        </motion.div>
      ))}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────
   STAGGER FADE-IN
───────────────────────────────────────────────────────── */
const field = (i: number) => ({
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { delay: 0.05 + i * 0.08, duration: 0.3, ease: [0.25, 0.1, 0.25, 1] as const },
});

/* ═══════════════════════════════════════
   GİRİŞ FORMU
═══════════════════════════════════════ */
function LoginForm({ onSwitch }: { onSwitch: () => void }) {
  const router = useRouter();
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw]     = useState(false);
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      await authApi.login(email, password);
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Giriş başarısız");
    } finally { setLoading(false); }
  }

  return (
    <div className="flex flex-col justify-center h-full px-10 py-12">
      <motion.div {...field(0)}>
        <h2 className="text-2xl font-bold text-gray-900 mb-1">Hoş Geldin</h2>
        <p className="text-sm text-gray-500 mb-8">Hesabına giriş yap ve alışverişe başla.</p>
      </motion.div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <motion.div {...field(1)}>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">E-posta</label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
            <input type="email" className="input pl-10" placeholder="ornek@email.com"
              value={email} onChange={e => setEmail(e.target.value)} required autoComplete="email" />
          </div>
        </motion.div>

        <motion.div {...field(2)}>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Şifre</label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
            <input type={showPw ? "text" : "password"} className="input pl-10 pr-10" placeholder="••••••••"
              value={password} onChange={e => setPassword(e.target.value)} required autoComplete="current-password" />
            <button type="button" onClick={() => setShowPw(p => !p)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors">
              {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </motion.div>

        {error && (
          <motion.p initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}
            className="text-red-500 text-sm bg-red-50 border border-red-100 rounded-xl px-3 py-2">
            {error}
          </motion.p>
        )}

        <motion.div {...field(3)}>
          <button type="submit" disabled={loading}
            className="btn-primary w-full flex items-center justify-center gap-2">
            {loading
              ? <span className="w-4 h-4 border-2 border-white/50 border-t-white rounded-full animate-spin" />
              : <><span>Giriş Yap</span><ArrowRight className="w-4 h-4" /></>}
          </button>
        </motion.div>
      </form>

      <motion.p {...field(4)} className="text-center text-sm text-gray-500 mt-6">
        Hesabın yok mu?{" "}
        <button onClick={onSwitch} className="text-indigo-600 hover:underline font-semibold">
          Kayıt ol
        </button>
      </motion.p>
    </div>
  );
}

/* ═══════════════════════════════════════
   KAYIT FORMU
═══════════════════════════════════════ */
function RegisterForm({ onSwitch }: { onSwitch: () => void }) {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw]     = useState(false);
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      await authApi.register(email, password, fullName);
      await authApi.login(email, password);
      router.push("/onboarding/personality");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Kayıt başarısız");
    } finally { setLoading(false); }
  }

  return (
    <div className="flex flex-col justify-center h-full px-10 py-12">
      <motion.div {...field(0)}>
        <button onClick={onSwitch}
          className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-700 transition-colors mb-5">
          <ArrowLeft className="w-3.5 h-3.5" /> Giriş sayfasına dön
        </button>
        <h2 className="text-2xl font-bold text-gray-900 mb-1">Hesap Oluştur</h2>
        <p className="text-sm text-gray-500 mb-7">Finansal özgürlüğün başladığı yer.</p>
      </motion.div>

      <form onSubmit={handleSubmit} className="space-y-3.5">
        <motion.div {...field(1)}>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Ad Soyad</label>
          <div className="relative">
            <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
            <input type="text" className="input pl-10" placeholder="Adınız Soyadınız"
              value={fullName} onChange={e => setFullName(e.target.value)} required autoComplete="name" />
          </div>
        </motion.div>

        <motion.div {...field(2)}>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">E-posta</label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
            <input type="email" className="input pl-10" placeholder="ornek@email.com"
              value={email} onChange={e => setEmail(e.target.value)} required autoComplete="email" />
          </div>
        </motion.div>

        <motion.div {...field(3)}>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Şifre</label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
            <input type={showPw ? "text" : "password"} className="input pl-10 pr-10" placeholder="En az 6 karakter"
              value={password} onChange={e => setPassword(e.target.value)} minLength={6} required autoComplete="new-password" />
            <button type="button" onClick={() => setShowPw(p => !p)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors">
              {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </motion.div>

        {error && (
          <motion.p initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}
            className="text-red-500 text-sm bg-red-50 border border-red-100 rounded-xl px-3 py-2">
            {error}
          </motion.p>
        )}

        <motion.div {...field(4)}>
          <button type="submit" disabled={loading}
            className="btn-primary w-full flex items-center justify-center gap-2">
            {loading
              ? <span className="w-4 h-4 border-2 border-white/50 border-t-white rounded-full animate-spin" />
              : <><span>Kayıt Ol</span><ArrowRight className="w-4 h-4" /></>}
          </button>
        </motion.div>
      </form>
    </div>
  );
}

/* ═══════════════════════════════════════
   POLİS ŞERİDİ KATMANI
═══════════════════════════════════════ */
const STRIPE_TEXT = "FinShop AI";
const STRIPE_REPEAT = 14; // her satırda kaç tekrar
const STRIPE_ROWS   = 18; // kaç satır

function StripeBg() {
  return (
    <div className="auth-stripe-bg" aria-hidden="true">
      {Array.from({ length: STRIPE_ROWS }).map((_, r) => (
        <div key={r} className="auth-stripe-row">
          {Array.from({ length: STRIPE_REPEAT }).map((_, c) => (
            <span key={c}>{STRIPE_TEXT}</span>
          ))}
        </div>
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════
   BRAND PANEL (sol ön + sağ register modu)
═══════════════════════════════════════ */
function BrandPanel({ onSwitch, label, btnText, isRight = false }:
  { onSwitch: () => void; label: string; btnText: string; isRight?: boolean }) {
  return (
    <div className="relative flex flex-col items-center justify-center h-full px-10 text-white overflow-hidden"
      style={{ background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)" }}>

      {/* Polis şeridi arka plan */}
      <StripeBg />

      {/* Yüzen ikonlar */}
      <FloatingIcons />

      {/* Dekoratif daireler */}
      <div className={`absolute ${isRight ? "top-6 left-6" : "top-8 right-8"} w-24 h-24 bg-white/10 rounded-full pointer-events-none`} />
      <div className={`absolute ${isRight ? "bottom-8 right-8" : "bottom-12 left-6"} w-20 h-20 bg-white/10 rounded-full pointer-events-none`} />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-white/5 rounded-full pointer-events-none" />

      {/* İçerik */}
      <div className="relative z-10 flex flex-col items-center text-center">
        <div className="logo-float mb-6">
          <div className="w-20 h-20 bg-white/20 backdrop-blur-sm rounded-3xl flex items-center justify-center border border-white/30 shadow-lg">
            <ShoppingBag className="w-10 h-10 text-white" />
          </div>
        </div>
        <h1 className="text-3xl font-bold mb-2">FinShop AI</h1>
        <p className="text-white/80 text-sm leading-relaxed mb-10 max-w-[200px]">{label}</p>
        <button onClick={onSwitch}
          className="flex items-center gap-2 px-5 py-2.5 bg-white/20 hover:bg-white/30 border border-white/40 rounded-xl text-sm font-medium transition-all duration-200 hover:scale-105">
          {isRight && <ArrowLeft className="w-4 h-4" />}
          {btnText}
          {!isRight && <ArrowRight className="w-4 h-4" />}
        </button>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════
   ANA SAYFA
═══════════════════════════════════════ */
function LoginPageInner() {
  const searchParams = useSearchParams();
  const [mode, setMode] = useState<"login" | "register">(
    searchParams.get("mode") === "register" ? "register" : "login"
  );
  const isRegister = mode === "register";

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-8">
      <motion.div
        className="w-full max-w-[860px] h-[580px]"
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
        style={{ perspective: 2000 }}
      >
        <div className="flex h-full rounded-[20px] overflow-hidden"
          style={{ boxShadow: "0 32px 80px rgba(99,102,241,0.25), 0 8px 32px rgba(0,0,0,0.12)" }}>

          {/* ── SOL PANEL (döner) ── */}
          <div className="relative w-1/2 h-full" style={{ perspective: 2000 }}>
            {/* Ön yüz — brand */}
            <motion.div
              className="absolute inset-0"
              style={{
                borderRadius: "20px 0 0 20px",
                backfaceVisibility: "hidden",
                WebkitBackfaceVisibility: "hidden",
                transformStyle: "preserve-3d",
              }}
              animate={{ rotateY: isRegister ? -180 : 0 }}
              transition={{ duration: 1.1, ease: [0.645, 0.045, 0.355, 1] }}
            >
              <BrandPanel
                onSwitch={() => setMode("register")}
                label="Cüzdanını bilen alışveriş asistanınla tanış."
                btnText="Hesabın yok mu? Kayıt ol"
              />
            </motion.div>

            {/* Arka yüz — register formu */}
            <motion.div
              className="absolute inset-0 overflow-hidden"
              style={{
                background: "rgba(255,255,255,0.97)",
                borderRadius: "20px 0 0 20px",
                backfaceVisibility: "hidden",
                WebkitBackfaceVisibility: "hidden",
                transformStyle: "preserve-3d",
                rotateY: 180,
              }}
              animate={{ rotateY: isRegister ? 0 : 180 }}
              transition={{ duration: 1.1, ease: [0.645, 0.045, 0.355, 1] }}
            >
              <AnimatePresence mode="wait">
                {isRegister && (
                  <motion.div key="reg-form" className="h-full"
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                    transition={{ delay: 0.65, duration: 0.25 }}>
                    <RegisterForm onSwitch={() => setMode("login")} />
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          </div>

          {/* ── SAĞ PANEL (sabit) ── */}
          <div className="relative w-1/2 h-full overflow-hidden"
            style={{ borderRadius: "0 20px 20px 0" }}>
            <AnimatePresence mode="wait">
              {!isRegister ? (
                <motion.div key="login-panel" className="absolute inset-0"
                  style={{ background: "rgba(255,255,255,0.95)", backdropFilter: "blur(24px)", WebkitBackdropFilter: "blur(24px)" }}
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                  transition={{ duration: 0.3 }}>
                  <LoginForm onSwitch={() => setMode("register")} />
                </motion.div>
              ) : (
                <motion.div key="back-panel" className="absolute inset-0"
                  style={{ borderRadius: "0 20px 20px 0" }}
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                  transition={{ duration: 0.4, delay: 0.5 }}>
                  <BrandPanel
                    onSwitch={() => setMode("login")}
                    label="Hesabın varsa giriş yaparak devam et."
                    btnText="Giriş Yap"
                    isRight
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </div>

        </div>
      </motion.div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginPageInner />
    </Suspense>
  );
}
