"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export function useAuth(redirectIfNoToken = true) {
  const router = useRouter();
  const [userId, setUserId] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // localStorage sadece client-side'da erişilebilir
    const t = localStorage.getItem("access_token");
    const uid = localStorage.getItem("user_id");

    if (!t && redirectIfNoToken) {
      router.replace("/login");
      return;
    }

    setToken(t);
    setUserId(uid);
    setLoading(false);
  }, []);

  return { token, userId, loading };
}
