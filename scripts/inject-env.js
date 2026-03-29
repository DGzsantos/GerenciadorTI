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
  console.warn('[inject-env] ⚠️  SUPABASE_URL ou SUPABASE_ANON_KEY não definidos nas env vars.');
  console.warn('             Gerando config.js com valores vazios — app mostrará aviso de configuração.');
}

const content = `// Gerado automaticamente pelo build (scripts/inject-env.js) — não edite manualmente.
// Configure SUPABASE_URL e SUPABASE_ANON_KEY no painel da Vercel.
const SUPABASE_URL  = '${url}';
const SUPABASE_KEY  = '${key}';
`;

fs.writeFileSync(configPath, content, 'utf-8');
console.log('[inject-env] ✅ frontend/config.js gerado. URL definida:', !!url, '| KEY definida:', !!key);
