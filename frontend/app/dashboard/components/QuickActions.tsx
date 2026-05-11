"use client";
import Link from "next/link";

// GÖREV: SEN
// Bu component hızlı erişim butonlarını içeriyor.
// Yapılabilecekler:
//   - İkon ekle her butona (lucide-react)
//   - "Son Arama" göster (chat history'den)
//   - Bütçe güncelle butonu ekle
//   - Kişilik testini yenile butonu ekle
//   - Butonlara hover animasyonu ekle

export default function QuickActions() {
  return (
    <div className="card">
      <h2 className="font-semibold text-gray-800 mb-4">Hızlı Erişim</h2>
      <div className="grid grid-cols-2 gap-3">
        <Link href="/chat" className="btn-secondary text-center text-sm">
          Alışveriş Asistanı
        </Link>
        <Link href="/chat/history" className="btn-secondary text-center text-sm">
          Geçmiş Aramalar
        </Link>
        <Link href="/onboarding/budget" className="btn-secondary text-center text-sm">
          Bütçeyi Güncelle
        </Link>
        <Link href="/onboarding/personality" className="btn-secondary text-center text-sm">
          Kişilik Testini Yenile
        </Link>
      </div>
    </div>
  );
}
