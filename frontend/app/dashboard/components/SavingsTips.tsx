"use client";
import { useState } from "react";
import { ChevronDown, TrendingUp, AlertCircle, Zap, RotateCcw } from "lucide-react";
import type { Personality } from "@/types";

interface SavingsTipsProps {
  tips: string[];
  personality?: Personality | null;
  onRefreshPersonality?: () => void;
}

const SPENDING_TYPE_CONFIG = {
  dengeli: { 
    label: "Dengeli Harcayıcı", 
    color: "bg-blue-50 text-blue-700 border-blue-200",
    bgColor: "bg-blue-500",
    emoji: "⚖️"
  },
  tutumlu: { 
    label: "Tutumlu Harcayıcı", 
    color: "bg-green-50 text-green-700 border-green-200",
    bgColor: "bg-green-500",
    emoji: "💚"
  },
  savruk: { 
    label: "Savruk Harcayıcı", 
    color: "bg-orange-50 text-orange-700 border-orange-200",
    bgColor: "bg-orange-500",
    emoji: "🎉"
  },
};

export default function SavingsTips({ 
  tips, 
  personality,
  onRefreshPersonality 
}: SavingsTipsProps) {
  const [expandedTips, setExpandedTips] = useState<number[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const config = SPENDING_TYPE_CONFIG[personality?.spending_type as keyof typeof SPENDING_TYPE_CONFIG]
    || SPENDING_TYPE_CONFIG.dengeli;

  const toggleTip = (index: number) => {
    setExpandedTips(prev =>
      prev.includes(index) ? prev.filter(i => i !== index) : [...prev, index]
    );
  };

  const handleRefreshPersonality = async () => {
    setIsRefreshing(true);
    if (onRefreshPersonality) {
      await onRefreshPersonality();
    }
    setTimeout(() => setIsRefreshing(false), 1000);
  };

  const getTipIcon = (index: number) => {
    const icons = [TrendingUp, AlertCircle, Zap, TrendingUp, AlertCircle];
    const IconComponent = icons[index % icons.length];
    return <IconComponent className="w-4 h-4" />;
  };

  return (
    <div className="space-y-4">
      {personality && (
        <div className={`card border ${config.color}`}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <span className="text-2xl">{config.emoji}</span>
              <h2 className="font-semibold text-gray-800">Finansal Profil</h2>
            </div>
            <span className={`text-xs font-bold px-3 py-1 rounded-full border ${config.color}`}>
              {config.label}
            </span>
          </div>

          {personality.strengths && personality.strengths.length > 0 && (
            <div className="mb-3">
              <p className="text-xs font-semibold text-gray-600 mb-2">💪 Güçlü Yönler</p>
              <ul className="space-y-1">
                {personality.strengths.map((s, i) => (
                  <li key={i} className="text-sm text-gray-700 flex items-center gap-2">
                    <span className="text-green-600">✓</span> {s}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {personality.weaknesses && personality.weaknesses.length > 0 && (
            <div className="mb-3">
              <p className="text-xs font-semibold text-gray-600 mb-2">⚠️ Geliştirilebilir Alanlar</p>
              <ul className="space-y-1">
                {personality.weaknesses.map((w, i) => (
                  <li key={i} className="text-sm text-gray-700 flex items-center gap-2">
                    <span className="text-orange-600">→</span> {w}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <button
            onClick={handleRefreshPersonality}
            disabled={isRefreshing}
            className="mt-3 w-full flex items-center justify-center gap-2 text-sm font-medium px-3 py-2 rounded-lg hover:bg-black/5 transition-colors disabled:opacity-50"
          >
            <RotateCcw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            Kişilik Testini Yenile
          </button>
        </div>
      )}

      {tips.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
            <Zap className="w-5 h-5 text-yellow-500" />
            Tasarruf Önerileri
          </h2>
          <ul className="space-y-2">
            {tips.map((tip, i) => (
              <li
                key={i}
                className="border rounded-lg overflow-hidden transition-all"
              >
                <button
                  onClick={() => toggleTip(i)}
                  className="w-full flex items-center gap-3 px-3 py-2 hover:bg-gray-50 transition-colors"
                >
                  <div className={`flex-shrink-0 ${config.bgColor} text-white rounded-full p-2`}>
                    {getTipIcon(i)}
                  </div>

                  <p className="text-sm text-gray-700 text-left flex-1">
                    {tip.substring(0, 50)}
                    {tip.length > 50 ? "..." : ""}
                  </p>

                  <ChevronDown
                    className={`w-4 h-4 text-gray-400 transition-transform ${
                      expandedTips.includes(i) ? "rotate-180" : ""
                    }`}
                  />
                </button>

                {expandedTips.includes(i) && (
                  <div className="px-3 py-2 bg-gray-50 border-t">
                    <p className="text-sm text-gray-700">{tip}</p>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {tips.length === 0 && !personality && (
        <div className="card text-center py-8">
          <AlertCircle className="w-8 h-8 text-gray-300 mx-auto mb-2" />
          <p className="text-gray-500 text-sm">Henüz kişilik testi yapılmamış.</p>
          <p className="text-gray-400 text-xs mt-1">Önerileri görmek için onboarding'i tamamla.</p>
        </div>
      )}
    </div>
  );
}