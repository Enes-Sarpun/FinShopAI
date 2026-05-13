"use client";
import { useEffect, useRef, useState } from "react";
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
} from "lucide-react";

/* ─── Reusable section fade-up ─── */
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
  const inView = useInView(ref, { once: true, margin: "-80px" });
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 40 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.7, delay, ease: [0.25, 0.1, 0.25, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

/* ─── Nav ─── */
function Navbar({ onCTA }: { onCTA: () => void }) {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handler);
    return () => window.removeEventListener("scroll", handler);
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
          ? "bg-white/80 backdrop-blur-xl border-b border-gray-100 shadow-sm"
          : "bg-transparent"
      }`}
    >
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <a href="#" className="flex items-center gap-2 group">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center shadow-sm group-hover:shadow-md transition-shadow">
            <ShoppingBag className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-gray-900 text-sm tracking-tight">FinShop AI</span>
        </a>

        {/* Desktop links */}
        <nav className="hidden md:flex items-center gap-8">
          {links.map((l) => (
            <a
              key={l.label}
              href={l.href}
              className="text-sm text-gray-600 hover:text-gray-900 transition-colors font-medium"
            >
              {l.label}
            </a>
          ))}
        </nav>

        {/* CTA */}
        <div className="hidden md:flex items-center gap-3">
          <a
            href="/login"
            className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
          >
            Giriş Yap
          </a>
          <button
            onClick={onCTA}
            className="text-sm font-semibold bg-gray-900 hover:bg-gray-800 text-white px-4 py-2 rounded-full transition-all duration-150 active:scale-95 shadow-sm hover:shadow-md"
          >
            Şimdi Dene
          </button>
        </div>

        {/* Mobile hamburger */}
        <button
          className="md:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors"
          onClick={() => setOpen((v) => !v)}
          aria-label="Menu"
        >
          {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile menu */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="md:hidden overflow-hidden bg-white/95 backdrop-blur-xl border-b border-gray-100"
          >
            <div className="px-6 py-4 flex flex-col gap-3">
              {links.map((l) => (
                <a
                  key={l.label}
                  href={l.href}
                  onClick={() => setOpen(false)}
                  className="text-sm font-medium text-gray-700 py-1"
                >
                  {l.label}
                </a>
              ))}
              <button
                onClick={() => { setOpen(false); onCTA(); }}
                className="mt-2 text-sm font-semibold bg-gray-900 text-white px-4 py-2.5 rounded-full text-center"
              >
                Şimdi Dene
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}

/* ─── Hero ─── */
function Hero({ onCTA }: { onCTA: () => void }) {
  return (
    <section className="min-h-screen flex items-center pt-16 pb-12 px-6">
      <div className="max-w-6xl mx-auto w-full grid md:grid-cols-2 gap-12 items-center">
        {/* Left: text */}
        <div>
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
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
            Finansal profilini analiz ederek sana özel alışveriş önerileri sunar. Bütçeni aşmadan,
            ihtiyacına tam uyan ürünleri keşfet.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.5 }}
            className="flex flex-col sm:flex-row gap-3"
          >
            <button
              onClick={onCTA}
              className="flex items-center justify-center gap-2 bg-gray-900 hover:bg-gray-800 text-white font-semibold px-6 py-3 rounded-full transition-all duration-150 active:scale-95 shadow-md hover:shadow-lg text-sm"
            >
              Ücretsiz Başla <ArrowRight className="w-4 h-4" />
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
              { icon: Star, text: "4.9/5 puan" },
              { icon: Shield, text: "Güvenli & Şifreli" },
              { icon: Zap, text: "Anında analiz" },
            ].map(({ icon: Icon, text }) => (
              <div key={text} className="flex items-center gap-1.5 text-xs text-gray-500">
                <Icon className="w-3.5 h-3.5 text-indigo-500" />
                {text}
              </div>
            ))}
          </motion.div>
        </div>

        {/* Right: decorative card stack */}
        <motion.div
          initial={{ opacity: 0, x: 40 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, delay: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
          className="hidden md:flex justify-center items-center"
        >
          <div className="relative w-80 h-80">
            {/* Back card */}
            <motion.div
              animate={{ y: [0, -8, 0] }}
              transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
              className="absolute top-8 left-8 w-64 h-40 rounded-2xl bg-gradient-to-br from-purple-400 to-pink-400 shadow-xl opacity-60"
            />
            {/* Mid card */}
            <motion.div
              animate={{ y: [0, -5, 0] }}
              transition={{ duration: 4, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
              className="absolute top-4 left-4 w-64 h-40 rounded-2xl bg-gradient-to-br from-indigo-400 to-purple-400 shadow-xl opacity-80"
            />
            {/* Front card — glassmorphism */}
            <motion.div
              animate={{ y: [0, -6, 0] }}
              transition={{ duration: 4.5, repeat: Infinity, ease: "easeInOut", delay: 0.3 }}
              className="absolute top-0 left-0 w-64 h-40 rounded-2xl shadow-2xl overflow-hidden"
              style={{
                background: "rgba(255,255,255,0.82)",
                backdropFilter: "blur(20px)",
                border: "1px solid rgba(255,255,255,0.9)",
              }}
            >
              <div className="p-5">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Aylık Bütçe</span>
                  <div className="w-6 h-6 rounded-full bg-indigo-100 flex items-center justify-center">
                    <Wallet className="w-3 h-3 text-indigo-600" />
                  </div>
                </div>
                <p className="text-2xl font-bold text-gray-900 font-numeric">₺12.500</p>
                <p className="text-xs text-emerald-600 font-semibold mt-1">+%18 tasarruf</p>
                <div className="mt-3 w-full bg-gray-100 rounded-full h-1.5">
                  <div className="w-3/5 h-1.5 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500" />
                </div>
              </div>
            </motion.div>

            {/* Floating recommendation chip */}
            <motion.div
              animate={{ y: [0, -4, 0] }}
              transition={{ duration: 3.5, repeat: Infinity, ease: "easeInOut", delay: 1 }}
              className="absolute bottom-10 right-0 bg-white rounded-xl px-3 py-2 shadow-lg border border-gray-100 text-xs"
            >
              <div className="flex items-center gap-1.5">
                <div className="w-5 h-5 rounded-full bg-emerald-100 flex items-center justify-center">
                  <Check className="w-3 h-3 text-emerald-600" />
                </div>
                <span className="font-semibold text-gray-800">Bütçeye uygun!</span>
              </div>
              <p className="text-gray-500 mt-0.5 pl-6.5">Samsung TV — ₺8.299</p>
            </motion.div>

            {/* Chat bubble */}
            <motion.div
              animate={{ y: [0, -5, 0] }}
              transition={{ duration: 4, repeat: Infinity, ease: "easeInOut", delay: 1.5 }}
              className="absolute -bottom-4 left-0 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl px-3 py-2 shadow-lg text-xs max-w-[180px]"
            >
              <p className="font-medium">Bütçen için en iyi 3 seçenek bulundu 🎯</p>
            </motion.div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

/* ─── Section 2.1: FinShop AI Nedir? ─── */
function WhatIsIt() {
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
            {[
              { icon: Brain, label: "Akıllı Analiz", desc: "Finansal verilerini anlayarak öğrenir", color: "indigo" },
              { icon: Target, label: "Hedef Odaklı", desc: "Tasarruf hedeflerini takip eder", color: "purple" },
              { icon: MessageCircle, label: "Sohbet Arayüzü", desc: "Doğal dilde ürün ara", color: "pink" },
              { icon: BarChart3, label: "Bütçe Analizi", desc: "Detaylı harcama raporları", color: "emerald" },
            ].map(({ icon: Icon, label, desc, color }) => (
              <div
                key={label}
                className="p-5 rounded-2xl transition-all duration-200 hover:-translate-y-1"
                style={{
                  background: "rgba(255,255,255,0.72)",
                  backdropFilter: "blur(16px)",
                  border: "1px solid rgba(255,255,255,0.85)",
                  boxShadow: "0 4px 20px rgba(31,38,135,0.08)",
                }}
              >
                <div
                  className={`w-9 h-9 rounded-xl flex items-center justify-center mb-3 ${
                    color === "indigo"
                      ? "bg-indigo-50"
                      : color === "purple"
                      ? "bg-purple-50"
                      : color === "pink"
                      ? "bg-pink-50"
                      : "bg-emerald-50"
                  }`}
                >
                  <Icon
                    className={`w-5 h-5 ${
                      color === "indigo"
                        ? "text-indigo-600"
                        : color === "purple"
                        ? "text-purple-600"
                        : color === "pink"
                        ? "text-pink-600"
                        : "text-emerald-600"
                    }`}
                    size={18}
                  />
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

/* ─── Section 2.2: Nasıl Ortaya Çıktı? ─── */
function Story() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-3xl mx-auto text-center">
        <FadeUp>
          <span className="text-xs font-semibold text-emerald-600 uppercase tracking-widest">Hikaye</span>
          <h2 className="text-4xl font-extrabold text-gray-900 mt-3 mb-12 leading-tight tracking-tight">
            Nasıl ortaya çıktı?
          </h2>
        </FadeUp>

        <div className="flex flex-col gap-8 text-left">
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
          ].map(({ num, text, delay }) => (
            <FadeUp key={num} delay={delay}>
              <div className="flex gap-6 items-start">
                <span className="text-5xl font-extrabold text-gray-100 leading-none flex-shrink-0 select-none">
                  {num}
                </span>
                <p className="text-gray-600 leading-relaxed pt-1">{text}</p>
              </div>
            </FadeUp>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── Section 2.3: Özellikler ─── */
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
          {features.map(({ icon: Icon, title, desc, color, bg }, i) => (
            <FadeUp key={title} delay={i * 0.1}>
              <div
                className="rounded-2xl p-6 h-full flex flex-col transition-all duration-200 hover:-translate-y-1"
                style={{
                  background: "rgba(255,255,255,0.72)",
                  backdropFilter: "blur(16px)",
                  border: "1px solid rgba(255,255,255,0.85)",
                  boxShadow: "0 4px 24px rgba(31,38,135,0.07)",
                }}
              >
                <div className={`w-12 h-12 rounded-2xl ${bg} flex items-center justify-center mb-4`}>
                  <div className={`w-8 h-8 rounded-xl bg-gradient-to-br ${color} flex items-center justify-center`}>
                    <Icon className="w-4 h-4 text-white" />
                  </div>
                </div>
                <h3 className="text-lg font-bold text-gray-900 mb-3">{title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed flex-1">{desc}</p>
              </div>
            </FadeUp>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── Section 2.4: Günlük Hayatı Nasıl Kolaylaştırır? ─── */
function HowItHelps() {
  const cases = [
    {
      icon: ShoppingBag,
      title: "Elektronik Alışverişi",
      desc: 'Yeni telefon almak istiyorsun ama hangisi bütçene uygun? "1500 TL\'ye kadar bana iyi bir telefon öner" de, gerisini biz halledelim.',
      highlight: "Ortalama %19 daha az harcama",
      reverse: false,
    },
    {
      icon: Target,
      title: "Hedef Tabanlı Planlama",
      desc: "3 ay içinde tatil için 5.000 TL biriktirmek mi istiyorsun? FinShop AI aylık alışveriş planını buna göre ayarlar.",
      highlight: "Hedeflere 2x daha hızlı ulaş",
      reverse: true,
    },
    {
      icon: Wallet,
      title: "Bütçe Kontrolü",
      desc: "Ay sonunda 'nasıl bu kadar harcadım?' diye sormak istemiyor musun? Gerçek zamanlı uyarılar ve önerilerle bütçende kal.",
      highlight: "%94 kullanıcı memnuniyeti",
      reverse: false,
    },
  ];

  return (
    <section id="how" className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        <FadeUp className="text-center mb-20">
          <span className="text-xs font-semibold text-pink-600 uppercase tracking-widest">Kullanım</span>
          <h2 className="text-4xl font-extrabold text-gray-900 mt-3 leading-tight tracking-tight">
            Günlük hayatı nasıl kolaylaştırır?
          </h2>
        </FadeUp>

        <div className="flex flex-col gap-20">
          {cases.map(({ icon: Icon, title, desc, highlight, reverse }, i) => (
            <FadeUp key={title} delay={0.05}>
              <div
                className={`grid md:grid-cols-2 gap-12 items-center ${reverse ? "md:[direction:rtl]" : ""}`}
              >
                <div className={reverse ? "[direction:ltr]" : ""}>
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mb-4">
                    <Icon className="w-5 h-5 text-white" />
                  </div>
                  <h3 className="text-2xl font-bold text-gray-900 mb-3">{title}</h3>
                  <p className="text-gray-500 leading-relaxed mb-5">{desc}</p>
                  <div className="inline-flex items-center gap-2 bg-emerald-50 text-emerald-700 text-sm font-semibold px-4 py-2 rounded-full border border-emerald-100">
                    <TrendingUp className="w-3.5 h-3.5" />
                    {highlight}
                  </div>
                </div>

                <div
                  className={`rounded-2xl p-6 min-h-[200px] flex items-center justify-center ${reverse ? "[direction:ltr]" : ""}`}
                  style={{
                    background: `rgba(${i === 0 ? "238,235,255" : i === 1 ? "235,252,245" : "255,235,235"},0.7)`,
                    backdropFilter: "blur(12px)",
                    border: "1px solid rgba(255,255,255,0.8)",
                  }}
                >
                  <div className="text-center">
                    <div className="w-16 h-16 rounded-2xl bg-white shadow-md flex items-center justify-center mx-auto mb-4">
                      <Icon
                        className={`w-8 h-8 ${i === 0 ? "text-indigo-500" : i === 1 ? "text-emerald-500" : "text-pink-500"}`}
                      />
                    </div>
                    <p className="text-xs text-gray-500 font-medium">{title} senaryosu</p>
                    <p className="text-2xl font-extrabold text-gray-900 mt-2 font-numeric">{highlight.split(" ").slice(-1)}</p>
                  </div>
                </div>
              </div>
            </FadeUp>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── CTA Banner ─── */
function CTABanner({ onCTA }: { onCTA: () => void }) {
  return (
    <section className="py-20 px-6">
      <FadeUp>
        <div
          className="max-w-4xl mx-auto rounded-3xl p-12 text-center relative overflow-hidden"
          style={{
            background: "linear-gradient(135deg, #312e81 0%, #4f46e5 40%, #7c3aed 100%)",
            boxShadow: "0 20px 60px rgba(79,70,229,0.35)",
          }}
        >
          {/* Subtle stripe overlay */}
          <div className="absolute inset-0 opacity-10"
            style={{
              backgroundImage: "repeating-linear-gradient(-45deg, transparent, transparent 20px, rgba(255,255,255,0.15) 20px, rgba(255,255,255,0.15) 21px)",
            }}
          />
          <div className="relative">
            <h2 className="text-3xl md:text-4xl font-extrabold text-white mb-4 tracking-tight">
              Akıllı alışverişe başla
            </h2>
            <p className="text-indigo-200 mb-8 max-w-md mx-auto">
              Finansal profilini oluştur, AI asistanınla tanış ve ilk önerini dakikalar içinde al.
            </p>
            <button
              onClick={onCTA}
              className="inline-flex items-center gap-2 bg-white text-indigo-700 font-bold px-8 py-3.5 rounded-full transition-all duration-150 active:scale-95 hover:shadow-xl text-sm hover:bg-gray-50"
            >
              Ücretsiz Kayıt Ol <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </FadeUp>
    </section>
  );
}

/* ─── Footer ─── */
function Footer() {
  return (
    <footer className="border-t border-gray-100">
      {/* Top light section */}
      <div className="max-w-6xl mx-auto px-6 py-14 grid md:grid-cols-4 gap-10">
        {/* Brand */}
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

        {/* Links */}
        <div>
          <p className="text-xs font-semibold text-gray-900 uppercase tracking-wider mb-4">Ürün</p>
          <ul className="flex flex-col gap-2">
            {["Özellikler", "Nasıl Çalışır", "Giriş Yap", "Kayıt Ol"].map((l) => (
              <li key={l}>
                <a href="#" className="text-sm text-gray-500 hover:text-gray-800 transition-colors">
                  {l}
                </a>
              </li>
            ))}
          </ul>
        </div>

        {/* Team */}
        <div>
          <p className="text-xs font-semibold text-gray-900 uppercase tracking-wider mb-4">Ekip</p>
          <ul className="flex flex-col gap-2 text-sm text-gray-500">
            {["Enes Sarpün", "Takım Üyesi 2", "Takım Üyesi 3"].map((name) => (
              <li key={name}>{name}</li>
            ))}
          </ul>
        </div>
      </div>

      {/* Bottom dark section */}
      <div
        className="px-6 py-6"
        style={{ background: "rgba(17,17,17,0.97)" }}
      >
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

/* ─── Main Page ─── */
export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      router.push("/dashboard");
    }
  }, [router]);

  const handleCTA = () => {
    const token = localStorage.getItem("access_token");
    router.push(token ? "/dashboard" : "/login?mode=register");
  };

  return (
    <main className="min-h-screen">
      <Navbar onCTA={handleCTA} />
      <Hero onCTA={handleCTA} />
      <WhatIsIt />
      <Story />
      <Features />
      <HowItHelps />
      <CTABanner onCTA={handleCTA} />
      <Footer />
    </main>
  );
}
