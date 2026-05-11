"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { personalityApi } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";

interface Question {
  id: number;
  text: string;
  options: { key: string; text: string }[];
}

export default function PersonalityPage() {
  const router = useRouter();
  const { loading } = useAuth();
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [current, setCurrent] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    personalityApi.getQuestions()
      .then((data) => {
        const normalized = (data.questions as unknown[]).map((q: unknown) => {
          const question = q as { id: number; text: string; options: Record<string, string> | { key: string; text: string }[] };
          const options = Array.isArray(question.options)
            ? question.options
            : Object.entries(question.options).map(([key, text]) => ({ key, text }));
          return { ...question, options };
        });
        setQuestions(normalized as Question[]);
      })
      .catch((err) => setError(err.message || "Sorular yüklenemedi"));
  }, []);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="card text-center">
          <p className="text-red-500 mb-2">{error}</p>
          <button className="btn-primary" onClick={() => window.location.reload()}>Tekrar Dene</button>
        </div>
      </div>
    );
  }

  if (loading || questions.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const q = questions[current];
  const progress = ((current + 1) / questions.length) * 100;

  function selectAnswer(key: string) {
    setAnswers((prev) => ({ ...prev, [String(q.id)]: key }));
  }

  async function handleNext() {
    if (!answers[String(q.id)]) return;
    if (current < questions.length - 1) {
      setCurrent((c) => c + 1);
      return;
    }
    setSubmitting(true);
    try {
      await personalityApi.submit(answers);
      router.push("/onboarding/budget");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Hata oluştu");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="card w-full max-w-lg">
        {/* Progress */}
        <div className="mb-6">
          <div className="flex justify-between text-sm text-gray-500 mb-2">
            <span>Kişilik Testi</span>
            <span>{current + 1} / {questions.length}</span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        <h2 className="text-lg font-semibold text-gray-800 mb-6">{q.text}</h2>

        <div className="space-y-3 mb-8">
          {q.options.map((opt) => (
            <button
              key={opt.key}
              onClick={() => selectAnswer(opt.key)}
              className={`w-full text-left px-4 py-3 rounded-xl border-2 transition-all text-sm ${
                answers[String(q.id)] === opt.key
                  ? "border-blue-600 bg-blue-50 text-blue-700 font-medium"
                  : "border-gray-200 hover:border-gray-300 text-gray-700"
              }`}
            >
              <span className="font-bold mr-2">{opt.key}.</span> {opt.text}
            </button>
          ))}
        </div>

        {error && <p className="text-red-500 text-sm mb-4">{error}</p>}

        <div className="flex gap-3">
          {current > 0 && (
            <button className="btn-secondary flex-1" onClick={() => setCurrent((c) => c - 1)}>
              Geri
            </button>
          )}
          <button
            className="btn-primary flex-1"
            onClick={handleNext}
            disabled={!answers[String(q.id)] || submitting}
          >
            {submitting ? "Kaydediliyor..." : current === questions.length - 1 ? "Tamamla" : "İleri"}
          </button>
        </div>
      </div>
    </div>
  );
}
