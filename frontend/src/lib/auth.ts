const TOKEN_KEY = "access_token";
const OPERATOR_TOKEN_KEY = "operator_access_token";

export function getToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function isAuthenticated() {
  return Boolean(getToken());
}

export function logout() {
  clearToken();
  window.location.href = "/login";
}

export function getOperatorToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(OPERATOR_TOKEN_KEY);
}

export function setOperatorToken(token: string) {
  localStorage.setItem(OPERATOR_TOKEN_KEY, token);
}

export function clearOperatorToken() {
  localStorage.removeItem(OPERATOR_TOKEN_KEY);
}

export function isOperatorAuthenticated() {
  return Boolean(getOperatorToken());
}

export function operatorLogout() {
  clearOperatorToken();
  window.location.href = "/operator-login";
}
