import { AUTH_STORAGE_KEY, AUTH_REVISION_KEY } from "../../config/authSession";

export const dynamic = "force-dynamic";

export function GET(): Response {
  const allowedOrigins = (process.env.SYSTEM_SSO_ORIGINS ?? "").split(",").flatMap((value) => {
    try {
      const url = new URL(value.trim());
      return ["http:", "https:"].includes(url.protocol) ? [url.origin] : [];
    } catch { return []; }
  });
  // The bridge is unavailable in standalone deployments.
  if (!allowedOrigins.length) return new Response("Not found", { status: 404 });
  const nonce = crypto.randomUUID();
  const html = `<!doctype html><html><head><meta charset="utf-8"><title>Đồng bộ phiên</title></head><body>
<script nonce="${nonce}">
const allowedOrigins = ${JSON.stringify(allowedOrigins)};
window.addEventListener("message", (event) => {
  if (event.source !== window.parent || !allowedOrigins.includes(event.origin)
      || event.data?.type !== "olpai-session-reset" || typeof event.data.id !== "string") return;
  try {
    localStorage.removeItem(${JSON.stringify(AUTH_STORAGE_KEY)});
    localStorage.setItem(${JSON.stringify(AUTH_REVISION_KEY)}, crypto.randomUUID());
    event.source.postMessage({type: "olpai-session-reset-done", id: event.data.id}, event.origin);
  } catch {}
});
</script></body></html>`;
  return new Response(html, { headers: {
    "Content-Type": "text/html; charset=utf-8",
    "Cache-Control": "no-store",
    "Content-Security-Policy": `default-src 'none'; script-src 'nonce-${nonce}'; frame-ancestors ${allowedOrigins.join(" ")}`,
    "Referrer-Policy": "no-referrer",
  } });
}
