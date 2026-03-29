/**
 * scripts/inject-env.js
 * ─────────────────────────────────────────────────────────────
 * Build script para Vercel: injeta SUPABASE_URL e SUPABASE_ANON_KEY
 * no frontend/config.js antes do deploy.
 *
 * Sempre gera o arquivo — mesmo sem env vars — para garantir que
 * a Vercel consiga servir /config.js sem 404.
 * Nesse caso os valores ficam vazios e o app exibe um aviso no login.
 *
 * Como configurar:
 *   Vercel Dashboard → Settings → Environment Variables:
 *     SUPABASE_URL      = https://xxxx.supabase.co
 *     SUPABASE_ANON_KEY = eyJhbGci...
 * ─────────────────────────────────────────────────────────────
 */

const fs   = require('fs');
const path = require('path');

const url = process.env.SUPABASE_URL      || '';
const key = process.env.SUPABASE_ANON_KEY || '';

const configPath = path.join(__dirname, '..', 'frontend', 'config.js');

if (!url || !key) {
  // Falha o build visivelmente para que a Vercel notifique o deploy como "falhou"
  // (muito melhor do que um site quebrado em produção sem aviso)
  console.error('');
  console.error('╔══════════════════════════════════════════════════════════════╗');
  console.error('║  [inject-env] ❌  VARIÁVEIS DE AMBIENTE NÃO CONFIGURADAS     ║');
  console.error('╠══════════════════════════════════════════════════════════════╣');
  console.error(`║  SUPABASE_URL      : ${url ? '✅ definida' : '❌ AUSENTE'}`);
  console.error(`║  SUPABASE_ANON_KEY : ${key ? '✅ definida' : '❌ AUSENTE'}`);
  console.error('╠══════════════════════════════════════════════════════════════╣');
  console.error('║  Corrija em: Vercel Dashboard → Settings → Env Variables     ║');
  console.error('╚══════════════════════════════════════════════════════════════╝');
  console.error('');
  process.exit(1);   // ← build falha com código 1, Vercel bloqueia o deploy
}

// Usa window.* para evitar conflito de re-declaração com qualquer outro script
// que possa usar var/let/const SUPABASE_URL no mesmo escopo global.
const content = `// Gerado automaticamente pelo build (scripts/inject-env.js) — não edite manualmente.
// Usa window.* para evitar SyntaxError de re-declaração no browser.
window.SUPABASE_URL = '${url}';
window.SUPABASE_KEY = '${key}';
`;

fs.writeFileSync(configPath, content, 'utf-8');
console.log('[inject-env] ✅ frontend/config.js gerado. URL definida:', !!url, '| KEY definida:', !!key);
