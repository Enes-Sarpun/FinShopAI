"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export function useAuth(redirectIfNoToken = true) {
  const router = useRouter();
  const [userId, setUserId] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [hasPersonality, setHasPersonality] = useState<boolean | null>(null);
  const [hasBudget, setHasBudget] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = localStorage.getItem("access_token");
    const uid = localStorage.getItem("user_id");

    if (!t && redirectIfNoToken) {
      router.replace("/login");
      return;
    }

    setToken(t);
    setUserId(uid);
    setHasPersonality(localStorage.getItem("has_personality") === "true");
    setHasBudget(localStorage.getItem("has_budget") === "true");
    setLoading(false);
  }, []);

  return { token, userId, hasPersonality, hasBudget, loading };
}
