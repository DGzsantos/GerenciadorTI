/**
 * ping-check — Supabase Edge Function
 *
 * Verifica a acessibilidade HTTP de uma lista de IPs/hostnames.
 * Útil para IPs PÚBLICOS quando o frontend está em HTTPS
 * (mixed-content bloqueia fetch http:// diretamente do browser).
 *
 * LIMITAÇÃO: Edge Functions rodam na nuvem (Deno Deploy) e NÃO
 * conseguem alcançar IPs privados (192.168.x.x, 10.x.x.x).
 * Para redes locais, use o pingDevice() do frontend, que roda
 * no browser do usuário — ele SIM está na mesma rede.
 *
 * Deploy:
 *   supabase functions deploy ping-check --no-verify-jwt
 *
 * Chamada:
 *   POST https://<project>.supabase.co/functions/v1/ping-check
 *   Body: { "ips": ["1.2.3.4", "meuservidor.exemplo.com"] }
 *   Headers: Authorization: Bearer <anon-key>
 */

import { serve } from 'https://deno.land/std@0.177.0/http/server.ts';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

serve(async (req: Request) => {
  // Pre-flight CORS
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: CORS });
  }

  let ips: string[] = [];
  try {
    const body = await req.json();
    if (!Array.isArray(body?.ips)) throw new Error('ips deve ser um array');
    ips = body.ips.filter((ip: unknown) => typeof ip === 'string' && ip.trim());
  } catch (e) {
    return new Response(
      JSON.stringify({ error: (e as Error).message }),
      { status: 400, headers: { ...CORS, 'Content-Type': 'application/json' } },
    );
  }

  const TIMEOUT_MS = 3000;

  const results = await Promise.all(
    ips.map(async (ip: string) => {
      const target = ip.trim().replace(/^https?:\/\//, '').split('/')[0];
      const controller = new AbortController();
      const tid = setTimeout(() => controller.abort(), TIMEOUT_MS);
      try {
        // Tenta HTTP HEAD — qualquer resposta (mesmo 4xx/5xx) = host acessível
        await fetch(`http://${target}`, {
          method: 'HEAD',
          signal: controller.signal,
        });
        clearTimeout(tid);
        return { ip, online: true };
      } catch {
        clearTimeout(tid);
        return { ip, online: false };
      }
    }),
  );

  return new Response(
    JSON.stringify({ results, checked_at: new Date().toISOString() }),
    { headers: { ...CORS, 'Content-Type': 'application/json' } },
  );
});
