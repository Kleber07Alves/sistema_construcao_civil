import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const COOKIE_KEY     = "auth_token"; // idêntico ao AuthContext.tsx
const ROTAS_PUBLICAS = new Set(["/login"]);


export function proxy(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;
  const token        = request.cookies.get(COOKIE_KEY)?.value;
  const autenticado  = Boolean(token?.trim());


  if (autenticado && ROTAS_PUBLICAS.has(pathname)) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  if (!autenticado && !ROTAS_PUBLICAS.has(pathname)) {
    const loginUrl = new URL("/login", request.url);
    if (pathname !== "/") {
      loginUrl.searchParams.set("redirect", pathname);
    }
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.\\w+$).*)",
  ],
};