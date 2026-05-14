"use client";
import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, MessageCircle, Bug, Lightbulb, Send, CheckCircle } from "lucide-react";
import Sidebar from "@/app/dashboard/components/Sidebar";

const CATEGORIES = [
  { value: "bug", label: "Hata Bildirimi", icon: Bug, color: "text-red-500", bg: "bg-red-50 dark:bg-red-900/20" },
  { value: "suggestion", label: "Öneri / Fikir", icon: Lightbulb, color: "text-amber-500", bg: "bg-amber-50 dark:bg-amber-900/20" },
  { value: "question", label: "Soru", icon: MessageCircle, color: "text-blue-500", bg: "bg-blue-50 dark:bg-blue-900/20" },
];

const PRIORITIES = [
  { value: "low", label: "Düşük" },
  { value: "medium", label: "Orta" },
  { value: "high", label: "Yüksek" },
];

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4, delay, ease: [0.25, 0.1, 0.25, 1] as const },
});

export default function SupportPage() {
  const [category, setCategory] = useState("bug");
  const [priority, setPriority] = useState("medium");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || !description.trim()) return;
    setSubmitting(true);
    // Simulate submission
    await new Promise((r) => setTimeout(r, 900));
    setSubmitting(false);
    setSubmitted(true);
  }

  function reset() {
    setTitle("");
    setDescription("");
    setCategory("bug");
    setPriority("medium");
    setSubmitted(false);
  }

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50 dark:bg-gray-900">
      <Sidebar />

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto px-6 py-8">

          <Link
            href="/dashboard"
            className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition-colors mb-6"
          >
            <ArrowLeft className="w-4 h-4" />
            Dashboard'a Dön
          </Link>

          <motion.div {...fadeUp(0)} className="mb-6">
            <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">Destek</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Bir sorun mu yaşıyorsun? Önerini veya sorununu bizimle paylaş.
            </p>
          </motion.div>

          {submitted ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="card text-center py-14"
            >
              <div className="w-16 h-16 bg-emerald-50 dark:bg-emerald-900/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="w-8 h-8 text-emerald-500" />
              </div>
              <p className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-1">Mesajın Ulaştı!</p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
                Geri bildiriminiz için teşekkürler. En kısa sürede dönüş yapacağız.
              </p>
              <button onClick={reset} className="btn-primary">
                Yeni Mesaj Gönder
              </button>
            </motion.div>
          ) : (
            <motion.div {...fadeUp(0.08)} className="card">
              <form onSubmit={handleSubmit} className="space-y-5">

                {/* Kategori seçimi */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Kategori
                  </label>
                  <div className="grid grid-cols-3 gap-3">
                    {CATEGORIES.map(({ value, label, icon: Icon, color, bg }) => (
                      <button
                        key={value}
                        type="button"
                        onClick={() => setCategory(value)}
                        className={`flex flex-col items-center gap-2 py-3 rounded-xl border-2 transition-all duration-200 ${
                          category === value
                            ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                            : "border-gray-100 dark:border-gray-700 bg-white dark:bg-gray-800/40 hover:border-gray-200 dark:hover:border-gray-600"
                        }`}
                      >
                        <div className={`w-8 h-8 rounded-lg ${bg} flex items-center justify-center`}>
                          <Icon className={`w-4 h-4 ${color}`} />
                        </div>
                        <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{label}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Öncelik */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Öncelik
                  </label>
                  <div className="flex gap-2">
                    {PRIORITIES.map(({ value, label }) => (
                      <button
                        key={value}
                        type="button"
                        onClick={() => setPriority(value)}
                        className={`px-4 py-1.5 rounded-full text-xs font-medium border transition-all duration-200 ${
                          priority === value
                            ? "bg-blue-600 text-white border-blue-600"
                            : "border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:border-gray-300 dark:hover:border-gray-500"
                        }`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Başlık */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                    Başlık
                  </label>
                  <input
                    type="text"
                    className="input w-full"
                    placeholder="Kısaca anlat..."
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    required
                  />
                </div>

                {/* Açıklama */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                    Açıklama
                  </label>
                  <textarea
                    className="input w-full resize-none"
                    rows={5}
                    placeholder="Detaylı anlat — ne oldu, ne bekliyordun?"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    required
                  />
                </div>

                <button
                  type="submit"
                  disabled={submitting || !title.trim() || !description.trim()}
                  className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {submitting ? (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                  {submitting ? "Gönderiliyor..." : "Gönder"}
                </button>
              </form>
            </motion.div>
          )}
        </div>
      </main>
    </div>
  );
}
