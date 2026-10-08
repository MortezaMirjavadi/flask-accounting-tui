import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/api";
import { queryKeys } from "@/keys";
import { STORAGE_KEYS } from "@/lib/constants";
import type { User, LoginResponse } from "@/types";

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (username: string, password: string) => Promise<LoginResponse>;
  register: (data: {
    username: string;
    password: string;
    display_name: string;
    email?: string;
  }) => Promise<void>;
  logout: () => void;
  verify2fa: (code: string) => Promise<void>;
  requires2fa: boolean;
  pendingUsername: string | null;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [requires2fa, setRequires2fa] = useState(false);
  const [pendingUsername, setPendingUsername] = useState<string | null>(null);
  const [username, setUsername] = useState<string | null>(() => {
    return localStorage.getItem(STORAGE_KEYS.USERNAME);
  });

  const { data: user, isLoading, isError } = useQuery({
    queryKey: queryKeys.auth.me(),
    queryFn: () => apiGet<User>("/auth/me"),
    enabled: !!username,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    if (user) {
      localStorage.setItem(STORAGE_KEYS.USERNAME, user.username);
    }
  }, [user]);

  const login = useCallback(
    async (username: string, password: string) => {
      const response = await apiPost<LoginResponse>("/auth/login", {
        username,
        password,
      });
      if (response.requires_2fa) {
        setRequires2fa(true);
        setPendingUsername(username);
        localStorage.setItem(STORAGE_KEYS.USERNAME, username);
        return response;
      }
      localStorage.setItem(STORAGE_KEYS.USERNAME, username);
      setUsername(username);
      setRequires2fa(false);
      setPendingUsername(null);
      await queryClient.invalidateQueries({ queryKey: queryKeys.auth.me() });
      return response;
    },
    [queryClient],
  );

  const register = useCallback(
    async (data: {
      username: string;
      password: string;
      display_name: string;
      email?: string;
    }) => {
      await apiPost("/auth/register", data);
    },
    [],
  );

  const verify2fa = useCallback(
    async (code: string) => {
      await apiPost("/auth/verify-2fa", { username: pendingUsername, code });
      setRequires2fa(false);
      setPendingUsername(null);
      await queryClient.invalidateQueries({ queryKey: queryKeys.auth.me() });
    },
    [queryClient, pendingUsername],
  );

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEYS.USERNAME);
    localStorage.removeItem(STORAGE_KEYS.TOKEN);
    setUsername(null);
    setRequires2fa(false);
    setPendingUsername(null);
    queryClient.clear();
  }, [queryClient]);

  const value: AuthContextType = {
    user: user ?? null,
    isLoading: isLoading || (username !== null && !user && !isError),
    isAuthenticated: !!user,
    isAdmin: user?.is_admin ?? false,
    login,
    register,
    logout,
    verify2fa,
    requires2fa,
    pendingUsername,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
