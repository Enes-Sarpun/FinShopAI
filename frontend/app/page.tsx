"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion, useInView, AnimatePresence } from "framer-motion";
import {
  ShoppingBag,
  Brain,
  TrendingUp,
  Shield,
  Zap,
  Star,
  ArrowRight,
  Menu,
  X,
  ChevronDown,
  Wallet,
  Target,
  MessageCircle,
  BarChart3,
  Check,
  ChevronRight,
} from "lucide-react";

/* ────────────────────────────────────────────────
   FADE-UP HELPER
──────────────────────────────────────────────── */
function FadeUp({
  children,
  delay = 0,
  className = "",
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-60px" });
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 36 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.65, delay, ease: [0.25, 0.1, 0.25, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

/* ────────────────────────────────────────────────
   SCROLL PROGRESS BAR (C.1)
──────────────────────────────────────────────── */
function ScrollProgress() {
  const [progress, setProgress] = useState(0);
  useEffect(() => {
    const onScroll = () => {
      const total = document.body.scrollHeight - window.innerHeight;
      if (total > 0) setProgress((window.scrollY / total) * 100);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  return (
    <div className="fixed top-0 left-0 right-0 z-[9999] h-[3px] bg-transparent pointer-events-none">
      <motion.div
        className="h-full rounded-full"
        style={{
          width: `${progress}%`,
          background: "linear-gradient(90deg, #6366f1, #a855f7, #ec4899)",
        }}
        transition={{ duration: 0.05 }}
      />
    </div>
  );
}

/* ────────────────────────────────────────────────
   NAVBAR
──────────────────────────────────────────────── */
function Navbar({ onCTA }: { onCTA: () => void }) {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const h = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", h, { passive: true });
    return () => window.removeEventListener("scroll", h);
  }, []);

  const links = [
    { label: "Hakkında", href: "#about" },
    { label: "Özellikler", href: "#features" },
    { label: "Nasıl Çalışır", href: "#how" },
  ];

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-white/85 backdrop-blur-xl border-b border-gray-100/80 shadow-sm"
          : "bg-transparent"
      }`}
    >
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <a href="#" className="flex items-center gap-2 group">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center shadow-sm group-hover:shadow-md transition-shadow">
            <ShoppingBag className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-gray-900 text-sm tracking-tight">FinShop AI</span>
        </a>

        <nav className="hidden md:flex items-center gap-8">
          {links.map((l) => (
            <a key={l.label} href={l.href} className="text-sm text-gray-600 hover:text-gray-900 transition-colors font-medium relative group">
              {l.label}
              <span className="absolute -bottom-0.5 left-0 w-0 h-px bg-indigo-500 group-hover:w-full transition-all duration-200" />
            </a>
          ))}
        </nav>

        <div className="hidden md:flex items-center gap-3">
          <a href="/login" target="_blank" rel="noopener noreferrer" className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors">
            Giriş Yap
          </a>
          <a
            href="/login?mode=register"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-semibold bg-gray-900 hover:bg-gray-800 text-white px-4 py-2 rounded-full transition-all duration-200 active:scale-95 shadow-sm hover:shadow-md"
          >
            Kayıt Ol
          </a>
        </div>

        <button className="md:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors" onClick={() => setOpen((v) => !v)}>
          {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22 }}
            className="md:hidden overflow-hidden bg-white/95 backdrop-blur-xl border-b border-gray-100"
          >
            <div className="px-6 py-4 flex flex-col gap-3">
              {links.map((l) => (
                <a key={l.label} href={l.href} onClick={() => setOpen(false)} className="text-sm font-medium text-gray-700 py-1">
                  {l.label}
                </a>
              ))}
              <button onClick={() => { setOpen(false); onCTA(); }} className="mt-2 text-sm font-semibold bg-gray-900 text-white px-4 py-2.5 rounded-full text-center">
                Şimdi Dene
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}

/* ────────────────────────────────────────────────
   HERO  (B.1 — parallax + enhanced card stack)
──────────────────────────────────────────────── */
function Hero({ onCTA }: { onCTA: () => void }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [mouse, setMouse] = useState({ x: 0, y: 0 });
  const [typed, setTyped] = useState("");
  const fullText = "1500 TL'ye kadar telefon öner...";

  /* Mouse parallax */
  const onMouseMove = useCallback((e: React.MouseEvent) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    setMouse({
      x: ((e.clientX - rect.left) / rect.width - 0.5) * 20,
      y: ((e.clientY - rect.top) / rect.height - 0.5) * 20,
    });
  }, []);

  /* Typewriter for chat demo */
  useEffect(() => {
    let i = 0;
    const id = setInterval(() => {
      i++;
      setTyped(fullText.slice(0, i));
      if (i >= fullText.length) clearInterval(id);
    }, 60);
    return () => clearInterval(id);
  }, []);

  return (
    <section
      ref={containerRef}
      onMouseMove={onMouseMove}
      onMouseLeave={() => setMouse({ x: 0, y: 0 })}
      className="min-h-screen flex items-center pt-16 pb-12 px-6"
    >
      <div className="max-w-6xl mx-auto w-full grid md:grid-cols-2 gap-12 items-center">
        {/* Left */}
        <div>
          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.1 }}>
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-600 bg-indigo-50 px-3 py-1 rounded-full mb-6 border border-indigo-100">
              <Zap className="w-3 h-3" /> AI destekli alışveriş asistanı
            </span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.2 }}
            className="text-5xl md:text-6xl font-extrabold text-gray-900 leading-[1.08] tracking-tight mb-6"
          >
            Cüzdanını bilen
            <br />
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-500">
              alışveriş asistanı
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.35 }}
            className="text-lg text-gray-500 leading-relaxed mb-8 max-w-md"
          >
            Finansal profilini analiz ederek sana özel alışveriş önerileri sunar. Bütçeni aşmadan, ihtiyacına tam uyan ürünleri keşfet.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.5 }}
            className="flex flex-col sm:flex-row gap-3"
          >
            <button
              onClick={onCTA}
              className="group flex items-center justify-center gap-2 bg-gray-900 hover:bg-gray-800 text-white font-semibold px-6 py-3 rounded-full transition-all duration-150 active:scale-95 shadow-md hover:shadow-lg text-sm relative overflow-hidden"
            >
              <span className="absolute inset-0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-500 bg-gradient-to-r from-transparent via-white/10 to-transparent" />
              Ücretsiz Başla <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            </button>
            <a
              href="#about"
              className="flex items-center justify-center gap-2 bg-white/70 hover:bg-white text-gray-700 font-medium px-6 py-3 rounded-full border border-gray-200 transition-all duration-150 text-sm backdrop-blur-sm"
            >
              Daha Fazla <ChevronDown className="w-4 h-4" />
            </a>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8, duration: 0.5 }}
            className="mt-10 flex items-center gap-6"
          >
            {[
              { icon: Star, text: "Beta sürümü" },
              { icon: Shield, text: "Güvenli & Şifreli" },
              { icon: Zap, text: "Yakında herkese açık" },
            ].map(({ icon: Icon, text }) => (
              <div key={text} className="flex items-center gap-1.5 text-xs text-gray-500">
                <Icon className="w-3.5 h-3.5 text-indigo-500" />
                {text}
              </div>
            ))}
          </motion.div>
        </div>

        {/* Right — parallax card stack */}
        <motion.div
          initial={{ opacity: 0, x: 40 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, delay: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
          className="hidden md:flex justify-center items-center"
        >
          <div className="relative w-[340px] h-[340px]">
            {/* Back card */}
            <motion.div
              animate={{ y: [0, -10, 0] }}
              transition={{ duration: 5.5, repeat: Infinity, ease: "easeInOut" }}
              style={{ x: mouse.x * 0.6, y: mouse.y * 0.6 }}
              className="absolute top-10 left-10 w-64 h-40 rounded-2xl bg-gradient-to-br from-purple-400 to-pink-400 shadow-xl opacity-50"
            />
            {/* Mid card */}
            <motion.div
              animate={{ y: [0, -6, 0] }}
              transition={{ duration: 4.5, repeat: Infinity, ease: "easeInOut", delay: 0.4 }}
              style={{ x: mouse.x * 0.4, y: mouse.y * 0.4 }}
              className="absolute top-5 left-5 w-64 h-40 rounded-2xl bg-gradient-to-br from-indigo-400 to-purple-400 shadow-xl opacity-75"
            />
            {/* Front card */}
            <motion.div
              animate={{ y: [0, -7, 0] }}
              transition={{ duration: 4.8, repeat: Infinity, ease: "easeInOut", delay: 0.2 }}
              style={{ x: mouse.x * 0.2, y: mouse.y * 0.2 }}
              className="absolute top-0 left-0 w-64 h-40 rounded-2xl shadow-2xl overflow-hidden"
            >
              <div
                className="w-full h-full p-5"
                style={{
                  background: "rgba(255,255,255,0.88)",
                  backdropFilter: "blur(20px)",
                  border: "1px solid rgba(255,255,255,0.9)",
                }}
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Aylık Bütçe</span>
                  <div className="w-6 h-6 rounded-full bg-indigo-100 flex items-center justify-center">
                    <Wallet className="w-3 h-3 text-indigo-600" />
                  </div>
                </div>
                <p className="text-2xl font-bold text-gray-900 font-numeric">₺12.500</p>
                <p className="text-xs text-emerald-600 font-semibold mt-1">+%18 tasarruf bu ay</p>
                <div className="mt-3 w-full bg-gray-100 rounded-full h-1.5">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: "60%" }}
                    transition={{ duration: 1.2, delay: 1.2, ease: "easeOut" }}
                    className="h-1.5 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500"
                  />
                </div>
              </div>
            </motion.div>

            {/* Chip — bütçeye uygun */}
            <motion.div
              animate={{ y: [0, -5, 0] }}
              transition={{ duration: 3.5, repeat: Infinity, ease: "easeInOut", delay: 0.8 }}
              style={{ x: mouse.x * 0.35, y: mouse.y * 0.35 }}
              className="absolute bottom-12 right-0 bg-white rounded-xl px-3 py-2 shadow-lg border border-gray-100 text-xs"
            >
              <div className="flex items-center gap-1.5">
                <div className="w-5 h-5 rounded-full bg-emerald-100 flex items-center justify-center">
                  <Check className="w-3 h-3 text-emerald-600" />
                </div>
                <span className="font-semibold text-gray-800">Bütçeye uygun!</span>
              </div>
              <p className="text-gray-400 mt-0.5 ml-6">Samsung TV — ₺8.299</p>
            </motion.div>

            {/* Typewriter chat bubble */}
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.9 }}
              style={{ x: mouse.x * 0.15 }}
              className="absolute -bottom-2 left-0 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl px-3 py-2 shadow-lg text-xs max-w-[200px]"
            >
              <p className="font-medium text-white/80 text-[10px] mb-0.5">Siz yazdınız</p>
              <p className="font-semibold">{typed}<span className="animate-pulse">|</span></p>
            </motion.div>

            {/* Sparkline mini card */}
            <motion.div
              animate={{ y: [0, -4, 0] }}
              transition={{ duration: 4, repeat: Infinity, ease: "easeInOut", delay: 1.2 }}
              style={{ x: mouse.x * 0.45, y: mouse.y * 0.45 }}
              className="absolute top-0 right-0 bg-white rounded-xl px-3 py-2 shadow-lg border border-gray-100 text-xs flex items-center gap-2"
            >
              <BarChart3 className="w-4 h-4 text-indigo-500" />
              <div>
                <p className="font-semibold text-gray-800">%23 tasarruf</p>
                <p className="text-gray-400">bu ay</p>
              </div>
            </motion.div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

/* ────────────────────────────────────────────────
   WHAT IS IT  (A.1 — metin düzeltmeleri)
──────────────────────────────────────────────── */
function WhatIsIt() {
  const miniCards = [
    { icon: Brain, label: "Akıllı Analiz", desc: "Verilerini öğrenir, sana uyum sağlar", color: "indigo" },
    { icon: Target, label: "Hedef Odaklı", desc: "Tasarruf hedeflerini takip eder", color: "purple" },
    { icon: MessageCircle, label: "Sohbet Arayüzü", desc: "Doğal dilde sorgu yap", color: "pink" },
    { icon: BarChart3, label: "Bütçe Analizi", desc: "Detaylı harcama raporları", color: "emerald" },
  ] as const;

  const colorMap = {
    indigo: { bg: "bg-indigo-50", text: "text-indigo-600" },
    purple: { bg: "bg-purple-50", text: "text-purple-600" },
    pink:   { bg: "bg-pink-50",   text: "text-pink-600" },
    emerald:{ bg: "bg-emerald-50",text: "text-emerald-600" },
  };

  return (
    <section id="about" className="py-24 px-6">
      <div className="max-w-6xl mx-auto grid md:grid-cols-2 gap-16 items-center">
        <FadeUp>
          <span className="text-xs font-semibold text-purple-600 uppercase tracking-widest">Hakkında</span>
          <h2 className="text-4xl font-extrabold text-gray-900 mt-3 mb-6 leading-tight tracking-tight">
            FinShop AI nedir?
          </h2>
          <p className="text-gray-500 leading-relaxed mb-4">
            FinShop AI, finansal profilini — gelirini, giderlerini ve tasarruf hedeflerini — derinlemesine
            analiz ederek sana özel alışveriş önerileri sunan bir yapay zeka asistanıdır.
          </p>
          <p className="text-gray-500 leading-relaxed mb-6">
            Sadece fiyat karşılaştırmaz; bütçeni, harcama alışkanlıklarını ve uzun vadeli hedeflerini
            göz önünde bulundurarak gerçekten ihtiyacın olan ürünü önerir.
          </p>
          <div className="flex flex-col gap-3">
            {[
              "Finansal profiline göre kişiselleştirilmiş öneriler",
              "Gerçek zamanlı bütçe takibi ve uyarılar",
              "Tasarruf odaklı akıllı alışveriş planlaması",
            ].map((item) => (
              <div key={item} className="flex items-start gap-3">
                <div className="w-5 h-5 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Check className="w-3 h-3 text-indigo-600" />
                </div>
                <span className="text-sm text-gray-700">{item}</span>
              </div>
            ))}
          </div>
        </FadeUp>

        <FadeUp delay={0.15}>
          <div className="grid grid-cols-2 gap-4">
            {miniCards.map(({ icon: Icon, label, desc, color }) => (
              <div
                key={label}
                className="p-5 rounded-2xl transition-all duration-200 hover:-translate-y-1 cursor-default"
                style={{
                  background: "rgba(255,255,255,0.72)",
                  backdropFilter: "blur(16px)",
                  border: "1px solid rgba(255,255,255,0.85)",
                  boxShadow: "0 4px 20px rgba(31,38,135,0.08)",
                }}
              >
                <div className={`w-9 h-9 rounded-xl flex items-center justify-center mb-3 ${colorMap[color].bg}`}>
                  <Icon className={`${colorMap[color].text}`} size={18} />
                </div>
                <p className="text-sm font-bold text-gray-800 mb-1">{label}</p>
                <p className="text-xs text-gray-500">{desc}</p>
              </div>
            ))}
          </div>
        </FadeUp>
      </div>
    </section>
  );
}

/* ────────────────────────────────────────────────
   STORY  (B.2 — timeline + scroll-triggered)
──────────────────────────────────────────────── */
function StoryItem({ num, text, delay }: { num: string; text: string; delay: number }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, x: -24 }}
      animate={inView ? { opacity: 1, x: 0 } : {}}
      transition={{ duration: 0.65, delay, ease: [0.25, 0.1, 0.25, 1] }}
      className="flex gap-6 items-start relative"
    >
      {/* Timeline dot */}
      <div className="flex flex-col items-center flex-shrink-0">
        <motion.div
          initial={{ scale: 0 }}
          animate={inView ? { scale: 1 } : {}}
          transition={{ duration: 0.4, delay: delay + 0.1, type: "spring" }}
          className="w-3 h-3 rounded-full bg-gradient-to-br from-indigo-500 to-purple-500 shadow-sm shadow-indigo-300 mt-2"
        />
      </div>
      {/* Number + text */}
      <div className="pb-8">
        <motion.span
          initial={{ opacity: 0, scale: 0.6 }}
          animate={inView ? { opacity: 1, scale: 1 } : {}}
          transition={{ duration: 0.5, delay }}
          className="block text-7xl font-extrabold leading-none mb-3 select-none"
          style={{
            WebkitTextStroke: "2px",
            WebkitTextFillColor: "transparent",
            backgroundImage: "linear-gradient(135deg, #6366f1, #a855f7)",
            WebkitBackgroundClip: "text",
            backgroundClip: "text",
          }}
        >
          {num}
        </motion.span>
        <motion.p
          initial={{ opacity: 0, filter: "blur(4px)" }}
          animate={inView ? { opacity: 1, filter: "blur(0px)" } : {}}
          transition={{ duration: 0.55, delay: delay + 0.2 }}
          className="text-gray-600 leading-relaxed"
        >
          {text}
        </motion.p>
      </div>
    </motion.div>
  );
}

function Story() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-3xl mx-auto">
        <FadeUp className="text-center mb-16">
          <span className="text-xs font-semibold text-emerald-600 uppercase tracking-widest">Hikaye</span>
          <h2 className="text-4xl font-extrabold text-gray-900 mt-3 leading-tight tracking-tight">
            Nasıl ortaya çıktı?
          </h2>
        </FadeUp>

        {/* Timeline line + items */}
        <div className="relative pl-6">
          {/* Vertical line */}
          <div className="absolute left-[5px] top-2 bottom-2 w-px bg-gradient-to-b from-indigo-200 via-purple-200 to-transparent" />

          {[
            {
              num: "01",
              text: "Her ay alışveriş yaparken bütçesini aşan insanlar için başladı her şey. İnternette binlerce ürün var ama hiçbiri 'bu sana göre mi?' diye sormuyor.",
              delay: 0,
            },
            {
              num: "02",
              text: "Yapay zekanın kişiselleştirme gücünü finansal farkındalıkla birleştirme fikri doğdu. Sadece ne almak istediğini değil, neyi alabileceğini de anlayan bir asistan.",
              delay: 0.1,
            },
            {
              num: "03",
              text: "FinShop AI bugün binlerce kullanıcının aylık alışveriş bütçesini ortalama %23 optimize ediyor. Çünkü en iyi alışveriş, pişman olmayan alışveriştir.",
              delay: 0.2,
            },
          ].map((item) => (
            <StoryItem key={item.num} {...item} />
          ))}
        </div>
      </div>
    </section>
  );
}

/* ────────────────────────────────────────────────
   FEATURES  (B.4 — hover glow border)
──────────────────────────────────────────────── */
function FeatureCard({
  icon: Icon,
  title,
  desc,
  color,
  bg,
  delay,
}: {
  icon: React.ElementType;
  title: string;
  desc: string;
  color: string;
  bg: string;
  delay: number;
}) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-60px" });
  const [hovered, setHovered] = useState(false);

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 36 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.65, delay, ease: [0.25, 0.1, 0.25, 1] }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="relative rounded-2xl p-6 h-full flex flex-col cursor-default"
      style={{
        background: "rgba(255,255,255,0.72)",
        backdropFilter: "blur(16px)",
        border: hovered ? "1px solid transparent" : "1px solid rgba(255,255,255,0.85)",
        boxShadow: hovered
          ? "0 8px 40px rgba(99,102,241,0.18), 0 2px 12px rgba(99,102,241,0.1)"
          : "0 4px 24px rgba(31,38,135,0.07)",
        transform: hovered ? "translateY(-4px)" : "translateY(0)",
        backgroundImage: hovered
          ? "linear-gradient(rgba(255,255,255,0.88),rgba(255,255,255,0.88)), linear-gradient(135deg,#6366f1,#a855f7,#ec4899,#6366f1)"
          : undefined,
        backgroundOrigin: "border-box",
        backgroundClip: hovered ? "padding-box, border-box" : undefined,
        transition: "all 0.25s ease",
      }}
    >
      <div className={`w-12 h-12 rounded-2xl ${bg} flex items-center justify-center mb-4`}>
        <div className={`w-8 h-8 rounded-xl bg-gradient-to-br ${color} flex items-center justify-center`}>
          <Icon className="w-4 h-4 text-white" />
        </div>
      </div>
      <h3 className="text-lg font-bold text-gray-900 mb-3">{title}</h3>
      <p className="text-sm text-gray-500 leading-relaxed flex-1">{desc}</p>
    </motion.div>
  );
}

function Features() {
  const features = [
    {
      icon: Brain,
      title: "Finansal Zeka",
      desc: "Gelir, gider ve tasarruf hedeflerini öğrenerek her öneriyi sana özel kılar. Ne kadar harcayabileceğini her zaman bilir.",
      color: "from-indigo-500 to-purple-600",
      bg: "bg-indigo-50",
    },
    {
      icon: MessageCircle,
      title: "Doğal Dil Arayüzü",
      desc: '"Yazın için sıcak bir mont arıyorum, 2000 TL bütçem var" gibi günlük konuşma dilinle arama yap. Teknik terim gerektirmez.',
      color: "from-purple-500 to-pink-600",
      bg: "bg-purple-50",
    },
    {
      icon: TrendingUp,
      title: "Tasarruf Takibi",
      desc: "Her alışverişten sonra ne kadar tasarruf ettiğini görürsün. Aylık raporlar ve önerilerle bütçeni sürekli optimize eder.",
      color: "from-emerald-500 to-teal-600",
      bg: "bg-emerald-50",
    },
  ];

  return (
    <section id="features" className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        <FadeUp className="text-center mb-16">
          <span className="text-xs font-semibold text-indigo-600 uppercase tracking-widest">Özellikler</span>
          <h2 className="text-4xl font-extrabold text-gray-900 mt-3 leading-tight tracking-tight">
            Neden FinShop AI?
          </h2>
          <p className="text-gray-500 mt-4 max-w-lg mx-auto">
            Rakiplerinden farkı: sana özel düşünen bir asistan
          </p>
        </FadeUp>
        <div className="grid md:grid-cols-3 gap-6">
          {features.map((f, i) => (
            <FeatureCard key={f.title} {...f} delay={i * 0.1} />
          ))}
        </div>
      </div>
    </section>
  );
}

/* ────────────────────────────────────────────────
   HOW IT HELPS  (B.3 — horizontal scroll snap)
──────────────────────────────────────────────── */

/* Scenario preview mockups */
function ElectronicsMockup() {
  const [show, setShow] = useState(false);
  const ref = useRef(null);
  const inView = useInView(ref, { once: true });
  useEffect(() => { if (inView) setTimeout(() => setShow(true), 400); }, [inView]);

  return (
    <div ref={ref} className="space-y-3">
      {/* User message */}
      <motion.div
        initial={{ opacity: 0, x: 20 }} animate={show ? { opacity: 1, x: 0 } : {}}
        transition={{ duration: 0.4 }}
        className="ml-auto w-fit bg-gradient-to-r from-indigo-500 to-purple-600 text-white text-xs rounded-2xl rounded-br-sm px-3 py-2 max-w-[200px] shadow-sm"
      >
        1500 TL'ye kadar iyi bir telefon öner
      </motion.div>
      {/* AI response */}
      <motion.div
        initial={{ opacity: 0, x: -20 }} animate={show ? { opacity: 1, x: 0 } : {}}
        transition={{ duration: 0.4, delay: 0.5 }}
        className="bg-white rounded-2xl rounded-bl-sm px-3 py-2 shadow-md border border-gray-100 text-xs max-w-[220px]"
      >
        <p className="text-gray-500 mb-2">Bütçene uygun 3 seçenek buldum:</p>
        {[
          { name: "Redmi 13C", price: "₺1.299", tag: "En Uygun" },
          { name: "Samsung A15", price: "₺1.499", tag: "En Popüler" },
        ].map((p) => (
          <div key={p.name} className="flex items-center justify-between py-1.5 border-b border-gray-50 last:border-0">
            <div>
              <p className="font-semibold text-gray-800">{p.name}</p>
              <span className="text-[10px] text-indigo-500 font-semibold">{p.tag}</span>
            </div>
            <span className="font-bold text-emerald-600">{p.price}</span>
          </div>
        ))}
      </motion.div>
    </div>
  );
}

function GoalMockup() {
  const [pct, setPct] = useState(0);
  const ref = useRef(null);
  const inView = useInView(ref, { once: true });
  useEffect(() => { if (inView) setTimeout(() => setPct(65), 400); }, [inView]);

  return (
    <div ref={ref} className="flex flex-col items-center gap-4">
      {/* Progress ring */}
      <div className="relative w-28 h-28">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="40" fill="none" stroke="#e5e7eb" strokeWidth="8" />
          <motion.circle
            cx="50" cy="50" r="40" fill="none"
            stroke="url(#goalGrad)" strokeWidth="8" strokeLinecap="round"
            strokeDasharray={`${2 * Math.PI * 40}`}
            initial={{ strokeDashoffset: 2 * Math.PI * 40 }}
            animate={{ strokeDashoffset: 2 * Math.PI * 40 * (1 - pct / 100) }}
            transition={{ duration: 1.2, ease: "easeOut", delay: 0.3 }}
          />
          <defs>
            <linearGradient id="goalGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#6366f1" />
              <stop offset="100%" stopColor="#a855f7" />
            </linearGradient>
          </defs>
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xl font-extrabold text-gray-900 font-numeric">%{pct}</span>
          <span className="text-[10px] text-gray-400">tamamlandı</span>
        </div>
      </div>
      <div className="text-center">
        <p className="text-xs font-semibold text-gray-700">Tatil Hedefi</p>
        <p className="text-sm font-extrabold text-gray-900 font-numeric">₺3.250 / ₺5.000</p>
        <p className="text-[11px] text-indigo-500 mt-1">65 gün kaldı</p>
      </div>
      {/* Monthly bars */}
      <div className="flex items-end gap-1.5 h-10">
        {[40, 55, 48, 65, 72, 80].map((h, i) => (
          <motion.div
            key={i}
            initial={{ height: 0 }}
            animate={inView ? { height: `${h}%` } : {}}
            transition={{ duration: 0.5, delay: 0.5 + i * 0.08 }}
            className="w-4 rounded-sm bg-gradient-to-t from-indigo-400 to-purple-400"
            style={{ minHeight: 4 }}
          />
        ))}
      </div>
    </div>
  );
}

function BudgetMockup() {
  const categories = [
    { name: "Market", amount: "₺2.400", icon: "🛒", ok: false },
    { name: "Eğlence", amount: "₺800",  icon: "🎬", ok: true },
    { name: "Ulaşım",  amount: "₺600",  icon: "🚌", ok: true },
  ];
  const ref = useRef(null);
  const inView = useInView(ref, { once: true });

  return (
    <div ref={ref} className="space-y-2.5 w-full max-w-[220px]">
      {categories.map(({ name, amount, icon, ok }, i) => (
        <motion.div
          key={name}
          initial={{ opacity: 0, x: 16 }}
          animate={inView ? { opacity: 1, x: 0 } : {}}
          transition={{ duration: 0.4, delay: 0.3 + i * 0.12 }}
          className="flex items-center justify-between bg-white rounded-xl px-3 py-2 shadow-sm border border-gray-50"
        >
          <div className="flex items-center gap-2">
            <span className="text-base">{icon}</span>
            <span className="text-xs font-semibold text-gray-700">{name}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-bold text-gray-800 font-numeric">{amount}</span>
            <span className={`text-[11px] ${ok ? "text-emerald-500" : "text-red-400"}`}>{ok ? "✓" : "↑"}</span>
          </div>
        </motion.div>
      ))}
      <motion.div
        initial={{ scaleX: 0 }}
        animate={inView ? { scaleX: 1 } : {}}
        transition={{ duration: 0.8, delay: 0.7 }}
        className="h-2 rounded-full overflow-hidden bg-gray-100 mt-1"
        style={{ originX: 0 }}
      >
        <div className="h-full w-[72%] bg-gradient-to-r from-emerald-400 to-teal-400 rounded-full" />
      </motion.div>
      <p className="text-[11px] text-gray-400 text-right">Bütçe sağlığı: <span className="text-emerald-600 font-semibold">İyi</span></p>
    </div>
  );
}

function HowItHelps() {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeIdx, setActiveIdx] = useState(0);
  const isDragging = useRef(false);
  const dragStartX = useRef(0);
  const dragScrollLeft = useRef(0);

  const onMouseDown = (e: React.MouseEvent) => {
    const el = scrollRef.current;
    if (!el) return;
    isDragging.current = true;
    dragStartX.current = e.pageX - el.offsetLeft;
    dragScrollLeft.current = el.scrollLeft;
    el.style.cursor = "grabbing";
    el.style.userSelect = "none";
  };

  const onMouseUpOrLeave = () => {
    isDragging.current = false;
    if (scrollRef.current) {
      scrollRef.current.style.cursor = "grab";
      scrollRef.current.style.userSelect = "";
    }
  };

  const onMouseMove = (e: React.MouseEvent) => {
    if (!isDragging.current) return;
    const el = scrollRef.current;
    if (!el) return;
    e.preventDefault();
    const x = e.pageX - el.offsetLeft;
    const walk = (x - dragStartX.current) * 1.2;
    el.scrollLeft = dragScrollLeft.current - walk;
  };

  const cases = [
    {
      num: "SENARYO 01",
      icon: ShoppingBag,
      title: "Elektronik Alışverişi",
      desc: 'Yeni telefon almak istiyorsun ama hangisi bütçene uygun? "1500 TL\'ye kadar bana iyi bir telefon öner" de, gerisini biz halledelim.',
      highlight: "Ortalama %19 daha az harcama",
      preview: <ElectronicsMockup />,
      bgLeft: "from-indigo-50 to-purple-50/50",
    },
    {
      num: "SENARYO 02",
      icon: Target,
      title: "Hedef Tabanlı Planlama",
      desc: "3 ay içinde tatil için 5.000 TL biriktirmek mi istiyorsun? FinShop AI aylık alışveriş planını buna göre ayarlar.",
      highlight: "Hedeflere 2× daha hızlı ulaş",
      preview: <GoalMockup />,
      bgLeft: "from-emerald-50 to-teal-50/50",
    },
    {
      num: "SENARYO 03",
      icon: Wallet,
      title: "Bütçe Kontrolü",
      desc: "Ay sonunda 'nasıl bu kadar harcadım?' diye sormak istemiyor musun? Gerçek zamanlı uyarılar ve önerilerle bütçende kal.",
      highlight: "%94 kullanıcı memnuniyeti",
      preview: <BudgetMockup />,
      bgLeft: "from-pink-50 to-rose-50/50",
    },
  ];

  /* Track active card via scroll */
  const onScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const idx = Math.round(el.scrollLeft / (el.scrollWidth / cases.length));
    setActiveIdx(Math.min(idx, cases.length - 1));
  }, [cases.length]);

  const scrollTo = (i: number) => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ left: i * (el.scrollWidth / cases.length), behavior: "smooth" });
  };

  return (
    <section id="how" className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        <FadeUp className="text-center mb-10">
          <span className="text-xs font-semibold text-pink-600 uppercase tracking-widest">Kullanım</span>
          <h2 className="text-4xl font-extrabold text-gray-900 mt-3 leading-tight tracking-tight">
            Günlük hayatı nasıl kolaylaştırır?
          </h2>

          {/* Progress dots */}
          <div className="flex items-center justify-center gap-3 mt-6">
            {cases.map((_, i) => (
              <button
                key={i}
                onClick={() => scrollTo(i)}
                className={`rounded-full transition-all duration-300 ${
                  i === activeIdx ? "w-8 h-2 bg-indigo-500" : "w-2 h-2 bg-gray-300"
                }`}
              />
            ))}
          </div>
        </FadeUp>

        {/* Horizontal scroll container */}
        <div
          ref={scrollRef}
          onScroll={onScroll}
          onMouseDown={onMouseDown}
          onMouseMove={onMouseMove}
          onMouseUp={onMouseUpOrLeave}
          onMouseLeave={onMouseUpOrLeave}
          className="flex gap-6 overflow-x-auto pb-6 snap-x snap-mandatory scrollbar-hide"
          style={{ scrollbarWidth: "none", msOverflowStyle: "none", cursor: "grab" }}
        >
          {cases.map(({ num, icon: Icon, title, desc, highlight, preview, bgLeft }) => (
            <div
              key={title}
              className="snap-center flex-shrink-0 w-[85vw] md:w-[70vw] max-w-[800px] rounded-3xl overflow-hidden"
              style={{
                background: "rgba(255,255,255,0.80)",
                backdropFilter: "blur(20px)",
                border: "1px solid rgba(255,255,255,0.9)",
                boxShadow: "0 8px 40px rgba(31,38,135,0.1)",
              }}
            >
              <div className="grid md:grid-cols-2 h-full min-h-[400px]">
                {/* Left: info */}
                <div className={`p-8 flex flex-col justify-center bg-gradient-to-br ${bgLeft}`}>
                  <span className="text-xs font-bold text-indigo-500 tracking-widest mb-3">{num}</span>
                  <div className="w-10 h-10 rounded-xl bg-white shadow-sm flex items-center justify-center mb-4">
                    <Icon className="w-5 h-5 text-indigo-600" />
                  </div>
                  <h3 className="text-2xl font-extrabold text-gray-900 mb-3">{title}</h3>
                  <p className="text-gray-500 text-sm leading-relaxed mb-5">{desc}</p>
                  <div className="inline-flex items-center gap-2 bg-white text-emerald-700 text-xs font-bold px-4 py-2 rounded-full border border-emerald-100 shadow-sm w-fit">
                    <TrendingUp className="w-3.5 h-3.5" />
                    {highlight}
                  </div>
                  <button className="mt-4 flex items-center gap-1 text-xs text-indigo-500 font-semibold hover:gap-2 transition-all w-fit">
                    Detayları gör <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Right: live mockup */}
                <div className="p-8 flex items-center justify-center bg-white/40">
                  {preview}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ────────────────────────────────────────────────
   CTA BANNER  (C.5 — shimmer + floating icons)
──────────────────────────────────────────────── */
function CTABanner({ onCTA }: { onCTA: () => void }) {
  return (
    <section className="py-20 px-6">
      <FadeUp>
        <div
          className="max-w-4xl mx-auto rounded-3xl p-12 text-center relative overflow-hidden"
          style={{
            background: "linear-gradient(135deg, #312e81 0%, #4f46e5 45%, #7c3aed 100%)",
            boxShadow: "0 20px 60px rgba(79,70,229,0.4)",
          }}
        >
          {/* Animated mesh overlay */}
          <div
            className="absolute inset-0 opacity-[0.07]"
            style={{
              backgroundImage:
                "radial-gradient(circle at 25% 25%, white 1px, transparent 1px), radial-gradient(circle at 75% 75%, white 1px, transparent 1px)",
              backgroundSize: "40px 40px",
            }}
          />
          {/* Floating shopping icons */}
          {[
            { icon: ShoppingBag, top: "12%", left: "8%",  size: 22, delay: 0 },
            { icon: Star,        top: "20%", right: "10%", size: 18, delay: 0.8 },
            { icon: Wallet,      bottom: "15%", left: "12%", size: 20, delay: 0.4 },
            { icon: Zap,         bottom: "20%", right: "8%", size: 16, delay: 1.2 },
          ].map(({ icon: Icon, size, delay, ...pos }, i) => (
            <motion.div
              key={i}
              animate={{ y: [0, -8, 0], rotate: [0, 8, -8, 0] }}
              transition={{ duration: 4 + i, repeat: Infinity, ease: "easeInOut", delay }}
              className="absolute text-white/20"
              style={pos as React.CSSProperties}
            >
              <Icon size={size} />
            </motion.div>
          ))}

          <div className="relative">
            <h2 className="text-3xl md:text-4xl font-extrabold text-white mb-4 tracking-tight">
              Akıllı alışverişe başla
            </h2>
            <p className="text-indigo-200 mb-8 max-w-md mx-auto text-sm leading-relaxed">
              Finansal profilini oluştur, AI asistanınla tanış ve ilk önerini dakikalar içinde al.
            </p>
            <button
              onClick={onCTA}
              className="group inline-flex items-center gap-2 bg-white text-indigo-700 font-bold px-8 py-3.5 rounded-full transition-all duration-150 active:scale-95 hover:shadow-xl text-sm hover:bg-gray-50 relative overflow-hidden"
            >
              <span className="absolute inset-0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-500 bg-gradient-to-r from-transparent via-indigo-50 to-transparent" />
              Ücretsiz Kayıt Ol <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            </button>
          </div>
        </div>
      </FadeUp>
    </section>
  );
}

/* ────────────────────────────────────────────────
   FOOTER  (A.3 — tek geliştirici)
──────────────────────────────────────────────── */
function Footer() {
  return (
    <footer className="border-t border-gray-100/80">
      <div className="max-w-6xl mx-auto px-6 py-14 grid md:grid-cols-4 gap-10">
        <div className="md:col-span-2">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center">
              <ShoppingBag className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-gray-900 text-sm">FinShop AI</span>
          </div>
          <p className="text-sm text-gray-500 leading-relaxed max-w-xs">
            Finansal profiline göre kişiselleştirilmiş alışveriş önerileri sunan AI destekli asistanın.
          </p>
        </div>

        <div>
          <p className="text-xs font-semibold text-gray-900 uppercase tracking-wider mb-4">Ürün</p>
          <ul className="flex flex-col gap-2">
            {[
              { label: "Özellikler", href: "#features" },
              { label: "Nasıl Çalışır", href: "#how" },
              { label: "Giriş Yap", href: "/login" },
              { label: "Kayıt Ol", href: "/login?mode=register" },
            ].map((l) => (
              <li key={l.label}>
                <a href={l.href} className="text-sm text-gray-500 hover:text-gray-800 transition-colors">
                  {l.label}
                </a>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <p className="text-xs font-semibold text-gray-900 uppercase tracking-wider mb-4">Geliştirici</p>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-400 to-purple-400 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
              ES
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-800">Enes Sarpün</p>
              <p className="text-xs text-gray-400">Full-Stack Developer</p>
            </div>
          </div>
        </div>
      </div>

      <div className="px-6 py-5" style={{ background: "rgba(15,15,20,0.96)" }}>
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-3">
          <p className="text-xs text-gray-500">© 2026 FinShop AI. Tüm hakları saklıdır.</p>
          <div className="flex items-center gap-4">
            {["Gizlilik", "Kullanım Şartları", "İletişim"].map((l) => (
              <a key={l} href="#" className="text-xs text-gray-500 hover:text-gray-300 transition-colors">
                {l}
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}

/* ────────────────────────────────────────────────
   SECTION DIVIDER  (C.2)
──────────────────────────────────────────────── */
function Divider() {
  return (
    <div className="max-w-6xl mx-auto px-6 flex items-center gap-4 my-2">
      <div className="flex-1 h-px bg-gradient-to-r from-transparent via-gray-200 to-transparent" />
      <motion.div
        animate={{ scale: [1, 1.4, 1], opacity: [0.4, 1, 0.4] }}
        transition={{ duration: 2.5, repeat: Infinity }}
        className="w-1.5 h-1.5 rounded-full bg-indigo-300"
      />
      <div className="flex-1 h-px bg-gradient-to-r from-transparent via-gray-200 to-transparent" />
    </div>
  );
}

/* ────────────────────────────────────────────────
   ROOT
──────────────────────────────────────────────── */
export default function Home() {
  const router = useRouter();

  const handleCTA = () => {
    const token = localStorage.getItem("access_token");
    router.push(token ? "/dashboard" : "/login?mode=register");
  };

  return (
    <>
      <ScrollProgress />
      <main className="min-h-screen">
        <Navbar onCTA={handleCTA} />
        <Hero onCTA={handleCTA} />
        <Divider />
        <WhatIsIt />
        <Divider />
        <Story />
        <Divider />
        <Features />
        <Divider />
        <HowItHelps />
        <CTABanner onCTA={handleCTA} />
        <Footer />
      </main>
    </>
  );
}
