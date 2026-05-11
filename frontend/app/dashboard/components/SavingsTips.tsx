"use client";
import type { Personality } from "@/types";

// GÖREV: ARKADAŞ 2
// Bu component tasarruf önerilerini ve kişilik profilini gösteriyor.
// Yapılabilecekler:
//   - Her öneri için ikon ekle
//   - Kişilik tipine göre farklı renk/tema uygula (savruk=kırmızı, dengeli=mavi, tutumlu=yeşil)
//   - Personality kartı ekle (spending_type, strengths, weaknesses)
//   - Önerileri accordion/expand şeklinde göster
//   - "Kişilik Testini Yenile" butonu ekle

interface SavingsTipsProps {
  tips: string[];
  personality?: Personality | null;
}

const SPENDING_TYPE_CONFIG = {
  dengeli: { label: "Dengeli Harcayıcı", color: "bg-blue-50 text-blue-700 border-blue-200" },
  tutumlu: { label: "Tutumlu Harcayıcı", color: "bg-green-50 text-green-700 border-green-200" },
  savruk: { label: "Savruk Harcayıcı", color: "bg-orange-50 text-orange-700 border-orange-200" },
};

export default function SavingsTips({ tips, personality }: SavingsTipsProps) {
  const config = SPENDING_TYPE_CONFIG[personality?.spending_type as keyof typeof SPENDING_TYPE_CONFIG]
    || SPENDING_TYPE_CONFIG.dengeli;

  return (
    <div className="space-y-4">
      {/* Kişilik Profili */}
      {personality && (
        <div className={`card border ${config.color}`}>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold">Finansal Profil</h2>
            <span className={`text-xs font-bold px-2 py-1 rounded-full border ${config.color}`}>
              {config.label}
            </span>
          </div>
          {personality.strengths?.length > 0 && (
            <div className="mb-2">
              <p className="text-xs font-medium text-gray-500 mb-1">Güçlü Yönler</p>
              <ul className="space-y-1">
                {personality.strengths.map((s, i) => (
                  <li key={i} className="text-sm text-gray-700">✓ {s}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Tasarruf Önerileri */}
      {tips.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-gray-800 mb-3">Tasarruf Önerileri</h2>
          <ul className="space-y-2">
            {tips.map((tip, i) => (
              <li key={i} className="text-sm text-gray-600">{tip}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
